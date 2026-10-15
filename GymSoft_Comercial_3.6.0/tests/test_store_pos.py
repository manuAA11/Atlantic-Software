"""POS core contracts without a display, network service, or physical scanner.

The RPC tests use a transport double. They do not establish PostgreSQL
transactions, server permissions, concurrent sessions, or HID hardware support.
"""
from copy import deepcopy
import json
import multiprocessing
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from store_pos import (Cart, CheckoutAttempt, PAYMENT_METHODS, PendingCheckout,
                       ProductCatalog, ScannerBuffer, StoreDatabaseMixin,
                       barcode_value, cash_change, checkout_rejected)


def product(product_id=1, **changes):
    value = dict(id=product_id, name="Coca-Cola", description="Bebida fría",
                 sku=f"REF-{product_id}", barcode=f"007701234{product_id:04d}",
                 category="Bebidas", sale_price=4000, cost=2000,
                 stock_quantity=3, stock_minimum=1, active=True)
    value.update(changes)
    return value


def hold_checkout_journal_lock(folder, connection):
    """Spawn target: hold the actual operating-system lock until released."""
    with PendingCheckout(folder, "gym-a", "employee-a")._lock():
        connection.send("locked")
        connection.recv()
    connection.close()


def race_checkout_journal_save(folder, payload, request_id, connection):
    """Spawn target: compete to create a pending checkout from another process."""
    journal = PendingCheckout(folder, "gym-a", "employee-a")
    connection.send("ready")
    connection.recv()
    try:
        journal.save(CheckoutAttempt(payload, request_id))
    except (ValueError, RuntimeError):
        connection.send(("blocked", request_id))
    else:
        connection.send(("saved", request_id))
    finally:
        connection.close()


class BarcodeCatalogTests(unittest.TestCase):
    def test_exact_barcode_retains_leading_zeroes_and_case(self):
        padded = product(barcode="0012345", sku="ABC")
        plain = product(2, barcode="12345", sku="DEF")
        lettered = product(3, barcode="AbC-123", sku="GHI")
        catalog = ProductCatalog([padded, plain, lettered])
        self.assertEqual(catalog.exact("0012345")["id"], 1)
        self.assertEqual(catalog.exact("12345")["id"], 2)
        self.assertEqual(catalog.exact("AbC-123")["id"], 3)
        self.assertIsNone(catalog.exact("abc-123"))
        self.assertEqual(catalog.exact("abc")["id"], 1)

    def test_optional_barcodes_and_manual_search_cover_all_fields(self):
        coffee = product(name="Café", barcode=None, sku="CAFE-01", category="Calientes")
        catalog = ProductCatalog([coffee, product(2)])
        for query in ("CAFÉ", "cafe-01", "calientes"):
            with self.subTest(query=query):
                self.assertEqual([p["id"] for p in catalog.search(query)], [1])
        self.assertEqual(catalog.search("0077012340002")[0]["id"], 2)
        self.assertEqual(barcode_value(None), "")
        self.assertIsNone(catalog.exact(""))

    def test_inactive_products_are_not_searchable_or_scannable(self):
        catalog = ProductCatalog([product(active=False), product(2)])
        self.assertIsNone(catalog.exact("0077012340001"))
        self.assertIsNone(catalog.exact("REF-1"))
        self.assertEqual([p["id"] for p in catalog.search()], [2])

    def test_duplicate_active_barcode_or_sku_is_reported_as_ambiguous(self):
        for field, code in (("barcode", "0012345"), ("sku", "sku-1")):
            with self.subTest(field=field):
                first, second = product(), product(2)
                first[field] = second[field] = code
                catalog = ProductCatalog([first, second])
                with self.assertRaisesRegex(ValueError, "ambiguo"):
                    catalog.exact(code)

    def test_barcode_wins_over_another_products_sku(self):
        catalog = ProductCatalog([product(barcode="ABC"), product(2, sku="ABC")])
        self.assertEqual(catalog.exact("ABC")["id"], 1)

    def test_controls_and_overlong_barcodes_are_rejected(self):
        self.assertEqual(barcode_value(" 00123 "), "00123")
        self.assertEqual(barcode_value("x" * 128), "x" * 128)
        for value in ("a\x00b", "ab\ncd", "abc\tdef", "x" * 129):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    barcode_value(value)

    def test_replace_removes_stale_indexes_and_results_are_copies(self):
        original = product()
        catalog = ProductCatalog([original])
        original["name"] = "Changed outside catalog"
        found = catalog.exact("0077012340001")
        self.assertEqual(found["name"], "Coca-Cola")
        found["name"] = "Changed returned row"
        catalog.search()[0]["barcode"] = "Changed returned search"
        self.assertEqual(catalog.exact("0077012340001")["name"], "Coca-Cola")
        catalog.replace([product(2)])
        self.assertIsNone(catalog.exact("0077012340001"))
        self.assertEqual([p["id"] for p in catalog.search(limit=1)], [2])

    def test_exact_scan_with_20000_products_uses_indexes_and_stays_fast(self):
        catalog = ProductCatalog(product(i) for i in range(1, 20001))

        class NoSearchScan:
            def __iter__(self):
                raise AssertionError("An exact scan must not scan the search catalog")

        catalog.search_rows = NoSearchScan()
        started = perf_counter()
        for index in range(2000):
            product_id = 1 + (index * 97) % 20000
            self.assertEqual(catalog.exact(f"007701234{product_id:04d}")["id"], product_id)
        # A generous ceiling catches accidentally reintroduced full-catalog scans
        # while avoiding a hardware-specific submillisecond assertion in CI.
        self.assertLess(perf_counter() - started, 2.0)


