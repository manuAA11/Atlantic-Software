"""Column contracts shared by complete Excel/JSON store backups.

The extra sheets are optional only for pre-POS workbooks. A server-side
transaction rejects incomplete files before replacing an existing POS ledger.
"""

POS_BACKUP_SHEETS = {
    "store_orders": "Ventas POS",
    "store_payments": "Pagos tienda",
    "store_inventory_movements": "Movimientos tienda",
    "gym_store_settings": "Configuración tienda",
}


class StorePosBackupUnavailable(RuntimeError):
    """The legacy server has not installed the atomic POS backup API yet."""

PRODUCT_COLUMNS = {
    "Nombre": "name", "Código": "sku", "SKU": "sku",
    "Código interno": "sku", "Código de barras": "barcode",
    "Descripción": "description", "Categoría": "category",
    "Costo": "unit_cost", "Costo unitario": "unit_cost",
    "Precio": "sale_price", "Stock": "stock_quantity",
    "Stock mínimo": "low_stock_threshold",
}

POS_COLUMNS = {
    "store_orders": {
        "ID": "id", "Número venta": "sale_number", "Referencia de solicitud": "request_id",
        "Solicitud original": "request_payload", "ID cliente": "client_id",
        "Cliente": "customer_name", "Notas": "notes", "Estado": "status",
        "Total": "total_amount", "Registrado por": "sold_by", "Fecha y hora": "sold_at",
        "Anulado por": "voided_by", "Fecha anulación": "voided_at", "Motivo anulación": "void_reason",
    },
    "store_payments": {
        "ID": "id", "ID venta": "order_id", "Método de pago": "method", "Valor": "amount",
        "Recibido": "received", "Cambio": "change_amount", "Referencia": "reference",
        "Estado": "status", "Registrado por": "recorded_by", "Creado": "created_at",
    },
    "store_inventory_movements": {
        "ID": "id", "ID producto": "product_id", "Cantidad": "quantity",
        "Stock anterior": "stock_before", "Stock posterior": "stock_after", "Tipo": "movement_type",
        "Referencia": "reference", "Motivo": "reason", "ID venta": "order_id",
        "Referencia de solicitud": "request_id", "Registrado por": "created_by", "Creado": "created_at",
    },
    "gym_store_settings": {
        "Tienda habilitada": "enabled", "Último número de venta": "last_sale_number",
        "Actualizado por": "updated_by", "Actualizado": "updated_at",
        "Historial de solicitudes de inventario": "inventory_request_archive",
    },
}

SALE_COLUMNS = {
    "ID venta": "order_id", "Costo unitario": "unit_cost", "Estado": "status",
    "Código de barras": "product_barcode",
}


def validate_pos_import(tables):
    """Validate local product/barcode input without inventing legacy cost data."""
    barcodes = set()
    for product in tables.get("store_products", []):
        barcode = str(product.get("barcode") or "").strip()
        if barcode:
            if len(barcode) > 128 or not barcode.isprintable():
                raise ValueError("Productos: el código de barras debe tener hasta 128 caracteres imprimibles.")
            if barcode in barcodes:
                raise ValueError("Productos: código de barras repetido en el mismo gimnasio: " + barcode)
            barcodes.add(barcode)
            product["barcode"] = barcode
        else:
            product.pop("barcode", None)
        for key in ("unit_cost", "sale_price", "stock_quantity", "low_stock_threshold"):
            value = product.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("Productos: costo, precio y existencias deben ser enteros no negativos.")
    supplied = set(POS_BACKUP_SHEETS).intersection(tables)
    if supplied and supplied != set(POS_BACKUP_SHEETS):
        raise ValueError("Faltan hojas del historial POS. Exporta nuevamente el archivo completo antes de importar.")


def is_missing_pos_table(error):
    """Older servers retain the existing backup feature before POS migration."""
    return str(getattr(error, "code", "") or "").upper() in {"42P01", "PGRST205"}
