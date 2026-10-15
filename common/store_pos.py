"""Shared, hardware-independent POS state; money is integer COP, never floats."""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
from itertools import islice
import os
from pathlib import Path
import tempfile
from time import monotonic
from uuid import UUID, uuid4


PAYMENT_METHODS = ("EFECTIVO", "TRANSFERENCIA", "TARJETA", "OTRO")


def checkout_rejected(error):
    """Only the POS server's explicit rolled-back validation code is definitive.

    Network errors, generic PostgreSQL errors, permission failures and request
    collisions never release an uncertain checkout identity.
    """
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if str(getattr(error, "code", "")) == "GS001":
            return True
        error = getattr(error, "__cause__", None)
    return False


def barcode_value(value):
    value = str(value or "").strip()
    if len(value) > 128 or any(not c.isprintable() for c in value):
        raise ValueError("El código de barras debe tener hasta 128 caracteres sin controles.")
    return value


def cash_change(total, received):
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("El total debe ser un valor entero no negativo.")
    if isinstance(received, bool) or not isinstance(received, int) or received < total:
        raise ValueError("El efectivo recibido es menor que el total.")
    return received - int(total)


class ProductCatalog:
    """Indexed exact scans and local search; scanning never reloads the page."""
    def __init__(self, products=()):
        self.replace(products)

    def replace(self, products):
        self.products = {int(p["id"]): dict(p) for p in products}
        self.barcodes, self.skus = {}, {}
        self.search_rows = []
        for product in self.products.values():
            if not product.get("active", True):
                continue
            barcode = barcode_value(product.get("barcode"))
            if barcode:
                self.barcodes.setdefault(barcode, []).append(product)
            sku = str(product.get("sku") or "").strip().casefold()
            if sku:
                self.skus.setdefault(sku, []).append(product)
            self.search_rows.append((product, " ".join(str(product.get(k) or "") for k in
                                                     ("name", "sku", "barcode", "category")).casefold()))

    def exact(self, code):
        code = barcode_value(code)
        matches = self.barcodes.get(code, []) or self.skus.get(code.casefold(), [])
        if len(matches) > 1:
            raise ValueError("Código ambiguo: revisa los productos del gimnasio.")
        return dict(matches[0]) if matches else None

    def search(self, term="", limit=200):
        term = str(term).strip().casefold()
        return [dict(row) for row in islice((row for row, text in self.search_rows if term in text), max(0, int(limit)))]