class CartTests(unittest.TestCase):
    def setUp(self):
        self.cart = Cart()
        self.coke = product()

    def test_repeated_scans_share_a_row_and_increment_quantity(self):
        catalog, scanner = ProductCatalog([self.coke]), ScannerBuffer()
        for start in (10.0, 11.0):
            for offset, character in enumerate(self.coke["barcode"]):
                scanner.feed(character, start + offset * .005)
            code = scanner.finish(start + len(self.coke["barcode"]) * .005)
            self.cart.add(catalog.exact(code))
            self.assertIsNone(scanner.finish(start + .075))
        self.assertEqual(len(self.cart.rows), 1)
        self.assertEqual(self.cart.rows[1]["quantity"], 2)
        self.assertEqual(self.cart.total, 8000)

    def test_stock_cap_preserves_cart_when_addition_or_edit_fails(self):
        self.cart.add(self.coke, 3)
        previous = deepcopy(self.cart.rows)
        for action in (lambda: self.cart.add(self.coke),
                       lambda: self.cart.set_quantity(self.coke, 4)):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, "Stock disponible: 3"):
                    action()
                self.assertEqual(self.cart.rows, previous)

    def test_quantity_changes_remove_and_clear_recalculate_total(self):
        self.cart.add(self.coke, 2)
        self.cart.add(product(2, sale_price=3000))
        self.assertEqual(self.cart.total, 11000)
        self.cart.set_quantity(self.coke, 1)
        self.assertEqual(self.cart.total, 7000)
        self.cart.set_quantity(self.coke, 0)
        self.assertNotIn(1, self.cart.rows)
        self.assertEqual(self.cart.total, 3000)
        self.cart.clear()
        self.assertEqual(self.cart.total, 0)
        self.assertEqual(self.cart.items(), [])

    def test_invalid_quantities_are_rejected_by_both_entry_points(self):
        for quantity in (True, False, 1.5, "2", -1):
            for method in (self.cart.add, self.cart.set_quantity):
                with self.subTest(quantity=quantity, method=method.__name__):
                    with self.assertRaises((ValueError, TypeError)):
                        method(self.coke, quantity)
        self.assertEqual(self.cart.items(), [])

    def test_inactive_product_cannot_be_added_or_set_directly(self):
        inactive = product(active=False)
        for method in (self.cart.add, self.cart.set_quantity):
            with self.subTest(method=method.__name__):
                with self.assertRaisesRegex(ValueError, "inactivo"):
                    method(inactive, 1)
        self.assertEqual(self.cart.total, 0)

    def test_zero_stock_and_invalid_prices_do_not_create_a_row(self):
        with self.assertRaisesRegex(ValueError, "Stock disponible: 0"):
            self.cart.add(product(stock_quantity=0))
        for price in (-1, 12.5, True):
            with self.subTest(price=price):
                with self.assertRaises(ValueError):
                    self.cart.add(product(sale_price=price))
        self.assertFalse(self.cart.rows)

    def test_checkout_items_are_deterministic_price_snapshots(self):
        self.cart.add(product(20, sale_price=3000), 2)
        self.cart.add(self.coke)
        self.coke["sale_price"] = 9000
        self.assertEqual(self.cart.items(), [
            {"product_id": 1, "quantity": 1, "expected_price": 4000},
            {"product_id": 20, "quantity": 2, "expected_price": 3000},
        ])
        self.assertEqual(self.cart.total, 10000)


