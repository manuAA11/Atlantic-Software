# Auditoría del módulo original de Tienda

Base inspeccionada antes de modificar código: `57febfb`, rama `feature/internal-plans-early-resume`. Requisitos: `REQUISITOS_TIENDA_POS_20261014.txt`. La auditoría es de código y pruebas locales; no representa una lectura de la base productiva ni una prueba física.

## Productos y persistencia

`GymSoft_Comercial_3.6.0/sql/014_store.sql` crea `store_products` con ID bigint, gym, nombre, SKU, precio, stock, mínimo, activo, autores y fechas TIMESTAMPTZ. `016_products.sql` agrega imagen y modifica los RPC de lectura/guardado. ZTATTUZ contiene las funciones equivalentes en `ACTUALIZAR_ZTATTUZ_3.4.5.sql`. Existen índices únicos por gimnasio para nombre normalizado y SKU no vacío, e índice de gimnasio/activo/nombre.

El editor `ProductDialog` de `app.py` etiqueta **un único campo SKU** como «Código de barras o SKU». Se persiste y busca ese SKU; no existe una columna barcode separada ni unicidad/indexación propia de barcode. Tampoco existen descripción, categoría o costo. La imagen, mínimo, estado y fechas sí existen y deben conservarse. `admin_save_store_product` permite sustituir stock sin un libro de movimientos.

## Ventas, pagos e inventario

`register_store_sale` bloquea una fila de producto con FOR UPDATE, valida stock y registra atómicamente una venta individual y su descuento. Es una base útil que se conserva. `store_sales` contiene snapshots del producto, cantidad, precio, total, método/referencia, nombre libre de comprador, empleado e instante. No hay cabecera UUID para carrito, consecutivo por gimnasio, pago separado, efectivo recibido/cambio, cliente relacionado, idempotencia de cobro, movimientos de inventario ni anulación administrativa conservando el original.

No hay recepción de inventario con costo, ajuste motivado con antes/después, ni reportes de margen basados en costos históricos. Una nueva cabecera no debe duplicar los ingresos de las líneas antiguas.

## Administrador y Recepción

`app.py:ShopPage` contiene productos/inventario, editor con imagen, activar/desactivar, resumen de existencias y ventas recientes. El administrador no dispone de un POS con carrito. `reception_app.py:ReceptionShopPage` tiene búsqueda, catálogo de tarjetas e imágenes, estados de stock y venta individual mediante `StoreSaleDialog`. Deben mantenerse el catálogo, la adaptación de tamaño, los componentes y las imágenes.

Recepción busca por nombre o SKU mediante RPC. La lectura actual `AutomaticHidScanner` observa una entrada concreta y se evalúa por inactividad; después busca una coincidencia exacta de SKU y abre el diálogo individual. No proporciona el flujo solicitado de escaneos repetidos agregados al carrito con ENTER y sin modales por producto.

`BiometricAccessController` inserta un bindtag en controles de la ventana principal y puede interpretar ráfagas de teclado como identificación de acceso. Reconoce `_hid_scanner` para omitir controles: el POS debe delimitar su contexto y evitar que un código de producto registre asistencia o solicite apertura. No debe capturar escritura de otros formularios, diálogos ni páginas ocultas.

## Permisos y multi-gym

Los RPC usan `private.user_has_gym_role`, con permisos admin para productos/finanzas y admin/receptionist para catálogo/venta. Comercial incorpora suscripción, usuario/equipo y licencia en esa autorización; se conserva. Las tablas existentes tienen RLS, aunque el administrador conserva acceso directo a productos y ventas. Los nuevos datos y mutaciones requieren controles en servidor, no solamente botones ocultos. No hay una configuración específica de Tienda habilitada por gimnasio.

Las diferencias entre Comercial y ZTATTUZ en `app.py`, `reception_app.py` y `cloud_database.py` corresponden principalmente a licencia, rutas, plantillas y formatos de respaldo. ZTATTUZ x86/x64 comparten estas fuentes; `reception_database.py` es idéntico en las tres ediciones. Las mejoras se implementarán en componentes comunes distribuidos a las tres ediciones, preservando estas diferencias.

## Finanzas, fechas e importación

`FinancePage` ya distingue membresías, tienda y gastos, y muestra un total combinado explícito. `admin_store_finance` agrupa las líneas de tienda por método/producto e incluye datos de auditoría. Se debe conservar esta separación e impedir que una venta anulada siga sumando. Los compradores STAFF no deben excluirse de ventas ordinarias de productos.

Las migraciones de tiempo existentes proporcionan `private.gym_server_now`, `private.gym_timezone` y `private.gym_local_date`. Los nuevos movimientos/cobros deben utilizar estos contratos; no la fecha del computador ni una zona fija.

`cloud_database.py` exporta/importa la hoja Productos con el SKU combinado, precio, stock, mínimo y estado; no incluye barcode/costo/categoría/descripción. `prepare_excel_replacement` relaciona ventas con productos por SKU. Los respaldos JSON incluyen las tablas antiguas. `admin_replace_gym_from_excel` elimina/recrea datos con remapeo de IDs: necesita protección/integración explícita para no perder los nuevos libros POS. Deben conservarse importadores históricos, imágenes, datos de membresías y los archivos de respaldo.

## Código incompleto y pruebas

No se encontró un POS completo oculto ni un segundo backend de carrito que pudiera habilitarse con un botón. No aparecen TODO/FIXME de tienda que completen estas ausencias. Los `pass` encontrados son manejo de ventanas/herencia y no constituyen implementación de POS. Hay lógica de catálogo/venta repartida en las copias por edición, por lo que los nuevos contratos deben ser comunes.

Las pruebas actuales cubren venta individual, descuento/stock insuficiente, producto inactivo, aislamiento, permisos, finanzas, edición del propietario, importación y tiempos. `review_ui_smoke.py` comprueba que el catálogo conserva tarjetas y se adapta correctamente. No cubren un carrito POS, barcode separado, movimientos, cambio, reintentos de cobro ni anulación. Se agregarán pruebas de esos flujos y se ejecutarán completas las regresiones existentes en las tres ediciones, sin retirar gates.

## Implementación que sigue a esta auditoría

Extensión aditiva de productos y de las líneas `store_sales`; cabeceras UUID, pagos, movimientos y configuración; RPC transaccionales comunes con bloqueo ordenado e idempotencia; catálogo/editor existente ampliado y carrito compartido para ambos roles; importación/exportación compatible; pruebas SQL/Python/Tk y checklist físico. La actualización no requiere reescribir membresías, marketing, pagos Wompi, huellas ni puerta.

La prueba física del lector y el despliegue productivo se registrarán únicamente cuando se ejecuten. El usuario informó que la puerta ya funciona; esto no sustituye las demás comprobaciones de hardware o instalación.
