# Validación de la corrección 3.3.1

Se reprodujo el mensaje exacto «No cargaron usuarios e invitaciones» de la versión anterior retrasando el comienzo de la consulta inicial. La prueba anterior verificaba la lista tras 400 ms y solo esperaba si ya había una consulta en curso; el intervalo anterior al inicio podía confundirse con una lista vacía definitiva.

La carga ahora comienza antes de mostrar el editor. La prueba espera un estado de carga completa y sigue comprobando los dos registros, sus correos, sus estados y la llamada al gimnasio correcto. La prueba retiene intencionadamente la respuesta simulada mientras comprueba que la ventana está visible y ocupada. No se elimina ni se omite la verificación que fallaba.

Resultados locales:

- 52 pruebas Python correctas.
- Prueba gráfica completa de acceso, formularios, archivos, pagos, gastos y editor del propietario correcta, incluyendo respuesta retrasada.
- Reproducción del fallo anterior confirmada antes de modificar el código.

La corrección usa la misma base y las mismas funciones SQL que 3.3.0. No se conectó a Supabase ni se modificaron datos comerciales en esta corrección. Los resultados de operaciones de 3.3.0 se conservan en VALIDACION_3.3.0.md.

Validado en Linux con Tk y Xvfb. La compilación y el funcionamiento de los ejecutables en Windows requieren comprobarse en el equipo de destino; esta entrega no contiene ejecutables ya compilados. CREAR_INSTALADORES.bat conserva las pruebas de ventanas, diseño, lectura y tiqueteras y la verificación del icono antes de generar los instaladores.