class ScannerBufferTests(unittest.TestCase):
    def scan(self, scanner, text, start=10.0, interval=.01):
        for index, character in enumerate(text):
            scanner.feed(character, start + index * interval)
        return scanner.finish(start + len(text) * interval)

    def test_fast_scan_is_consumed_once_then_next_identical_scan_is_allowed(self):
        scanner = ScannerBuffer()
        self.assertEqual(self.scan(scanner, "0012345"), "0012345")
        self.assertIsNone(scanner.finish(10.08))
        self.assertEqual(self.scan(scanner, "0012345", start=11.0), "0012345")

    def test_manual_typing_short_codes_and_stale_enter_are_not_scans(self):
        scanner = ScannerBuffer()
        self.assertIsNone(self.scan(scanner, "0012345", interval=.2))
        self.assertIsNone(self.scan(scanner, "12", start=12.0))
        for index, character in enumerate("0012345"):
            scanner.feed(character, 14 + index * .01)
        self.assertIsNone(scanner.finish(15))
        self.assertIsNone(scanner.finish(15.01))

    def test_average_speed_threshold_rejects_fast_but_human_typing(self):
        self.assertIsNone(self.scan(ScannerBuffer(), "0012345", interval=.06))

    def test_controls_and_explicit_context_reset_clear_pending_scan(self):
        scanner = ScannerBuffer()
        scanner.feed("0", 10)
        scanner.feed("0", 10.01)
        scanner.feed("\t", 10.02)
        scanner.feed("1", 10.03)
        self.assertIsNone(scanner.finish(10.04))
        for index, character in enumerate("0012345"):
            scanner.feed(character, 11 + index * .01)
        # The UI calls reset when focus leaves POS or a modal opens.
        scanner.reset()
        self.assertIsNone(scanner.finish(11.08))

    def test_overlong_scan_discards_whole_code_until_enter(self):
        scanner = ScannerBuffer()
        self.assertIsNone(self.scan(scanner, "x" * 132, interval=.001))
        self.assertEqual(self.scan(scanner, "0012345", start=11), "0012345")


