# Gym soft ZTATTUZ 3.5.3 — Corrección del panel de ingreso y la compilación

## Instalar esta actualización

1. Cierra las aplicaciones y las ventanas de prueba anteriores.
2. Extrae este ZIP completo en una carpeta nueva. No mezcles sus archivos con la carpeta 3.5.2.
3. Ejecuta **CREAR_INSTALADORES.bat**. La consola debe empezar la validación con **Gym soft 3.5.3 · Validación local con lector simulado**.
4. Durante las pruebas gráficas, mantén el escritorio desbloqueado y no cierres sus ventanas. Se cierran automáticamente al terminar cada caso.
5. Cuando finalice correctamente, instala **salida/ZTATTUZ_Instalar_o_Actualizar_3.5.3.exe** y abre los accesos directos habituales.
6. Comprueba que el programa indique **3.5.3**.

El paquete incluye código completo, pruebas, generador de instaladores y los componentes del lector. Requiere Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6 para compilar en Windows. **No incluye los ejecutables de Gym soft ya compilados.**

**No se necesita el lector físico ni su controlador durante la compilación.** No vuelvas a ejecutar SQL ni a registrar los clientes por esta actualización. Los datos y las huellas de la base existente se conservan.

## Qué se corrigió

- El mensaje **INGRESO NO AUTORIZADO** y los demás resultados respetan los márgenes interiores del aviso.
- Las columnas de búsqueda y resultado mantienen su distribución al cambiar el mensaje o mostrar un nombre largo. El texto se envuelve dentro de su columna.
- El cálculo de texto del módulo compartido reserva el espacio de márgenes y bordes de las etiquetas.
- La prueba de huellas espera cada respuesta, incluida una respuesta tardía. Sus mensajes de confirmación se simulan durante todo el escenario para no dejar un diálogo esperando un clic.
- Las esperas detectan el cierre de la ventana y muestran el paso que falló. La limpieza no intenta destruir otra vez una aplicación ya cerrada.
- Cada etapa imprime progreso y tiene un límite de tiempo. Un fallo detiene la compilación; no se cambia un error por un PASS ni se omiten las pruebas.

## Cómo reconocer la prueba actualizada

Aparece **PRUEBA: access_layout_ui_smoke**, con casos al 100 %, 120 % y 125 %. En **PRUEBA: fingerprint_ui_smoke** aparecen líneas que comienzan por **HUELLA:** e indican la aplicación, escala y operación.

El error anterior en `fingerprint_ui_smoke.py`, línea 66, en `<module>`, correspondía al test antiguo. En esta entrega los escenarios se ejecutan dentro de `scenario()` y la ventana de prueba muestra el número de versión.

Si una etapa falla, envía `salida/validacion/RESUMEN_PRUEBAS.txt` y el `.log` de esa etapa. Los avisos de actualización de pip no son errores de compilación.

## Registro y comprobación biométrica

El registro sigue siendo opcional, dentro de **Nuevo cliente** y **Editar cliente**. Espera la confirmación **Huella registrada y verificada correctamente** antes de darlo por terminado. **Comprobar huella** verifica la identidad sin registrar una entrada ni consumir una tiquetera.

Para el ingreso automático, cierra los formularios, deja activada **Lectura automática de huella** y utiliza una sola aplicación con ese lector. La lectura no necesita el cursor en el buscador. Un resultado de ingreso rechazado conserva el plan y no descuenta entradas.

En el computador que tenga el lector, instala una vez **DigitalPersonaRuntime/setup.exe**, manteniendo todos los archivos de esa carpeta. Si ya está instalado y funcionando, esta actualización no requiere reinstalar el controlador.

## Alcance de la comprobación

El informe nuevo está en **VERIFICACION_3.5.3.md** y los resultados por etapa están en `salida/validacion`. Se usa Tk real en Linux, PostgreSQL local con datos ficticios y lector simulado. Las pruebas no se conectan a los gimnasios reales.

La comprobación final del instalador, el dibujo en Windows 10 Mini y el lector físico debe realizarse en el computador del gimnasio. Los resultados locales no garantizan ausencia de todos los errores ni sustituyen esa comprobación.
