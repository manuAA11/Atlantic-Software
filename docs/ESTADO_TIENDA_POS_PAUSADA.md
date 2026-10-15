# Tienda / POS: borrador pausado

El usuario pidió el 15 de octubre priorizar la incidencia del relé y Bluetooth.
Se conserva el trabajo de Tienda sin generar instaladores, desplegar SQL remoto
ni declararlo terminado. La rama de checkpoint `wip/tienda-pos-20261015` sirve
para recuperar este estado; no es una versión publicada del programa.

Requisitos originales: `REQUISITOS_TIENDA_POS_20261014.txt`. Auditoría realizada
antes de implementar: `AUDITORIA_TIENDA_POS_20261014.md`.

Hay extensión de backend POS, productos/barcode, inventario, carrito y cobro,
historial, estadísticas, importación y respaldo en componentes comunes y copias
por edición. Las pruebas dirigidas ejecutadas durante el desarrollo no equivalen
a la validación completa final. Al retomar se debe revisar la sincronización de
`common/store_pos_ui.py` con sus copias y completar las últimas comprobaciones
de foco del escáner, catálogo limitado y gimnasio con Tienda deshabilitada.

Pendientes: integración/regresiones completas de las tres ediciones, revisión
final de migración y respaldo, despliegue autenticado de servidor, Windows
x86/x64 y lector HID físico conforme a `PRUEBA_TIENDA_POS.md`. Conservar también
los requisitos de aceptación externos y `release_readiness.json`.

La corrección del cierre del relé se guardó aparte en `816fcb9`; no necesita la
migración POS ni las funciones nuevas de Tienda. El checkout de trabajo conserva
ambos avances para continuar después de resolver la incidencia física.
