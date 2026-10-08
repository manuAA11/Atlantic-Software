# Validación Windows

Los informes son generados por GitHub Actions en Windows Server 2022 y se conservan con su commit y run ID. No contienen aceptación de hardware ni pilotos Meta/Wompi.

Run `37859485810`, commit `44c26bf39fe2e453f0012b66153ef0f5e1e403b3`: las tres ediciones fallaron en `windows_ui_smoke`, después de aprobar sus pruebas Python, datos y las primeras pantallas. Los 450 tests Python ejecutados en Windows aprobaron con CPython 3.14.8; ZTATTUZ x86 utilizó un proceso de 32 bits.

El selector devuelve `path.resolve()`, mientras que la prueba comparaba directamente con el texto de la carpeta temporal. Se corrigió la comparación para exigir la misma ruta resuelta, conservar la comprobación de selección y mostrar ambas rutas si difieren. Las tres pruebas gráficas corregidas aprobaron también en Linux/Tk. La repetición completa en Windows determinará si quedan fallos posteriores; los informes FAIL originales se conservan aquí.

Los probes congelados y la comprobación del gate no llegaron a ejecutarse en este run porque falló la etapa anterior. No se generaron instaladores finales.
