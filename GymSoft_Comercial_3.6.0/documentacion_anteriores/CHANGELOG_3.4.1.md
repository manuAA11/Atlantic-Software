# Gym soft Comercial 3.4.1

- Corrección del cierre `KeyError: popdown` al abrir desplegables durante pagos y del fallo secundario al mostrar el aviso de error.
- Consulta segura del foco y del control modal de Tcl/ttk; los formularios mantienen la pausa del lector y de los refrescos.
- Corrección de campos incompatibles con el esquema comercial al crear rutinas, ejercicios y clases.
- Dos distribuciones estables de tarjetas por escala: ventana normal y maximizada. El movimiento no vuelve a distribuir cuadros; los textos se ajustan tras estabilizar el ancho y las barras aparecen ante desbordamiento.
- Las vistas ocultas y los controles destruidos dejan de programar ajustes pendientes de distribución.
- Simulación de jornada con las clases Python reales y PostgreSQL local, incluyendo roles, licencia, clientes, planes, pagos, entradas, tienda, gastos, personal, rutinas, clases, estadísticas, marketing y restauración.
- Ampliación de los contratos de tablas para comprobar también campos literales enviados en escrituras.
- Pruebas de desplegables reales y de los dos modos al 100 %, 120 % y 125 %, incluidas comprobaciones de texto visible.
- Informes por etapa y validación integrada como requisito previo a generar instaladores.
- Preparación de Python sin dependencia obligatoria del comando `py`.

No incluye cambios de SQL ni modificaciones en gimnasios reales. La compilación y verificación nativa de los instaladores se realizan en Windows.