class CheckoutAndCashTests(unittest.TestCase):
    def test_only_explicit_server_validation_code_releases_pending_checkout(self):
        rejected = Exception("Stock changed")
        rejected.code = "GS001"
        self.assertTrue(checkout_rejected(rejected))
        for code in ("P0001", "42501", "23505", "40001", "GS002", ""):
            with self.subTest(code=code):
                error = Exception("GS001 appears in text only")
                error.code = code
                self.assertFalse(checkout_rejected(error))
        self.assertFalse(checkout_rejected(TimeoutError("GS001")))
        self.assertFalse(checkout_rejected(ConnectionError("Uncertain write")))

    def test_structured_validation_code_survives_an_explicit_adapter_exception_cause(self):
        rejected = Exception("Insufficient stock")
        rejected.code = "GS001"
        wrapped = ValueError("Adapter explanation")
        wrapped.__cause__ = rejected
        self.assertTrue(checkout_rejected(wrapped))

    def test_cyclic_exception_causes_do_not_hang_rejection_classification(self):
        first, second = RuntimeError("Uncertain"), ConnectionError("Network")
        first.__cause__, second.__cause__ = second, first
        self.assertFalse(checkout_rejected(first))

    def test_exact_cash_and_change_use_integer_cop(self):
        self.assertEqual(cash_change(19000, 20000), 1000)
        self.assertEqual(cash_change(19000, 19000), 0)
        self.assertEqual(PAYMENT_METHODS, ("EFECTIVO", "TRANSFERENCIA", "TARJETA", "OTRO"))

    def test_insufficient_or_noninteger_cash_cannot_confirm(self):
        for received in (18999, -1, 20000.5, "20000", True):
            with self.subTest(received=received):
                with self.assertRaises(ValueError):
                    cash_change(19000, received)

    def test_total_cannot_be_negative_boolean_or_silently_truncated(self):
        for total in (-1, True, 19000.5, "19000"):
            with self.subTest(total=total):
                with self.assertRaises(ValueError):
                    cash_change(total, 20000)

    def test_uncertain_checkout_reuses_request_and_deep_payload_snapshot(self):
        request_id = str(uuid4())
        payload = {"items": [{"product_id": 1, "quantity": 2, "expected_price": 4000}],
                   "payment": {"method": "EFECTIVO", "received": 10000},
                   "customer_name": "", "notes": ""}
        expected = deepcopy(payload)
        attempt = CheckoutAttempt(payload, request_id=request_id)
        payload["items"][0]["quantity"] = 3
        payload["payment"]["received"] = 12000
        first = attempt.retry()
        self.assertEqual(first, dict(request_id=request_id, **expected))
        first["items"][0]["quantity"] = 99
        first["payment"]["method"] = "TARJETA"
        exposed_payload = attempt.payload
        exposed_payload["items"][0]["quantity"] = 77
        self.assertEqual(attempt.retry(expected), dict(request_id=request_id, **expected))
        with self.assertRaisesRegex(ValueError, "cobro pendiente"):
            attempt.retry(payload)

    def test_new_checkout_attempts_have_distinct_valid_request_ids(self):
        first, second = CheckoutAttempt({}), CheckoutAttempt({})
        self.assertEqual(str(UUID(first.request_id)), first.request_id)
        self.assertNotEqual(first.request_id, second.request_id)
        with self.assertRaises(ValueError):
            CheckoutAttempt({}, request_id="not-a-uuid")


class PendingCheckoutJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = PendingCheckout(self.temp.name, "gym-a", "employee-a")
        self.payload = {"items": [{"product_id": 1, "quantity": 2, "expected_price": 4000}],
                        "payment": {"method": "EFECTIVO", "received": 10000},
                        "customer_name": "Cliente opcional", "notes": "Venta rápida"}
        self.attempt = CheckoutAttempt(self.payload)

    def test_missing_journal_is_empty_without_creating_files(self):
        self.assertIsNone(self.journal.load())
        self.assertFalse(self.journal.path.exists())
        self.journal.clear(self.attempt.request_id)
        self.assertFalse(self.journal.path.exists())

    def test_restart_restores_exact_request_id_payload_and_unicode(self):
        self.journal.save(self.attempt)
        restarted = PendingCheckout(self.temp.name, "gym-a", "employee-a")
        restored = restarted.load()
        self.assertEqual(restored.retry(), self.attempt.retry())
        self.assertEqual(restored.payload, self.payload)
        self.payload["items"][0]["quantity"] = 99
        restored.payload["payment"]["method"] = "TARJETA"
        self.assertEqual(restarted.load().retry(), self.attempt.retry())
        self.assertEqual(list(self.journal.folder.glob(".checkout-*")), [])

    def test_journal_is_scoped_by_both_gym_and_employee(self):
        self.journal.save(self.attempt)
        for gym_id, user_id in (("gym-b", "employee-a"), ("gym-a", "employee-b")):
            with self.subTest(gym_id=gym_id, user_id=user_id):
                other = PendingCheckout(self.temp.name, gym_id, user_id)
                self.assertNotEqual(other.path, self.journal.path)
                self.assertIsNone(other.load())
                other.save(CheckoutAttempt(self.attempt.payload))
                self.assertEqual(self.journal.load().retry(), self.attempt.retry())

    def test_missing_identity_cannot_create_or_load_a_checkout(self):
        for gym_id, user_id in ((None, "user"), ("gym", None), ("", "user"),
                                ("gym", "  ")):
            with self.subTest(gym_id=gym_id, user_id=user_id):
                with self.assertRaises(ValueError):
                    PendingCheckout(self.temp.name, gym_id, user_id)

    def test_repeat_save_accepts_only_the_exact_existing_request_and_payload(self):
        self.journal.save(self.attempt)
        self.journal.save(self.attempt)
        changed = deepcopy(self.attempt.payload)
        changed["items"][0]["quantity"] = 3
        alternatives = (CheckoutAttempt(self.attempt.payload),
                        CheckoutAttempt(changed, self.attempt.request_id))
        for alternative in alternatives:
            with self.subTest(request_id=alternative.request_id):
                with self.assertRaisesRegex(ValueError, "cobro pendiente"):
                    self.journal.save(alternative)
                self.assertEqual(self.journal.load().retry(), self.attempt.retry())

    def test_atomic_replace_or_sync_failure_preserves_previous_journal(self):
        self.journal.save(self.attempt)
        previous = self.journal.path.read_bytes()
        for operation in ("store_pos.os.replace", "store_pos.os.fsync", "store_pos.json.dump"):
            with self.subTest(operation=operation):
                with patch(operation, side_effect=OSError("simulated disk failure")):
                    with self.assertRaises(OSError):
                        self.journal.save(self.attempt)
                self.assertEqual(self.journal.path.read_bytes(), previous)
                self.assertEqual(self.journal.load().retry(), self.attempt.retry())
                self.assertEqual(list(self.journal.folder.glob(".checkout-*")), [])

    def test_failed_first_write_is_not_mistaken_for_a_saved_pending_checkout(self):
        with patch("store_pos.os.replace", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.journal.save(self.attempt)
        self.assertIsNone(self.journal.load())
        self.assertEqual(list(self.journal.folder.glob(".checkout-*")), [])

    def test_abandoned_temporary_write_does_not_replace_confirmed_journal(self):
        self.journal.save(self.attempt)
        orphan = self.journal.folder / ".checkout-interrupted"
        orphan.write_text('{"version":', encoding="utf-8")
        restarted = PendingCheckout(self.temp.name, "gym-a", "employee-a")
        self.assertEqual(restarted.load().retry(), self.attempt.retry())

    def test_clear_requires_matching_request_id_and_is_repeatable(self):
        self.journal.save(self.attempt)
        with self.assertRaisesRegex(ValueError, "referencia pendiente cambió"):
            self.journal.clear(str(uuid4()))
        self.assertEqual(self.journal.load().retry(), self.attempt.retry())
        self.journal.clear(self.attempt.request_id)
        self.assertIsNone(self.journal.load())
        self.journal.clear(self.attempt.request_id)

    def test_corrupt_journal_blocks_loading_saving_and_clearing(self):
        self.journal.save(self.attempt)
        valid = json.loads(self.journal.path.read_text(encoding="utf-8"))
        documents = ["{broken-json", "[]", "null"]
        for field, value in (("version", 2), ("scope", "another-gym-user"),
                             ("payload", []), ("request_id", "invalid-uuid"),
                             ("request_id", ""), ("request_id", None),
                             ("request_id", False), ("request_id", 0)):
            documents.append(json.dumps(dict(valid, **{field: value})))
        missing_reference = dict(valid)
        del missing_reference["request_id"]
        documents.append(json.dumps(missing_reference))
        for document in documents:
            with self.subTest(document=document):
                self.journal.path.write_text(document, encoding="utf-8")
                for action in (self.journal.load,
                               lambda: self.journal.save(CheckoutAttempt(self.attempt.payload)),
                               lambda: self.journal.clear(self.attempt.request_id)):
                    with self.assertRaises(ValueError):
                        action()
                self.assertEqual(self.journal.path.read_text(encoding="utf-8"), document)

    def test_unreadable_journal_blocks_instead_of_creating_new_identity(self):
        with patch.object(Path, "read_text", side_effect=PermissionError("access denied")):
            with self.assertRaisesRegex(ValueError, "historial"):
                self.journal.load()

    def start_child(self, target, *arguments):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=target, args=(*arguments, child))
        process.start()
        child.close()

        def cleanup():
            if process.is_alive():
                process.terminate()
            process.join(10)
            parent.close()

        self.addCleanup(cleanup)
        self.assertTrue(parent.poll(10), "Child did not reach its journal operation")
        return process, parent

    def test_other_process_lock_blocks_same_scope_save_and_clear_only(self):
        process, connection = self.start_child(hold_checkout_journal_lock, self.temp.name)
        self.assertEqual(connection.recv(), "locked")
        for action in (lambda: self.journal.save(self.attempt),
                       lambda: self.journal.clear(self.attempt.request_id)):
            with self.assertRaisesRegex(RuntimeError, "Otra ventana"):
                action()
        self.assertIsNone(self.journal.load())
        other = PendingCheckout(self.temp.name, "gym-b", "employee-a")
        other.save(CheckoutAttempt(self.attempt.payload))
        self.assertIsNotNone(other.load())
        connection.send("release")
        process.join(10)
        self.assertEqual(process.exitcode, 0)
        self.journal.save(self.attempt)
        self.assertEqual(self.journal.load().retry(), self.attempt.retry())

    def test_abrupt_process_exit_releases_lock_without_losing_pending_sale(self):
        self.journal.save(self.attempt)
        process, connection = self.start_child(hold_checkout_journal_lock, self.temp.name)
        self.assertEqual(connection.recv(), "locked")
        process.terminate()
        process.join(10)
        self.assertFalse(process.is_alive())
        self.journal.save(self.attempt)
        self.assertEqual(self.journal.load().retry(), self.attempt.retry())
        with self.assertRaises(ValueError):
            self.journal.save(CheckoutAttempt(self.attempt.payload))

    def test_two_processes_cannot_overwrite_each_others_pending_checkout(self):
        children = [self.start_child(race_checkout_journal_save, self.temp.name,
                                    self.attempt.payload, str(uuid4())) for _ in range(2)]
        for _, connection in children:
            self.assertEqual(connection.recv(), "ready")
        for _, connection in children:
            connection.send("save")
        results = []
        for process, connection in children:
            self.assertTrue(connection.poll(10), "Child did not finish the concurrent save")
            results.append(connection.recv())
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        winners = [request_id for result, request_id in results if result == "saved"]
        self.assertEqual(len(winners), 1, results)
        self.assertEqual([result for result, _ in results].count("blocked"), 1)
        self.assertEqual(self.journal.load().request_id, winners[0])


