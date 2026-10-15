"""Atlantic desktop POS shared by Administrator and Reception in every edition.

The server owns stock, permissions, clock and payment completion. HID input is
bound only to this page's widgets and is consumed once, on ENTER.
"""
from __future__ import annotations

import tkinter as tk
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from tkinter import ttk

from atlantic_ui import COLORS
from desktop_ui import decorate_window, friendly_error, messagebox, simpledialog
from gym_time import business_today, display_timestamp, timezone_for
from money_input import parse_amount
from responsive_ui import ScrollArea, UI_FONT, fit_window
from store_pos import Cart, CheckoutAttempt, PAYMENT_METHODS, PendingCheckout, ProductCatalog, ScannerBuffer, cash_change, checkout_rejected


def money(value):
    return "$" + f"{int(value or 0):,}".replace(",", ".")


def records(value):
    return value if isinstance(value, list) else []


class PosDialog(tk.Toplevel):
    def __init__(self, parent, title, width=570, height=650):
        super().__init__(parent.winfo_toplevel())
        self.title(title)
        self.transient(parent.winfo_toplevel())
        decorate_window(self)
        fit_window(self, width, height, parent=parent.winfo_toplevel())
        self.result = None
        viewport = ScrollArea(self, padding=20, style="Surface.TFrame", width=width, height=height)
        viewport.pack(fill="both", expand=True, padx=8, pady=8)
        self.body = viewport.body
        self.body.columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

    def field(self, label, variable, row):
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(row=row * 2, column=0, sticky="w", pady=(8, 3))
        entry = ttk.Entry(self.body, textvariable=variable)
        entry.grid(row=row * 2 + 1, column=0, sticky="ew")
        entry._hid_scanner = self
        return entry