class Cart:
    def __init__(self):
        self.rows = {}

    def add(self, product, quantity=1):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("La cantidad debe ser un número entero positivo.")
        product_id = int(product["id"])
        if not product.get("active", True):
            raise ValueError("El producto está inactivo.")
        self.set_quantity(product, self.rows.get(product_id, {}).get("quantity", 0) + quantity)

    def set_quantity(self, product, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError("La cantidad debe ser un número entero positivo.")
        product_id = int(product["id"])
        if quantity and not product.get("active", True):
            raise ValueError("El producto está inactivo.")
        stock = int(product.get("stock_quantity") or 0)
        if quantity > stock:
            raise ValueError(f"Stock disponible: {stock}.")
        if not quantity:
            self.rows.pop(product_id, None)
            return
        price = product.get("sale_price", 0)
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("El precio del producto no es válido.")
        self.rows[product_id] = {"product": dict(product), "quantity": quantity,
                                 "unit_price": price, "subtotal": price * quantity}

    @property
    def total(self):
        return sum(row["subtotal"] for row in self.rows.values())

    def items(self):
        return [{"product_id": pid, "quantity": row["quantity"], "expected_price": row["unit_price"]}
                for pid, row in sorted(self.rows.items())]

    def clear(self):
        self.rows.clear()


class CheckoutAttempt:
    """An uncertain network result must reuse the exact same request and payload."""
    def __init__(self, payload, request_id=None):
        if request_id is not None and (not isinstance(request_id, str) or not request_id):
            raise ValueError("La referencia del cobro no es válida.")
        self.request_id = str(UUID(request_id)) if request_id is not None else str(uuid4())
        self._payload = deepcopy(payload)

    @property
    def payload(self):
        return deepcopy(self._payload)

    def retry(self, payload=None):
        if payload is not None and payload != self._payload:
            raise ValueError("Consulta el resultado del cobro pendiente antes de cambiar la venta.")
        return dict(request_id=self.request_id, **deepcopy(self._payload))


class PendingCheckout:
    """Durable gym/user-scoped checkout identity, saved before sending a write.

    A corrupt/unreadable journal is an explicit error, never an invitation to
    create a new charge. Atomic replace retains the old journal on write errors.
    """
    def __init__(self, folder, gym_id, user_id):
        if not str(gym_id or "").strip() or not str(user_id or "").strip():
            raise ValueError("No se pudo identificar la cuenta del cobro pendiente.")
        self.scope = hashlib.sha256((str(gym_id) + ":" + str(user_id)).encode()).hexdigest()
        self.folder = Path(folder) / "pos_pending"
        self.path = self.folder / (self.scope + ".json")

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as error:
            raise ValueError("No se pudo leer el cobro pendiente. Revisa el historial antes de cobrar otra vez.") from error
        if (not isinstance(data, dict) or data.get("version") != 1 or data.get("scope") != self.scope
                or not isinstance(data.get("payload"), dict)
                or not isinstance(data.get("request_id"), str) or not data["request_id"]):
            raise ValueError("El archivo del cobro pendiente no es válido. Consulta el historial de ventas.")
        try:
            return CheckoutAttempt(data["payload"], data["request_id"])
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("La referencia del cobro pendiente no es válida. Consulta el historial de ventas.") from error

    def save(self, attempt):
        with self._lock():
            self._save_locked(attempt)

    @contextmanager
    def _lock(self):
        """Kernel locks are released on process exit, including an abrupt crash."""
        self.folder.mkdir(parents=True, exist_ok=True)
        with (self.folder / (self.scope + ".lock")).open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError("Otra ventana está procesando el cobro pendiente. Espera su resultado.") from error
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _save_locked(self, attempt):
        current = self.load()
        if current is not None and (current.request_id != attempt.request_id or current.payload != attempt.payload):
            raise ValueError("Hay un cobro pendiente. Consulta su resultado antes de iniciar otro.")
        self.folder.mkdir(parents=True, exist_ok=True)
        data = dict(version=1, scope=self.scope, request_id=attempt.request_id, payload=attempt.payload)
        descriptor, temporary = tempfile.mkstemp(prefix=".checkout-", dir=self.folder)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def clear(self, request_id):
        with self._lock():
            self._clear_locked(request_id)

    def _clear_locked(self, request_id):
        current = self.load()
        if current is not None and current.request_id != str(request_id):
            raise ValueError("La referencia pendiente cambió; revisa el historial.")
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class ScannerBuffer:
    """ENTER consumes a fast HID sequence exactly once; no device/driver needed.

    A UI adapter must call this only while its POS context is visible and focused,
    with no modal or unrelated text field. It must not install a global key hook.
    """
    def __init__(self, minimum=3, interval=.080, average=.050):
        self.minimum, self.interval, self.average = minimum, interval, average
        self.reset()

    def reset(self):
        self.characters, self.times = [], []
        self.overflow = False

    def feed(self, character, now=None):
        now = monotonic() if now is None else now
        if self.overflow:
            return
        if len(character) != 1 or not character.isprintable():
            self.reset()
            return
        if self.times and now - self.times[-1] > self.interval:
            self.reset()
        self.characters.append(character)
        self.times.append(now)
        if len(self.characters) > 128:
            self.overflow = True

    def finish(self, now=None):
        now = monotonic() if now is None else now
        code = "".join(self.characters)
        times = self.times[:]
        overflow = self.overflow
        self.reset()
        if overflow or len(code) < self.minimum or now - times[-1] > self.interval:
            return None
        if (times[-1] - times[0]) / max(1, len(times) - 1) > self.average:
            return None
        return barcode_value(code)


class StoreDatabaseMixin:
    """The same RPC client contract is used by Admin and Reception in all editions."""
    def _pos_rpc(self, name, **params):
        response = self._execute(self.client.rpc(name, {"p_gym_id": self.gym_id, **params}))
        value = response.data
        row_lists = {"store_pos_products", "store_pos_history", "store_pos_movements"}
        if (isinstance(value, list) and len(value) == 1 and
                (isinstance(value[0], list) or (name not in row_lists and isinstance(value[0], dict)))):
            value = value[0]
        return value

    def pos_settings(self):
        return self._pos_rpc("store_pos_settings")

    def pos_configure(self, enabled):
        return self._pos_rpc("store_pos_configure", p_enabled=bool(enabled))

    def pos_products(self, search="", include_inactive=False):
        return self._pos_rpc("store_pos_products", p_search=str(search).strip(),
                             p_include_inactive=bool(include_inactive))

    def pos_save_product(self, data, product_id=None):
        return self._pos_rpc("store_pos_save_product", p_product_id=product_id, p_data=dict(data))

    def pos_inventory(self, product_id, mode, quantity, reason="", unit_cost=None,
                      expected_stock=None, request_id=None):
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("La cantidad de inventario debe ser un número entero.")
        if unit_cost is not None and (isinstance(unit_cost, bool) or not isinstance(unit_cost, int) or unit_cost < 0):
            raise ValueError("El costo debe ser un valor entero no negativo.")
        if expected_stock is not None and (isinstance(expected_stock, bool) or not isinstance(expected_stock, int) or expected_stock < 0):
            raise ValueError("El stock esperado debe ser un número entero no negativo.")
        return self._pos_rpc("store_pos_inventory", p_request_id=str(UUID(request_id)) if request_id else str(uuid4()),
                             p_product_id=int(product_id), p_mode=str(mode), p_quantity=int(quantity),
                             p_reason=reason, p_unit_cost=unit_cost, p_expected_stock=expected_stock)

    def pos_checkout(self, items, payment, client_id=None, customer_name="", notes="", *, request_id):
        return self._pos_rpc("store_pos_checkout", p_request_id=str(UUID(request_id)), p_items=items,
                             p_payment=payment, p_client_id=client_id, p_customer_name=customer_name, p_notes=notes)

    def pos_history(self, filters=None):
        return self._pos_rpc("store_pos_history", p_filters=dict(filters or {}))

    def pos_void(self, order_id, reason):
        return self._pos_rpc("store_pos_void", p_order_id=str(UUID(order_id)), p_reason=str(reason).strip())

    def pos_stats(self, filters=None):
        return self._pos_rpc("store_pos_stats", p_filters=dict(filters or {}))

    def pos_movements(self, product_id=None):
        return self._pos_rpc("store_pos_movements", p_product_id=product_id)
