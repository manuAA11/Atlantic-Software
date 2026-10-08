# Validación de Gym soft Comercial 3.4.4

Revisión realizada el 14 de septiembre de 2026 sobre la entrega 3.4.3. Se probaron el código corregido y sus operaciones con datos ficticios. No se escribieron datos en gimnasios reales ni se cambiaron funciones o permisos de Supabase.

## Resultados

**Resultado final: PASS en las 17 etapas de la ejecución completa.**

La batería combina nueve etapas de datos y ocho de interfaz. Los archivos de `salida/validacion` contienen el resultado, la duración y la salida de cada etapa. El paquete de resultados incluye estos registros y la salida completa de la ejecución.

| Área | Comprobación |
| --- | --- |
| Lógica Python | 64 pruebas, incluidas nuevas regresiones de importes, fecha, concurrencia y licencia durante un guardado. |
| Seguridad y reglas | 54 comprobaciones con PostgreSQL local. |
| Contratos del cliente y del servidor | Extracción de contratos y validación de 61 llamadas RPC y 15 contratos de tablas. |
| Operaciones del propietario | 35 comprobaciones de formularios, renovaciones y operaciones. |
| Editor del propietario | 159 comprobaciones de permisos, conflictos, tablas editables, restauración transaccional, relaciones, inventario y eliminación aislada. |
| Huella opcional y cupos | 27 comprobaciones de registro, consumo, renovación e independencia entre gimnasios. |
| Tiqueteras y seguimiento | 70 comprobaciones de meses calendario, saldos, roles, seguimiento e idempotencia. |
| Jornada de un gimnasio | 107 comprobaciones usando las clases de datos de Python y el SQL comercial. |
| Inicio y ventanas | Acceso, Sí/No, formularios, mensajes oscuros, archivos, pagos, gastos y editor del propietario. |
| Espacio disponible | 510 comprobaciones de tamaños, navegación y formularios al 100 % y 125 %, además de pruebas del detector de controles tapados. |
| Lector automático | Lectura con y sin Enter, búsqueda manual, repetición, foco fuera del buscador, formularios, pausa y respuestas pendientes. |
| Fechas y planes en interfaz | 34 comprobaciones al 100 % y 125 %. |
| Carga y actualización | 14 páginas, respuestas obsoletas descartadas, ráfagas agrupadas, modales, selección, barras condicionales y reutilización de contenido. |
| Desplegables nativos | 40 comprobaciones del problema `popdown`, pagos, avisos y recuperación. |
| Distribuciones de ventana | 396 comprobaciones de modo normal, maximizado y movimiento sin redistribuir al 100 %, 120 % y 125 %. |
| Nuevas regresiones gráficas | 71 comprobaciones de cambio de distribución sin retirar controles, scroll sin recalcular tamaños, pagos con respuesta lenta o fallida, doble envío, invitaciones y catálogo con productos. |

Los números describen comprobaciones ejecutadas; no representan un porcentaje de cobertura de todas las combinaciones posibles.

## Qué se simuló en la jornada

1. Crear y consultar clientes con cumpleaños y huella opcional.
2. Crear planes mensuales y tiqueteras; registrar pagos y vigencias.
3. Registrar entradas, consumir cupos y comprobar denegaciones de acceso.
4. Corregir y anular pagos, conservando su historial.
5. Vender desde Recepción y comprobar inventario y totales.
6. Registrar gastos y conciliar la jornada.
7. Gestionar personal, turnos, rutinas, clases y reservas.
8. Consultar Dashboard, estadísticas y seguimiento de clientes por sesión.
9. Comprobar contactos y autorizaciones de marketing.
10. Exportar Excel, crear respaldos y restaurar en otro gimnasio de prueba.
11. Comprobar roles, licencia y aislamiento entre gimnasios.

Se ejecuta PostgreSQL local mediante PGlite. El transporte de pruebas conecta las clases Python con ese motor. Se prueban reglas y resultados del SQL; esto no equivale a probar la conexión real de Internet, Auth o Realtime de un gimnasio.

## Evidencia de rendimiento

En la ejecución final, despachar una consulta al trabajador tomó **0,07 ms**; aplicar a una tabla de **1.000 filas** una respuesta idéntica tomó **3,01 ms**, con **cero borrados y cero inserciones**. Son mediciones puntuales en este entorno, no una promesa de tiempos idénticos en Windows ni una medida del tiempo total de respuesta del servidor.

Las regresiones nuevas comprueban también que:

- Cambiar de modo no espera los antiguos temporizadores de distribución ni coloca una capa sobre la aplicación.
- Los controles que ya usan `grid` no reciben `Unmap` por cambiar de columnas.
- Desplazar contenido estable no ejecuta otra distribución.
- Un guardado lento permite que siga avanzando el bucle de eventos de Tk.
- Un error conserva los campos del formulario y no se convierte en un mensaje de éxito.
- Otro envío durante la espera no repite la escritura.
- Las tarjetas de productos se reutilizan si no cambian y el botón de venta permanece dentro de cada tarjeta al 100 %, 120 % y 125 %.

El enfoque de separar trabajo de datos y dibujo sigue el modelo de eventos de Tk: sus manejadores deben devolver el control pronto para que la interfaz continúe respondiendo. Referencia: [documentación oficial de Python sobre Tkinter y sus hilos](https://docs.python.org/3/library/tkinter.html#threading-model).

## Entorno y límites

La validación local utilizó **Linux, Python 3.12.14 y Tk 9.0**, con un escritorio virtual. Los cambios de estado normal/maximizado se emulan donde el entorno no dispone de un gestor de ventanas. Las pruebas inspeccionan controles reales de Tk, su geometría, visibilidad y eventos; no miden la animación del compositor de Windows ni certifican que un vídeo de desplazamiento no muestre ningún artefacto.

La entrega de Windows requiere Python 3.13 de 64 bits y se compila con PyInstaller e Inno Setup. **Este ZIP no contiene ejecutables compilados o probados en Windows.** Su constructor vuelve a ejecutar la batería completa y comprueba el icono GS de los ejecutables antes de generar instaladores.

Queda por verificar en el computador de uso: instalación y actualización del EXE, iconos, desplazamiento y maximización nativos, cambio entre monitores, lector físico, envío y confirmación de correo, conexión entre equipos y servicio de WhatsApp si se ofrece. Las pruebas automatizadas reducen riesgos; no garantizan que sea imposible encontrar otro error.

## Reproducir y diagnosticar

Ejecuta `SIMULAR_GIMNASIO.bat` o compila con `CREAR_INSTALADORES.bat`. Deja el escritorio desbloqueado y las ventanas visibles durante las pruebas gráficas. Una superposición ajena puede impedir comprobar qué control recibe el ratón.

Si falla una etapa, la compilación se detiene. Conserva `salida/validacion/resultado_pruebas.json`, `RESUMEN_PRUEBAS.txt` y el registro de la etapa indicada. No omitas pruebas para obtener un instalador.

Created by Manuel Cuéllar  
© 2026 Manuel Cuéllar. All rights reserved.
