# Validación Windows

Los informes son generados por GitHub Actions en Windows Server 2022 y se conservan con su commit y run ID. No contienen aceptación de hardware ni pilotos Meta/Wompi.

Run `37859485810`, commit `44c26bf39fe2e453f0012b66153ef0f5e1e403b3`: las tres ediciones fallaron en `windows_ui_smoke`, después de aprobar sus pruebas Python, datos y las primeras pantallas. Los 450 tests Python ejecutados en Windows aprobaron con CPython 3.14.8; ZTATTUZ x86 utilizó un proceso de 32 bits.

El selector devuelve `path.resolve()`, mientras que la prueba comparaba directamente con el texto de la carpeta temporal. Se corrigió la comparación para exigir la misma ruta resuelta, conservar la comprobación de selección y mostrar ambas rutas si difieren. Las tres pruebas gráficas corregidas aprobaron también en Linux/Tk. La repetición completa en Windows determinará si quedan fallos posteriores; los informes FAIL originales se conservan aquí.

Los probes congelados y la comprobación del gate no llegaron a ejecutarse en este run porque falló la etapa anterior. No se generaron instaladores finales.

Run `37859988512`, commit `13d6040`: las tres ediciones aprobaron la comparación de ruta corregida y avanzaron hasta `layout_consistency_ui_smoke` (etapa 35), donde falló el requisito de no desplazar horizontalmente el Dashboard en una ventana solicitada de 1280x800. Los informes se mantienen completos. El mismo fallo se reprodujo en Linux con monitor 1024x768: la ventana pedida se limita realmente a 992x672; la prueba completa aprueba con monitor 1600x1000. La siguiente ejecución prepara un escritorio Windows 1920x1080, registra su área útil y ejecuta primero la prueba que falla. La aserción se conserva y ahora informa geometría real y ancho del visor. Esto comprobará la hipótesis de resolución del entorno antes de atribuirlo al producto.

Run `37861051674`, commit `6a5d4a8`: el escritorio Windows se configuró correctamente (área útil 1920x1040). Al 100 % y 120 % la prueba avanzó; al 125 % confirmó un defecto de producto: Dashboard requiere 1000 píxeles y el visor mide 967 dentro de una ventana real de 1280x800. Se redujo de tres a dos celdas el ancho de los iconos de las cuatro tarjetas métricas, conservando texto, tamaño de fuente, filas y columnas en las tres ediciones. El recheck gráfico Linux aprobó las 120 comprobaciones existentes. La nueva ejecución Windows comprobará el ajuste; no se modificó la aserción para aceptar desplazamiento.

Run `37861401268`, commit `86e1417`: el ancho mínimo bajó a 976 píxeles; todavía excedía el visor de 967 al 125 %. Se ajustó únicamente el margen horizontal de Dashboard de 24 a 16 píxeles por lado, usando el espaciado existente del kit y conservando el margen vertical, texto, fuente y columnas. Las 120 comprobaciones del recheck Linux aprobaron; la repetición Windows determinará el resultado.