class CheckoutDialog(PosDialog):
    """The form and request stay intact until an authoritative response arrives."""
    def __init__(self, panel):
        super().__init__(panel, "Cobrar venta", 580, 720)
        self.panel = panel
        self.method = tk.StringVar(value="EFECTIVO")
        self.received = tk.StringVar(value=str(panel.cart.total))
        self.reference = tk.StringVar()
        self.customer = tk.StringVar()
        self.client = tk.StringVar(value="Venta rápida sin cliente")
        self.notes = tk.StringVar()
        self.change = tk.StringVar()
        self.clients = {}
        self.submitting = False
        self.inputs = []
        ttk.Label(self.body, text="TOTAL A PAGAR", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self.body, text=money(panel.checkout_total()), font=(UI_FONT, 24, "bold"), foreground=COLORS["primary"]).grid(row=1, column=0, sticky="w", pady=(4, 12))
        ttk.Label(self.body, text="Método de pago", style="Field.TLabel").grid(row=2, column=0, sticky="w")
        self.method_input = ttk.Combobox(self.body, textvariable=self.method, values=PAYMENT_METHODS, state="readonly")
        self.method_input.grid(row=3, column=0, sticky="ew")
        self.cash_input = self.field("Efectivo recibido", self.received, 2)
        ttk.Label(self.body, textvariable=self.change, foreground=COLORS["success"]).grid(row=6, column=0, sticky="w", pady=(5, 0))
        self.reference_input = self.field("Referencia de pago (opcional)", self.reference, 4)
        self.customer_input = self.field("Comprador / buscar cliente (opcional)", self.customer, 5)
        client_actions = ttk.Frame(self.body, style="Surface.TFrame")
        client_actions.grid(row=12, column=0, sticky="ew", pady=(6, 0))
        self.client_search = ttk.Button(client_actions, text="Buscar cliente", command=self.find_clients)
        self.client_search.pack(side="left")
        self.client_input = ttk.Combobox(self.body, textvariable=self.client, state="readonly", values=("Venta rápida sin cliente",))
        self.client_input.grid(row=13, column=0, sticky="ew", pady=(5, 0))
        self.notes_input = self.field("Nota (opcional)", self.notes, 7)
        self.feedback = tk.StringVar()
        ttk.Label(self.body, textvariable=self.feedback, wraplength=460, foreground=COLORS["warning"]).grid(row=16, column=0, sticky="ew", pady=(10, 0))
        actions = ttk.Frame(self.body, style="Surface.TFrame")
        actions.grid(row=17, column=0, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Cerrar", command=self.destroy).pack(side="left", padx=(0, 8))
        self.confirm = ttk.Button(actions, text="Confirmar venta", command=self.save, style="Primary.TButton")
        self.confirm.pack(side="left")
        self.revalidate = ttk.Button(self.body, text="Revisar precios y existencias del carrito", command=self.revalidate_cart)
        self.revalidate.grid(row=18, column=0, sticky="e", pady=(10, 0))
        self.inputs = [self.method_input, self.cash_input, self.reference_input, self.customer_input, self.client_input, self.notes_input, self.client_search]
        self.method.trace_add("write", self.update_change)
        self.received.trace_add("write", self.update_change)
        self.update_change()
        if panel.pending is not None:
            self.restore_pending()
        self.after_idle(self.cash_input.focus_set)

    def update_change(self, *_):
        if self.method.get() != "EFECTIVO":
            self.change.set("Pago completo por " + self.method.get().lower())
            self.cash_input.configure(state="disabled")
            return
        if self.panel.pending is None:
            self.cash_input.configure(state="normal")
        try:
            self.change.set("Cambio: " + money(cash_change(self.panel.checkout_total(), parse_amount(self.received.get()))))
        except ValueError:
            self.change.set("El recibido debe cubrir el total de la venta.")

    def find_clients(self):
        try:
            rows = self.panel.db.list_clients(self.customer.get().strip())
        except Exception as error:
            messagebox.showerror("No se pudo buscar", friendly_error(error), parent=self)
            return
        self.clients = {}
        for row in records(rows)[:100]:
            name = row.get("full_name") or row.get("client_name") or " ".join(str(row.get(k) or "") for k in ("first_name", "last_name")).strip()
            label = f"{name} · {row.get('document') or 'Sin documento'}"
            self.clients[label] = row["id"]
        self.client_input.configure(values=("Venta rápida sin cliente", *self.clients))
        if self.clients:
            self.client.set(next(iter(self.clients)))
        else:
            self.client.set("Venta rápida sin cliente")
            self.feedback.set("No se encontraron clientes. Puedes continuar con venta rápida.")

    def restore_pending(self):
        payload = self.panel.pending.payload
        payment = payload["payment"]
        self.method.set(payment["method"])
        self.received.set(str(payment.get("received") or 0))
        self.reference.set(payment.get("reference") or "")
        self.customer.set(payload.get("customer_name") or "")
        self.notes.set(payload.get("notes") or "")
        for widget in self.inputs:
            widget.configure(state="disabled")
        self.confirm.configure(text="Reintentar mismo cobro")
        self.feedback.set("Resultado pendiente de confirmar. El reintento conserva la misma venta y no duplica el cobro.")
        self.revalidate.configure(state="disabled")

    def restore_editing(self):
        for widget in self.inputs:
            widget.configure(state="readonly" if isinstance(widget, ttk.Combobox) else "normal")
        self.confirm.configure(text="Confirmar venta")
        self.revalidate.configure(state="normal")
        self.update_change()

    def revalidate_cart(self):
        if self.panel.revalidate_cart():
            self.destroy()

    def save(self):
        if self.submitting:
            return
        if self.panel.pending is None:
            try:
                received = parse_amount(self.received.get()) if self.method.get() == "EFECTIVO" else None
                if received is not None:
                    cash_change(self.panel.cart.total, received)
                payload = dict(items=self.panel.cart.items(), payment=dict(method=self.method.get(), received=received, reference=self.reference.get().strip()),
                               client_id=self.clients.get(self.client.get()), customer_name=self.customer.get().strip(), notes=self.notes.get().strip())
                self.panel.begin_checkout(payload)
            except (ValueError, OSError, RuntimeError) as error:
                messagebox.showwarning("Revisa el cobro", str(error), parent=self)
                return
        self.restore_pending()
        self.submitting = True
        self.confirm.configure(state="disabled")
        try:
            result = self.panel.db.pos_checkout(**self.panel.pending.retry())
            if not isinstance(result, dict) or not (result.get("id") or result.get("order_id")):
                raise RuntimeError("El servidor no confirmó el comprobante. Consulta o reintenta el mismo cobro.")
        except Exception as error:
            if checkout_rejected(error) and self.panel.reject_checkout():
                self.restore_editing()
                self.feedback.set("El servidor rechazó esta venta sin realizar el cobro. Revisa precios y existencias antes de confirmar otra vez.")
                messagebox.showwarning("Venta rechazada sin cobro", friendly_error(error), parent=self)
            else:
                self.feedback.set("Resultado no confirmado. Conservamos el cobro para consultar o reintentar.")
                messagebox.showerror("Cobro pendiente de confirmar", friendly_error(error), parent=self)
        else:
            self.result = result
            self.panel.complete_checkout(result)
            self.destroy()
            self.panel.show_receipt(result)
        finally:
            self.submitting = False
            if self.winfo_exists():
                self.confirm.configure(state="normal")


class StorePosPanel(ttk.Frame):
    def __init__(self, owner, parent=None, *, administrator=False, external_catalog=False):
        super().__init__(parent or owner, style="Card.TFrame")
        self.owner, self.db, self.administrator = owner, owner.db, administrator
        self.external_catalog = external_catalog
        self.cart, self.catalog, self.scanner = Cart(), ProductCatalog(), ScannerBuffer()
        self._scan_origin = None
        self.pending = None
        self.journal = None
        self.pending_error = None
        self.inventory_journal = None
        self.inventory_pending = None
        self.inventory_error = None
        self.enabled = True
        self.status = tk.StringVar(value="Escanea y pulsa ENTER, o busca un producto para agregarlo.")
        self.total = tk.StringVar(value=money(0))
        self.search = tk.StringVar()
        self.history_rows = {}
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.sale_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(self.sale_tab, text="Punto de venta")
        self.sale_tab.columnconfigure(0, weight=1)
        self.sale_tab.rowconfigure(0, weight=1)
        self.catalog_host = ttk.Frame(self.sale_tab, style="Card.TFrame")
        self.catalog_host.grid(row=0, column=0, sticky="nsew")
        self.catalog_notice = tk.StringVar()
        ttk.Label(self.catalog_host, textvariable=self.catalog_notice, style="CardMuted.TLabel", wraplength=600).pack(side="bottom", anchor="w", pady=(4, 0))
        if not external_catalog:
            self.build_product_search()
        self.build_cart()
        self.build_history()
        if administrator:
            self.build_stats()
            self.build_settings()
        self._scan_tag = "AtlanticPos" + str(id(self))
        self.winfo_toplevel().bind_class(self._scan_tag, "<KeyPress>", self.key)
        self.winfo_toplevel().bind_class(self._scan_tag, "<FocusOut>", self.reset_scanner)
        self.notebook.bind("<<NotebookTabChanged>>", self.reset_scanner, add="+")
        self.bind("<Unmap>", self.reset_scanner, add="+")
        self._map_binding = owner.bind("<Map>", self._tag_event, add="+")
        self.bind("<Destroy>", self._destroy, add="+")
        self.after_idle(self.tag_widgets)
        self.restore_journal()
        if not external_catalog:
            self.after_idle(self.search_entry.focus_set)

    def build_product_search(self):
        toolbar = ttk.Frame(self.catalog_host, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 8))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry._pos_search = True
        ttk.Button(toolbar, text="Buscar", command=self.render_products).pack(side="left", padx=(8, 0))
        self.search.trace_add("write", lambda *_: self.render_products())
        self.product_tree = self.tree(self.catalog_host, (("name", "Producto", 240), ("code", "Código / SKU", 145), ("category", "Categoría", 130), ("price", "Precio", 110), ("stock", "Stock", 65)), height=5)
        self.product_tree.pack(fill="both", expand=True)
        self.product_tree.bind("<Double-1>", lambda _: self.add_selected())
        ttk.Button(self.catalog_host, text="Agregar al carrito", command=self.add_selected).pack(anchor="w", pady=(7, 0))

    @staticmethod
    def tree(parent, columns, height=6):
        tree = ttk.Treeview(parent, columns=tuple(row[0] for row in columns), show="headings", selectmode="browse", height=height)
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=45, stretch=True)
        return tree

    def build_cart(self):
        frame = ttk.Frame(self.sale_tab, style="Card.TFrame")
        frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.cart_tree = self.tree(frame, (("product", "Carrito · Producto", 260), ("price", "Precio", 100), ("quantity", "Cantidad", 75), ("subtotal", "Subtotal", 115)), height=3)
        self.cart_tree.pack(fill="x")
        actions = ttk.Frame(frame, style="Card.TFrame")
        actions.pack(fill="x", pady=(8, 0))
        for label, command in (("＋", lambda: self.change_quantity(1)), ("−", lambda: self.change_quantity(-1)), ("Cantidad", self.enter_quantity), ("Quitar", self.remove_item), ("Vaciar", self.clear_cart)):
            ttk.Button(actions, text=label, command=command, width=8).pack(side="left", padx=(0, 5))
        ttk.Label(actions, textvariable=self.total, font=(UI_FONT, 15, "bold"), foreground=COLORS["primary"]).pack(side="left", padx=8)
        self.pay_button = ttk.Button(actions, text="COBRAR", command=self.checkout, style="Primary.TButton")
        self.pay_button.pack(side="right")
        feedback = ttk.Frame(frame, style="Card.TFrame")
        feedback.pack(fill="x", pady=(6, 0))
        ttk.Button(feedback, text="Revisar carrito", command=self.revalidate_cart).pack(side="right", padx=(8, 0))
        ttk.Label(feedback, textvariable=self.status, style="CardMuted.TLabel", wraplength=510).pack(side="left", anchor="w")

    def build_history(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(tab, text="Historial de ventas" if self.administrator else "Mis ventas")
        self.history_tab = tab
        self.period = tk.StringVar(value="Hoy")
        self.date_from, self.date_to = tk.StringVar(), tk.StringVar()
        self.employee_filter, self.product_filter, self.client_filter = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.employees, self.history_products, self.history_clients = {}, {}, {}
        filters = ttk.Frame(tab, style="Card.TFrame")
        filters.pack(fill="x", pady=(0, 8))
        ttk.Combobox(filters, textvariable=self.period, values=("Hoy", "Semana", "Mes", "Rango", "Últimos 2 años"), state="readonly", width=14).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        for column, (label, variable) in enumerate((("Desde AAAA-MM-DD", self.date_from), ("Hasta AAAA-MM-DD", self.date_to)), 1):
            group = ttk.Frame(filters, style="Card.TFrame")
            group.grid(row=0, column=column, sticky="ew", padx=5)
            ttk.Label(group, text=label, style="CardMuted.TLabel").pack(anchor="w")
            ttk.Entry(group, textvariable=variable, width=13).pack(fill="x")
        ttk.Button(filters, text="Consultar", command=self.refresh_history).grid(row=0, column=3, sticky="s", padx=5)
        details = ttk.Frame(tab, style="Card.TFrame")
        details.pack(fill="x", pady=(0, 8))
        column = 0
        if self.administrator:
            ttk.Label(details, text="Empleado", style="CardMuted.TLabel").grid(row=0, column=column, sticky="w")
            self.employee_combo = ttk.Combobox(details, textvariable=self.employee_filter, state="readonly", width=20)
            self.employee_combo.grid(row=1, column=column, sticky="ew", padx=(0, 8))
            details.columnconfigure(column, weight=1)
            column += 1
        for label, variable, attr in (("Producto", self.product_filter, "history_product_combo"), ("Cliente", self.client_filter, "history_client_combo")):
            ttk.Label(details, text=label, style="CardMuted.TLabel").grid(row=0, column=column, sticky="w")
            combo = ttk.Combobox(details, textvariable=variable, state="readonly", width=20)
            combo.grid(row=1, column=column, sticky="ew", padx=(0, 8))
            setattr(self, attr, combo)
            details.columnconfigure(column, weight=1)
            column += 1
        self.history_tree = self.tree(tab, (("date", "Fecha", 145), ("number", "Venta", 100), ("products", "Productos / cantidades", 240), ("total", "Total", 110), ("method", "Pago", 110), ("actor", "Empleado / rol", 160), ("status", "Estado", 100)), height=9)
        self.history_tree.pack(fill="both", expand=True)
        self.history_tree.bind("<Double-1>", lambda _: self.selected_receipt())
        actions = ttk.Frame(tab, style="Card.TFrame")
        actions.pack(fill="x", pady=(9, 0))
        ttk.Button(actions, text="Ver comprobante", command=self.selected_receipt).pack(side="left")
        if self.administrator:
            ttk.Button(actions, text="Anular venta…", command=self.void_order).pack(side="left", padx=8)
        ttk.Button(actions, text="Consultar cobro pendiente", command=self.resolve_pending).pack(side="left", padx=8)

    def build_stats(self):
        self.stats_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=12)
        self.notebook.add(self.stats_tab, text="Estadísticas tienda")
        ttk.Label(self.stats_tab, text="Ingresos exclusivos de tienda. El rango se toma del historial de ventas.", style="CardMuted.TLabel", wraplength=600).pack(anchor="w")
        ttk.Button(self.stats_tab, text="Actualizar estadísticas", command=self.refresh_stats).pack(anchor="w", pady=8)
        self.stats_text = tk.StringVar(value="Consulta los resultados para ver ingresos, productos vendidos y existencias.")
        ttk.Label(self.stats_tab, textvariable=self.stats_text, justify="left", wraplength=650, font=(UI_FONT, 11)).pack(anchor="w", pady=8)
        self.top_tree = self.tree(self.stats_tab, (("product", "Más vendidos", 250), ("quantity", "Unidades", 100), ("total", "Ingresos", 140)), height=5)
        self.top_tree.pack(fill="both", expand=True)

    def build_settings(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=14)
        self.notebook.add(tab, text="Configuración tienda")
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tab, text="Tienda habilitada para este gimnasio", variable=self.enabled_var).pack(anchor="w")
        ttk.Label(tab, text="Al deshabilitarla, se bloquean las ventas en el servidor. El historial permanece disponible.", style="CardMuted.TLabel", wraplength=580).pack(anchor="w", pady=10)
        ttk.Button(tab, text="Guardar configuración", command=self.configure_store, style="Primary.TButton").pack(anchor="w")

    def tag_widgets(self, widget=None):
        widget = widget or self.owner
        widget._hid_scanner = self
        tags = widget.bindtags()
        if self._scan_tag not in tags:
            widget.bindtags((self._scan_tag, *tags))
        for child in widget.winfo_children():
            self.tag_widgets(child)

    def _tag_event(self, _=None):
        if self.winfo_exists():
            self.tag_widgets()

    def _destroy(self, event):
        if event.widget is not self:
            return
        self.winfo_toplevel().unbind_class(self._scan_tag, "<KeyPress>")
        self.winfo_toplevel().unbind_class(self._scan_tag, "<FocusOut>")
        if self._map_binding:
            self.owner.unbind("<Map>", self._map_binding)

    def reset_scanner(self, _=None):
        self.scanner.reset()
        self._scan_origin = None

    def key(self, event):
        if (not self.sale_tab.winfo_viewable() or not self.owner.winfo_viewable()
                or not event.widget.winfo_viewable()
                or self.winfo_toplevel().grab_current() is not None
                or event.widget.winfo_toplevel() is not self.winfo_toplevel()
                or event.state & (0x4 | 0x8)):
            self.reset_scanner()
            return
        widget = event.widget
        if self._scan_origin is not widget:
            self.reset_scanner()
            self._scan_origin = widget
        is_search = getattr(widget, "_pos_search", False)
        if isinstance(widget, (ttk.Entry, tk.Entry, tk.Text, ttk.Combobox, tk.Spinbox, ttk.Spinbox)) and not is_search:
            self.reset_scanner()
            return
        if event.keysym in ("Return", "KP_Enter"):
            code = self.scanner.finish()
            if code is None and is_search:
                code = widget.get().strip()
            if code:
                self.process_barcode(code)
                return "break"
            return
        character = str(event.char or "")
        if character and character.isprintable():
            self.scanner.feed(character)
        elif event.keysym not in ("Shift_L", "Shift_R"):
            self.reset_scanner()

    def process_barcode(self, code):
        try:
            product = self.catalog.exact(code)
            if product is None:
                raise ValueError(f"No se encontró un producto activo para {code}.")
            self.add_product(product)
        except ValueError as error:
            self.status.set(str(error))
            self.bell()
        finally:
            self.reset_scanner()
            if self.external_catalog:
                if self.owner.search.get():
                    self.owner.search.set("")
                    self.owner.refresh_products()
            else:
                if self.search.get():
                    self.search.set("")

    def render_products(self):
        term = self.owner.search.get() if self.external_catalog else self.search.get()
        limit = 50 if self.external_catalog else 200
        matches = self.catalog.search(term, limit=limit + 1)
        rows = matches[:limit]
        self.catalog_notice.set(f"Mostrando los primeros {limit} productos. Refina la búsqueda por nombre, código o categoría para ver los demás." if len(matches) > limit else "")
        if self.external_catalog:
            self.owner._render_refresh_products(rows)
            self.tag_widgets()
            return
        self.product_tree.delete(*self.product_tree.get_children())
        for row in rows:
            self.product_tree.insert("", "end", iid=str(row["id"]), values=(row.get("name"), row.get("barcode") or row.get("sku") or "—", row.get("category") or "—", money(row.get("sale_price")), row.get("stock_quantity", 0)))

    def set_products(self, rows):
        if not self.enabled:
            rows = []
        self.catalog.replace(records(rows))
        self.history_products = {str(p.get("name")): int(p["id"]) for p in self.catalog.products.values()}
        self.history_product_combo.configure(values=("", *sorted(self.history_products)))
        self.render_products()
        if self.administrator:
            self.render_admin_products()

    def render_admin_products(self):
        term = self.owner.search.get().strip().casefold()
        rows = []
        for product in self.catalog.products.values():
            if term in " ".join(str(product.get(key) or "") for key in ("name", "sku", "barcode", "category")).casefold():
                rows.append(product)
                if len(rows) > 200:
                    break
        self.owner.product_notice.set("Mostrando los primeros 200 productos. Refina la búsqueda para ver los demás." if len(rows) > 200 else "")
        self.owner._render_refresh_products(rows[:200])

    def refresh(self):
        self.owner.load_view("pos_settings", self.db.pos_settings, self.settings_loaded)
        self.refresh_history()
        if self.administrator:
            self.refresh_stats()

    def settings_loaded(self, data):
        self.render_settings(data)
        if self.enabled:
            self.owner.load_view("pos_products", lambda: self.db.pos_products(include_inactive=self.administrator), self.set_products)

    def render_settings(self, data):
        if not isinstance(data, dict):
            return
        self.enabled = bool(data.get("enabled", True))
        if self.administrator:
            self.enabled_var.set(self.enabled)
        self.pay_button.configure(state="normal" if self.enabled or self.pending else "disabled")
        if not self.enabled:
            self.catalog.replace([])
            self.render_products()
            if hasattr(self.owner, "products_tree"):
                self.owner._render_refresh_products([])
            for key in ("pos_products", "refresh_products"):
                self.owner._view_errors.discard(key)
                self.owner._view_error_details.pop(key, None)
            if not self.owner._view_pending and not self.owner._view_errors:
                self.owner._view_status.set("")
            self.status.set("La tienda está deshabilitada en este gimnasio.")

    def configure_store(self):
        try:
            data = self.db.pos_configure(self.enabled_var.get())
        except Exception as error:
            messagebox.showerror("No se pudo guardar", friendly_error(error), parent=self)
            return
        self.render_settings(data if isinstance(data, dict) else {"enabled": self.enabled_var.get()})
        self.owner.refresh()
        messagebox.showinfo("Configuración guardada", "Se actualizó la disponibilidad de Tienda.", parent=self)

    def add_selected(self):
        selection = self.product_tree.selection()
        if selection:
            self.add_product(self.catalog.products[int(selection[0])])

    def add_product(self, product):
        if self.pending_error:
            self.status.set(self.pending_error)
            return
        if self.pending:
            self.status.set("Confirma primero el resultado del cobro pendiente.")
            return
        if not self.enabled:
            self.status.set("La tienda está deshabilitada.")
            return
        try:
            self.cart.add(product)
        except ValueError as error:
            self.status.set(str(error))
            self.bell()
            return
        self.render_cart()
        self.status.set(f"{product.get('name', 'Producto')} agregado. Puedes seguir escaneando.")

    def render_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for product_id, row in self.cart.rows.items():
            self.cart_tree.insert("", "end", iid=str(product_id), values=(row["product"].get("name"), money(row["unit_price"]), row["quantity"], money(row["subtotal"])))
        self.total.set(money(self.cart.total))
        self.pay_button.configure(text="COBRO PENDIENTE" if self.pending else "COBRAR")

    def selected_cart_row(self):
        if self.pending:
            self.status.set("El cobro pendiente conserva sus productos y cantidades.")
            return None
        selection = self.cart_tree.selection()
        return self.cart.rows.get(int(selection[0])) if selection else None

    def change_quantity(self, delta):
        row = self.selected_cart_row()
        if row:
            self.set_quantity(row, row["quantity"] + delta)

    def set_quantity(self, row, quantity):
        try:
            self.cart.set_quantity(row["product"], quantity)
        except ValueError as error:
            self.status.set(str(error))
            return
        self.render_cart()
        product_id = str(row["product"]["id"])
        if self.cart_tree.exists(product_id):
            self.cart_tree.selection_set(product_id)

    def enter_quantity(self):
        row = self.selected_cart_row()
        if row:
            quantity = simpledialog.askinteger("Cantidad", "Cantidad de unidades:", initialvalue=row["quantity"], minvalue=0, parent=self)
            if quantity is not None:
                self.set_quantity(row, quantity)

    def remove_item(self):
        row = self.selected_cart_row()
        if row:
            self.set_quantity(row, 0)

    def clear_cart(self):
        if self.pending:
            self.status.set("Confirma primero el resultado del cobro pendiente.")
        elif self.cart.rows and messagebox.askyesno("Vaciar carrito", "¿Quitar todos los productos del carrito?", parent=self):
            self.cart.clear()
            self.render_cart()

    def checkout(self):
        if self.pending_error:
            messagebox.showerror("Revisa el cobro pendiente", self.pending_error, parent=self)
            return
        if not self.cart.rows and not self.pending:
            self.status.set("Agrega un producto antes de cobrar.")
            return
        if not self.enabled and not self.pending:
            return
        dialog = CheckoutDialog(self)
        self.wait_window(dialog)

    def begin_checkout(self, payload):
        attempt = CheckoutAttempt(payload)
        if self.journal is not None:
            self.journal.save(attempt)
        self.pending = attempt
        self.render_cart()

    def reject_checkout(self):
        """Only GS001 after the server's request lock proves no charge was made."""
        if self.journal is not None and self.pending is not None:
            try:
                self.journal.clear(self.pending.request_id)
            except (ValueError, OSError, RuntimeError) as error:
                self.pending_error = str(error)
                return False
        self.pending = None
        self.render_cart()
        self.status.set("Venta rechazada sin cobro. Revisa el carrito para actualizar precio o existencias.")
        return True

    def revalidate_cart(self):
        if self.pending is not None or self.pending_error:
            self.status.set("Confirma primero el resultado del cobro pendiente.")
            return False
        if not self.cart.rows:
            self.status.set("El carrito está vacío.")
            return False
        try:
            rows = self.db.pos_products(include_inactive=self.administrator)
            latest = {int(row["id"]): row for row in records(rows)}
            updated, changes = Cart(), []
            for product_id, row in self.cart.rows.items():
                product = latest.get(product_id)
                if product is None or not product.get("active", True):
                    changes.append(f"{row['product'].get('name')}: se quitará porque no está disponible.")
                    continue
                quantity = min(row["quantity"], int(product.get("stock_quantity") or 0))
                if quantity != row["quantity"]:
                    changes.append(f"{product.get('name')}: cantidad {row['quantity']} → {quantity} por existencias.")
                if int(product.get("sale_price") or 0) != row["unit_price"]:
                    changes.append(f"{product.get('name')}: precio {money(row['unit_price'])} → {money(product.get('sale_price'))}.")
                updated.set_quantity(product, quantity)
        except Exception as error:
            messagebox.showerror("No se pudo revisar el carrito", friendly_error(error), parent=self)
            return False
        if changes and not messagebox.askyesno("Actualizar carrito", "\n".join(changes) + "\n\n¿Aplicar estos cambios?", parent=self):
            return False
        self.cart = updated
        self.set_products(rows)
        self.render_cart()
        self.status.set("Carrito revisado con los precios y existencias del servidor.")
        return True

    def checkout_total(self):
        if self.pending is not None:
            return sum(int(item["quantity"]) * int(item["expected_price"]) for item in self.pending.payload["items"])
        return self.cart.total

    def restore_journal(self):
        cloud = getattr(self.owner.app, "cloud", None)
        gym_id, user_id = getattr(cloud, "gym_id", None), getattr(cloud, "user_id", None)
        # UI test shells without authenticated accounts never write local files.
        if not isinstance(gym_id, str) or not isinstance(user_id, str) or not user_id:
            return
        folder = getattr(self.owner.app, "data_dir", None)
        if not isinstance(folder, (str, Path)):
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) if sys.platform == "win32" else Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
            folder = base / "GymSoft" / str(gym_id)
        try:
            self.journal = PendingCheckout(folder, gym_id, user_id)
            self.pending = self.journal.load()
            if self.pending is not None:
                payload = self.pending.payload
                if not isinstance(payload.get("items"), list) or not payload["items"] or not isinstance(payload.get("payment"), dict):
                    raise ValueError("El cobro pendiente no contiene productos o pago válidos. Consulta el historial antes de continuar.")
                if any(not isinstance(item, dict) or not all(isinstance(item.get(key), int) and not isinstance(item.get(key), bool) for key in ("product_id", "quantity", "expected_price")) for item in payload["items"]):
                    raise ValueError("Los productos del cobro pendiente no son válidos. Consulta el historial antes de continuar.")
        except (ValueError, OSError, RuntimeError) as error:
            self.pending_error = str(error)
            self.status.set(self.pending_error)
        try:
            self.inventory_journal = PendingCheckout(Path(folder) / "inventory", gym_id, user_id)
            self.inventory_pending = self.inventory_journal.load()
            if self.inventory_pending is not None:
                payload = self.inventory_pending.payload
                if not isinstance(payload.get("arguments"), dict) or not isinstance(payload.get("product"), dict) or not all(key in payload["arguments"] for key in ("product_id", "mode", "quantity", "reason", "unit_cost", "expected_stock")):
                    raise ValueError("El movimiento pendiente no contiene datos válidos. Consulta el historial de inventario.")
        except (ValueError, OSError, RuntimeError) as error:
            self.inventory_error = str(error)
        if self.pending is not None and not self.pending_error:
            self.total.set(money(self.checkout_total()))
            self.pay_button.configure(text="COBRO PENDIENTE")
            self.status.set("Hay un cobro pendiente de confirmar de una sesión anterior. Consulta su resultado antes de continuar.")

    def complete_checkout(self, result):
        if self.journal is not None and self.pending is not None:
            try:
                self.journal.clear(self.pending.request_id)
            except (ValueError, OSError, RuntimeError) as error:
                self.pending_error = str(error)
                self.status.set("Venta confirmada; no se pudo cerrar su registro local. " + str(error))
                messagebox.showerror("Venta confirmada", self.status.get(), parent=self)
                return
        self.pending = None
        self.cart.clear()
        self.render_cart()
        self.status.set("Venta confirmada por el servidor. Lista para el siguiente cliente.")
        self.refresh()
        if hasattr(self.owner, "refresh_sales"):
            self.owner.refresh_sales()

    def history_filters(self):
        filters = {"limit": 300}
        period = self.period.get()
        if period in ("Hoy", "Semana", "Mes"):
            today = business_today(self.owner)
            if isinstance(today, str):
                today = date.fromisoformat(today[:10])
            start = today if period == "Hoy" else today - timedelta(days=today.weekday()) if period == "Semana" else today.replace(day=1)
            filters.update(date_from=start.isoformat(), date_to=today.isoformat())
        elif period == "Rango":
            first, last = date.fromisoformat(self.date_from.get().strip()), date.fromisoformat(self.date_to.get().strip())
            if first > last:
                raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
            filters.update(date_from=first.isoformat(), date_to=last.isoformat())
        elif period == "Últimos 2 años":
            today = business_today(self.owner)
            if isinstance(today, str):
                today = date.fromisoformat(today[:10])
            filters.update(date_from=(today - timedelta(days=730)).isoformat(), date_to=today.isoformat())
        for key, variable, mapping in (("employee_id", self.employee_filter, self.employees), ("product_id", self.product_filter, self.history_products), ("client_id", self.client_filter, self.history_clients)):
            value = mapping.get(variable.get())
            if value is not None:
                filters[key] = value
        return filters

    def refresh_history(self):
        try:
            filters = self.history_filters()
        except (ValueError, TypeError) as error:
            messagebox.showwarning("Revisa las fechas", str(error), parent=self)
            return
        self.owner.load_view("pos_history", lambda: self.db.pos_history(filters), self.render_history, (str(filters),))

    def render_history(self, rows):
        self.history_tree.delete(*self.history_tree.get_children())
        self.history_rows = {}
        for row in records(rows):
            order_id = str(row.get("id") or row.get("order_id"))
            self.history_rows[order_id] = row
            payment = row.get("payment") or {}
            items = ", ".join(f"{item.get('product_name') or item.get('name', '')} ×{item.get('quantity', 0)}" for item in row.get("items", []))
            actor = str(row.get("actor_email") or "Sistema")
            role = "Recepción" if row.get("actor_role") == "receptionist" else "Admin"
            self.history_tree.insert("", "end", iid=order_id, values=(display_timestamp(row.get("sold_at", ""), timezone_for(self.db)), row.get("number") or row.get("sale_number"), items, money(row.get("total_amount")), payment.get("method") or row.get("payment_method"), f"{actor} · {role}", row.get("status")))
            employee = row.get("sold_by") or row.get("actor_id")
            if employee:
                self.employees[actor] = employee
            if row.get("client_id"):
                self.history_clients[row.get("customer_name") or "Cliente " + str(row["client_id"])] = row["client_id"]
        if self.administrator:
            self.employee_combo.configure(values=("", *sorted(self.employees)))
        self.history_client_combo.configure(values=("", *sorted(self.history_clients)))

    def selected_order(self):
        selected = self.history_tree.selection()
        return self.history_rows.get(selected[0]) if selected else None

    def selected_receipt(self):
        order = self.selected_order()
        if order:
            self.show_receipt(order)

    def show_receipt(self, order):
        payment = order.get("payment") or {}
        lines = [f"Venta: {order.get('number') or order.get('sale_number') or order.get('id')}",
                 display_timestamp(order.get("sold_at", ""), timezone_for(self.db)), ""]
        lines += [f"{row.get('product_name') or row.get('name', '')} ×{row.get('quantity')}   {money(row.get('line_total', row.get('total_amount', int(row.get('unit_price') or 0) * int(row.get('quantity') or 0))))}" for row in order.get("items", [])]
        lines += ["", "TOTAL: " + money(order.get("total_amount")), "Pago: " + str(payment.get("method") or order.get("payment_method") or ""), "Estado: " + str(order.get("status") or "CONFIRMED")]
        if (payment.get("method") or order.get("payment_method")) == "EFECTIVO":
            lines += ["Recibido: " + money(payment.get("received", order.get("cash_received"))), "Cambio: " + money(payment.get("change_amount", order.get("change_amount")))]
        messagebox.showinfo("Comprobante de tienda", "\n".join(lines), parent=self)

    def void_order(self):
        order = self.selected_order()
        if not order:
            return
        reason = simpledialog.askstring("Anular venta", "Motivo obligatorio de la anulación y devolución de existencias:", parent=self)
        if not reason or not reason.strip():
            return
        if not messagebox.askyesno("Anular venta", "Se conservará la venta anulada y se devolverán sus existencias. ¿Continuar?", parent=self):
            return
        try:
            self.db.pos_void(order.get("id") or order.get("order_id"), reason.strip())
        except Exception as error:
            messagebox.showerror("No se pudo anular", friendly_error(error), parent=self)
            return
        self.refresh()
        if hasattr(self.owner, "refresh_sales"):
            self.owner.refresh_sales()

    def resolve_pending(self):
        if self.pending is None:
            messagebox.showinfo("Cobros", "No hay un cobro pendiente en este equipo.", parent=self)
            return
        try:
            rows = self.db.pos_history({"request_id": self.pending.request_id, "limit": 10})
        except Exception as error:
            messagebox.showerror("No se pudo consultar", friendly_error(error), parent=self)
            return
        order = next((row for row in records(rows) if str(row.get("request_id") or "") == self.pending.request_id), None)
        if order is not None:
            self.complete_checkout(order)
            self.show_receipt(order)
        else:
            messagebox.showinfo("Cobro pendiente", "El servidor aún no devuelve esta venta. Usa COBRO PENDIENTE para reintentar exactamente el mismo cobro.", parent=self)

    def refresh_stats(self):
        try:
            filters = self.history_filters()
        except (ValueError, TypeError):
            return
        self.owner.load_view("pos_stats", lambda: self.db.pos_stats(filters), self.render_stats, (str(filters),))

    def render_stats(self, data):
        if not isinstance(data, dict):
            return
        def summary(value, period):
            if isinstance(value, dict):
                return f"{value.get('sales_count', value.get('count', 0))} ventas · {money(value.get('income', value.get('total_amount', 0)))}"
            return f"{data.get(period + '_count', 0)} ventas · {money(value)}"
        low, empty = data.get("low_stock", []), data.get("out_of_stock", [])
        count = lambda value: len(value) if isinstance(value, list) else int(value or 0)
        profit = "Sin costos fiables para estimar utilidad" if data.get("gross_profit") is None else money(data["gross_profit"])
        self.stats_text.set(f"Hoy: {summary(data.get('today'), 'today')}\nSemana: {summary(data.get('week'), 'week')}\nMes: {summary(data.get('month'), 'month')}\n\nIngresos tienda (rango): {money(data.get('store_income'))}\nUnidades vendidas: {data.get('units_sold', 0)}\nUtilidad bruta estimada: {profit}\nStock bajo: {count(low)} · Agotados: {count(empty)}")
        self.top_tree.delete(*self.top_tree.get_children())
        for row in records(data.get("top_products")):
            self.top_tree.insert("", "end", values=(row.get("product_name") or row.get("name"), row.get("quantity", row.get("units_sold", 0)), money(row.get("revenue", row.get("total_amount", row.get("income", 0))))))

    def inventory(self, product):
        if self.inventory_error:
            messagebox.showerror("Revisa el movimiento pendiente", self.inventory_error, parent=self)
            return
        if self.inventory_pending is not None:
            product = self.inventory_pending.payload["product"]
        dialog = InventoryDialog(self, product)
        self.wait_window(dialog)
        if dialog.result:
            self.owner.refresh()