class StoreDatabaseContractTests(unittest.TestCase):
    def setUp(self):
        self.db = StoreDatabaseMixin()
        self.db.gym_id = "gym-a"
        self.db.client = SimpleNamespace(rpc=Mock(return_value="rpc-operation"))
        self.db._execute = Mock(return_value=SimpleNamespace(data={"ok": True}))

    def assert_rpc(self, name, **parameters):
        self.db.client.rpc.assert_called_once_with(name, {"p_gym_id": "gym-a", **parameters})
        self.db._execute.assert_called_once_with("rpc-operation")

    def test_one_product_remains_a_list_just_like_zero_or_many(self):
        for rows in ([], [product()], [product(), product(2)]):
            with self.subTest(count=len(rows)):
                self.db._execute.return_value = SimpleNamespace(data=deepcopy(rows))
                self.assertEqual(self.db.pos_products(), rows)

    def test_one_history_or_movement_row_does_not_change_response_shape(self):
        for method, row in ((self.db.pos_history, {"id": "sale-a"}),
                            (self.db.pos_movements, {"id": "movement-a"})):
            with self.subTest(method=method.__name__):
                self.db._execute.return_value = SimpleNamespace(data=[row])
                self.assertEqual(method(), [row])

    def test_product_queries_are_scoped_and_include_admin_filter_explicitly(self):
        self.db.pos_products("  Agua  ", include_inactive=True)
        self.assert_rpc("store_pos_products", p_search="Agua", p_include_inactive=True)

    def test_checkout_for_each_payment_method_has_same_scoped_rpc_contract(self):
        items = [{"product_id": 1, "quantity": 2, "expected_price": 4000}]
        request_id = str(uuid4())
        for method in PAYMENT_METHODS:
            with self.subTest(method=method):
                self.db.client.rpc.reset_mock()
                self.db._execute.reset_mock()
                payment = {"method": method, "received": 10000 if method == "EFECTIVO" else 8000}
                result = self.db.pos_checkout(items, payment, customer_name="Venta rápida",
                                              notes="Mostrador", request_id=request_id)
                self.assertEqual(result, {"ok": True})
                self.assert_rpc("store_pos_checkout", p_request_id=request_id, p_items=items,
                                p_payment=payment, p_client_id=None,
                                p_customer_name="Venta rápida", p_notes="Mostrador")

    def test_checkout_requires_caller_request_id_and_rejects_invalid_uuid_before_transport(self):
        with self.assertRaises(TypeError):
            self.db.pos_checkout([], {})
        with self.assertRaises(ValueError):
            self.db.pos_checkout([], {}, request_id="invalid")
        self.db.client.rpc.assert_not_called()

    def test_inventory_retry_keeps_supplied_request_stock_and_cost(self):
        request_id = str(uuid4())
        self.db.pos_inventory(1, "PURCHASE", 24, "Compra", 2000,
                              expected_stock=10, request_id=request_id)
        self.assert_rpc("store_pos_inventory", p_request_id=request_id, p_product_id=1,
                        p_mode="PURCHASE", p_quantity=24, p_reason="Compra", p_unit_cost=2000,
                        p_expected_stock=10)

    def test_inventory_rejects_silent_integer_or_money_coercion_before_transport(self):
        for changes in ({"quantity": True}, {"quantity": 2.5}, {"quantity": "2"},
                        {"unit_cost": True}, {"unit_cost": -1}, {"unit_cost": 2.5},
                        {"expected_stock": True}, {"expected_stock": -1},
                        {"expected_stock": 2.5}):
            with self.subTest(changes=changes):
                parameters = dict(product_id=1, mode="PURCHASE", quantity=2,
                                  unit_cost=2000, expected_stock=10)
                parameters.update(changes)
                with self.assertRaises(ValueError):
                    self.db.pos_inventory(**parameters)
        self.db.client.rpc.assert_not_called()

    def test_void_is_scoped_has_reason_and_preserves_transport_failure(self):
        order_id = str(uuid4())
        self.db.pos_void(order_id, "  Venta duplicada  ")
        self.assert_rpc("store_pos_void", p_order_id=order_id, p_reason="Venta duplicada")
        self.db._execute.side_effect = TimeoutError("uncertain result")
        with self.assertRaises(TimeoutError):
            self.db.pos_void(order_id, "Venta duplicada")


if __name__ == "__main__":
    unittest.main()
