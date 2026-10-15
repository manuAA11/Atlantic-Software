"""Real Tk POS regression with simulated HID and mocked server, no hardware claim."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
from responsive_ui_smoke import assert_buttons_fit, pump, shell
from store_pos_ui import CheckoutDialog, InventoryDialog
from ui_assertions import destroy_root


PRODUCTS = [dict(id=1, name="Agua", sku="AGUA", barcode="7701234567890", category="Bebidas", unit_cost=1000,
                 sale_price=3000, stock_quantity=5, low_stock_threshold=2, active=True),
            dict(id=2, name="Barra", sku="BAR", barcode="ABC-123", category="Alimentos", unit_cost=None,
                 sale_price=5000, stock_quantity=1, low_stock_threshold=1, active=True)]


def scan(entry, code):
    entry.focus_force()
    entry.update()
    for character in code:
        entry.event_generate("<KeyPress>", keysym=character)
    entry.event_generate("<KeyPress>", keysym="Return")
    entry.update()


def main():
    checks = 0
    for module, cls in ((admin, admin.GymSoftApp), (reception, reception.ReceptionApp)):
        with patch.object(reception.branding, "show_reception_logo", lambda *_: None):
            root = shell(cls, 1.25)
        failures = []
        root.report_callback_exception = lambda kind, error, tb: failures.append(error)
        try:
            page_type = module.ShopPage if module is admin else module.ReceptionShopPage
            with patch.object(page_type, "refresh", lambda self: None):
                root.show_page("shop")
            page, db = root.pages["shop"], root.db
            panel = page.pos
            panel.set_products(PRODUCTS)
            pump(root)
            entry = panel.search_entry if module is admin else page.search_entry
            db.pos_products.reset_mock()
            root.biometric_access.lookup = Mock()
            scan(entry, PRODUCTS[0]["barcode"])
            scan(entry, PRODUCTS[0]["barcode"])
            assert panel.cart.rows[1]["quantity"] == 2
            assert entry.get() == "" and not db.pos_products.called
            assert not root.biometric_access.lookup.called, "Un producto llegó al lector de acceso."
            checks += 4
            # The automatic buffer also works when focus is on the cart.
            scan(panel.cart_tree, PRODUCTS[1]["barcode"])
            assert panel.cart.rows[2]["quantity"] == 1
            scan(panel.cart_tree, PRODUCTS[1]["barcode"])
            assert panel.cart.rows[2]["quantity"] == 1 and "Stock disponible" in panel.status.get()
            checks += 2
            panel.notebook.select(panel.history_tab)
            pump(root)
            scan(panel.history_tree, PRODUCTS[0]["barcode"])
            assert panel.cart.rows[1]["quantity"] == 2, "Se escaneó desde una pestaña oculta."
            panel.notebook.select(panel.sale_tab)
            checks += 1
            # Checkout excludes unrelated/modal input and preserves uncertain writes.
            dialog = CheckoutDialog(panel)
            pump(root)
            dialog.customer_input.focus_force()
            dialog.customer_input.event_generate("<KeyPress>", keysym="7")
            dialog.customer_input.event_generate("<KeyPress>", keysym="Return")
            pump(root)
            assert panel.cart.rows[1]["quantity"] == 2
            dialog.received.set("100")
            with patch("store_pos_ui.messagebox.showwarning") as warning:
                dialog.save()
            assert warning.called and not db.pos_checkout.called
            dialog.received.set("20000")
            order = dict(id="00000000-0000-4000-8000-000000000111", number="V-000001", total_amount=11000,
                         sold_at="2026-10-15T14:00:00Z", status="COMPLETED", items=[], payment=dict(method="EFECTIVO", received=20000, change_amount=9000))
            calls = []
            def checkout(**payload):
                calls.append(payload)
                if len(calls) == 1:
                    raise TimeoutError("Resultado no confirmado")
                return order
            db.pos_checkout.side_effect = checkout
            with patch("store_pos_ui.messagebox.showerror"), patch.object(panel, "refresh"), patch.object(panel, "show_receipt"), patch.object(page, "refresh_sales", create=True):
                dialog.save()
                assert dialog.winfo_exists() and panel.pending is not None
                before = panel.cart.items()
                panel.add_product(PRODUCTS[0])
                assert panel.cart.items() == before
                dialog.reference.set("No debe cambiar el cobro")
                dialog.save()
            assert calls[0] == calls[1], "El reintento cambió identidad o contenido del cobro."
            assert not panel.cart.rows and panel.pending is None
            checks += 6
            # A definitive server rollback releases the attempt, keeping the cart.
            panel.add_product(PRODUCTS[0])
            rejected = RuntimeError("El precio cambió")
            rejected.code = "GS001"
            db.pos_checkout.side_effect = rejected
            dialog = CheckoutDialog(panel)
            pump(root)
            with patch("store_pos_ui.messagebox.showwarning"):
                dialog.save()
            assert panel.pending is None and panel.cart.rows[1]["quantity"] == 1
            assert str(dialog.reference_input.cget("state")) == "normal"
            dialog.destroy()
            checks += 2
            # A broad/incorrect history response cannot release a different charge.
            panel.begin_checkout(dict(items=panel.cart.items(), payment=dict(method="EFECTIVO", received=3000, reference=""), client_id=None, customer_name="", notes=""))
            pending_id = panel.pending.request_id
            db.pos_history.return_value = [dict(order, request_id="00000000-0000-4000-8000-000000000999")]
            with patch("store_pos_ui.messagebox.showinfo"):
                panel.resolve_pending()
            assert panel.pending.request_id == pending_id
            db.pos_history.return_value = [dict(order, request_id=pending_id)]
            with patch.object(panel, "refresh"), patch.object(panel, "show_receipt"), patch.object(page, "refresh_sales", create=True):
                panel.resolve_pending()
            assert panel.pending is None and not panel.cart.rows
            checks += 2
            assert_buttons_fit(page)
            if module is admin:
                product = admin.ProductDialog(page, PRODUCTS[0])
                pump(root)
                assert product.barcode.get() == PRODUCTS[0]["barcode"] and product.sku.get() == "AGUA"
                product.barcode.set("NEW-123")
                product.save()
                assert product.result["barcode"] == "NEW-123" and "stock_quantity" not in product.result
                checks += 2
                db.pos_movements.return_value = []
                inventory = InventoryDialog(panel, PRODUCTS[0])
                pump(root)
                inventory.mode.set("ADJUST")
                inventory.quantity.set("3")
                with patch("store_pos_ui.messagebox.showwarning") as warning:
                    inventory.save()
                assert warning.called and not db.pos_inventory.called
                inventory.reason.set("Conteo físico")
                db.pos_inventory.return_value = dict(stock_after=3)
                # Dedicated inventory scanning must select the scanned product.
                inventory.code.set(PRODUCTS[1]["barcode"])
                inventory.scan_product()
                inventory.save()
                payload = db.pos_inventory.call_args.kwargs
                assert payload["quantity"] == 3 and payload["expected_stock"] == 1 and payload["mode"] == "ADJUST" and payload["product_id"] == 2
                checks += 3
                # A lost inventory response remains the same attempt after close/reopen.
                db.pos_inventory.reset_mock()
                db.pos_inventory.side_effect = TimeoutError("Resultado no confirmado")
                inventory = InventoryDialog(panel, PRODUCTS[0])
                pump(root)
                with patch("store_pos_ui.messagebox.showerror"):
                    inventory.save()
                original = db.pos_inventory.call_args.kwargs
                inventory.destroy()
                inventory = InventoryDialog(panel, PRODUCTS[0])
                pump(root)
                db.pos_inventory.side_effect = None
                db.pos_inventory.return_value = dict(stock_after=6)
                inventory.save()
                assert db.pos_inventory.call_args.kwargs == original
                assert panel.inventory_pending is None
                checks += 2
            assert not failures, failures
        finally:
            destroy_root(root)
    print(f"POS_UI_SMOKE_OK {checks} checks; mocked server, simulated HID, no physical hardware")


if __name__ == "__main__":
    main()