class InventoryDialog(PosDialog):
    def __init__(self, panel, product):
        if panel.inventory_pending is not None:
            product = panel.inventory_pending.payload["product"]
        super().__init__(panel, "Recibir / ajustar inventario", 560, 670)
        self.panel, self.product = panel, product
        self.mode = tk.StringVar(value="RECEIVE")
        self.code = tk.StringVar()
        self.quantity, self.cost, self.reason = tk.StringVar(value="1"), tk.StringVar(), tk.StringVar()
        self.request_id = None
        self.frozen = None
        self.submitting = False
        self.product_name = ttk.Label(self.body, text=product.get("name", ""), font=(UI_FONT, 15, "bold"))
        self.product_name.grid(row=0, column=0, sticky="w")
        self.stock_label = ttk.Label(self.body, text=f"Existencias actuales: {product.get('stock_quantity', 0)}", style="CardMuted.TLabel")
        self.stock_label.grid(row=1, column=0, sticky="w", pady=(5, 12))
        scan = self.field("Escanear / escribir código de otro producto", self.code, 1)
        scan.bind("<Return>", self.scan_product)
        modes = ttk.Frame(self.body, style="Surface.TFrame")
        modes.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Radiobutton(modes, text="Recibir unidades", variable=self.mode, value="RECEIVE").pack(anchor="w")
        ttk.Radiobutton(modes, text="Ajustar al conteo físico", variable=self.mode, value="ADJUST").pack(anchor="w")
        self.quantity_entry = self.field("Unidades recibidas / conteo físico final", self.quantity, 3)
        self.cost_entry = self.field("Costo unitario (opcional)", self.cost, 4)
        self.reason_entry = self.field("Motivo / referencia de compra", self.reason, 5)
        ttk.Label(self.body, text="Cada operación conserva stock anterior, stock posterior, motivo y usuario. El ajuste exige un motivo.", style="CardMuted.TLabel", wraplength=450).grid(row=12, column=0, sticky="ew", pady=12)
        self.confirm = ttk.Button(self.body, text="Confirmar movimiento", command=self.save, style="Primary.TButton")
        self.confirm.grid(row=13, column=0, sticky="e")
        self.movements = StorePosPanel.tree(self.body, (("type", "Tipo", 90), ("quantity", "Cantidad", 70), ("before", "Antes", 65), ("after", "Después", 65), ("date", "Fecha", 145)), height=5)
        self.movements.grid(row=14, column=0, sticky="ew", pady=(16, 0))
        self.after_idle(self.load_movements)
        self.after_idle(scan.focus_set)
        self.inputs = [scan, self.quantity_entry, self.cost_entry, self.reason_entry, *modes.winfo_children()]
        if panel.inventory_pending is not None:
            self.request_id = panel.inventory_pending.request_id
            self.frozen = panel.inventory_pending.payload["arguments"]
            self.mode.set(self.frozen["mode"])
            self.quantity.set(str(self.frozen["quantity"]))
            self.cost.set("" if self.frozen["unit_cost"] is None else str(self.frozen["unit_cost"]))
            self.reason.set(self.frozen["reason"])
            self.freeze_inputs()

    def freeze_inputs(self):
        for widget in self.inputs:
            widget.configure(state="disabled")
        self.confirm.configure(text="Reintentar mismo movimiento")

    def clear_pending(self):
        attempt = self.panel.inventory_pending
        if attempt is not None and self.panel.inventory_journal is not None:
            self.panel.inventory_journal.clear(attempt.request_id)
        self.panel.inventory_pending = None

    def scan_product(self, _=None):
        if self.frozen is not None:
            messagebox.showwarning("Movimiento pendiente", "Confirma el resultado del movimiento antes de cambiar de producto.", parent=self)
            return "break"
        code = self.code.get().strip()
        products = self.panel.catalog.products.values()
        matches = [row for row in products if row.get("barcode") == code or str(row.get("sku") or "").casefold() == code.casefold()]
        if not code or len(matches) != 1:
            messagebox.showwarning("Código no encontrado", "Selecciona un código que identifique un producto de este gimnasio.", parent=self)
            return "break"
        self.product = matches[0]
        self.product_name.configure(text=self.product.get("name", ""))
        self.stock_label.configure(text=f"Existencias actuales: {self.product.get('stock_quantity', 0)}")
        self.movements.delete(*self.movements.get_children())
        self.load_movements()
        self.code.set("")
        self.quantity_entry.focus_set()
        return "break"

    def load_movements(self):
        try:
            rows = self.panel.db.pos_movements(self.product["id"])
        except Exception as error:
            messagebox.showerror("No se pudieron cargar los movimientos", friendly_error(error), parent=self)
            return
        for row in records(rows):
            self.movements.insert("", "end", values=(row.get("movement_type") or row.get("type"), row.get("quantity"), row.get("stock_before"), row.get("stock_after"), display_timestamp(row.get("created_at", ""), timezone_for(self.panel.db))))
        confirmed = next((row for row in records(rows) if self.request_id and str(row.get("request_id") or "") == self.request_id), None)
        if confirmed is not None:
            try:
                self.clear_pending()
            except (ValueError, OSError, RuntimeError) as error:
                messagebox.showerror("Movimiento confirmado", "El servidor confirmó el movimiento, pero no se pudo cerrar su registro local.\n" + str(error), parent=self)
                return
            self.result = dict(stock_after=confirmed.get("stock_after"), movement=confirmed)
            messagebox.showinfo("Movimiento confirmado", "El movimiento pendiente ya figura en el inventario. No se registró otra entrada.", parent=self)
            self.destroy()

    def save(self):
        if self.submitting:
            return
        try:
            quantity = int(self.quantity.get())
            if quantity < 0 or self.mode.get() == "RECEIVE" and quantity == 0:
                raise ValueError("La cantidad no es válida.")
            reason = self.reason.get().strip()
            if self.mode.get() == "ADJUST" and not reason:
                raise ValueError("Escribe el motivo del ajuste.")
            cost = parse_amount(self.cost.get()) if self.cost.get().strip() else None
            if cost is not None and cost < 0:
                raise ValueError("El costo debe ser cero o positivo.")
            payload = dict(product_id=self.product["id"], mode=self.mode.get(), quantity=quantity, reason=reason, unit_cost=cost, expected_stock=int(self.product.get("stock_quantity") or 0))
            if self.frozen is not None and self.frozen != payload:
                raise ValueError("El resultado está pendiente. Reintenta con los mismos datos y consulta los movimientos antes de cambiarlo.")
        except ValueError as error:
            messagebox.showwarning("Revisa el movimiento", str(error), parent=self)
            return
        if self.panel.inventory_pending is None:
            attempt = CheckoutAttempt(dict(arguments=payload, product=self.product))
            try:
                if self.panel.inventory_journal is not None:
                    self.panel.inventory_journal.save(attempt)
            except (ValueError, OSError, RuntimeError) as error:
                messagebox.showerror("No se pudo preparar el movimiento", str(error), parent=self)
                return
            self.panel.inventory_pending = attempt
        self.request_id = self.panel.inventory_pending.request_id
        self.frozen = self.panel.inventory_pending.payload["arguments"]
        self.freeze_inputs()
        self.submitting = True
        self.confirm.configure(state="disabled")
        try:
            result = self.panel.db.pos_inventory(**self.frozen, request_id=self.request_id)
            if not isinstance(result, dict) or "stock_after" not in result:
                raise RuntimeError("El servidor no confirmó el movimiento. Consulta o reintenta la misma operación.")
        except Exception as error:
            if checkout_rejected(error):
                try:
                    self.clear_pending()
                except (ValueError, OSError, RuntimeError) as local_error:
                    messagebox.showerror("No se pudo cerrar el movimiento", str(local_error), parent=self)
                else:
                    messagebox.showwarning("Movimiento rechazado sin cambios", friendly_error(error) + "\nActualiza las existencias antes de volver a intentarlo.", parent=self)
                    self.destroy()
                    self.panel.owner.refresh()
            else:
                messagebox.showerror("Movimiento no confirmado", friendly_error(error) + "\nSe conserva la misma operación aunque cierres la ventana. Consulta o reintenta para evitar duplicados.", parent=self)
        else:
            try:
                self.clear_pending()
            except (ValueError, OSError, RuntimeError) as error:
                messagebox.showerror("Movimiento confirmado", "No se pudo cerrar su registro local. Consulta antes de registrar otra entrada.\n" + str(error), parent=self)
            else:
                self.result = result
                self.destroy()
        finally:
            self.submitting = False
            if self.winfo_exists():
                self.confirm.configure(state="normal")
