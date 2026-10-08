# Corrección de compilación 3.5.2 — revisión 1

## Aplicar el parche a una carpeta existente

1. Cierra la ventana de compilación anterior y sus ventanas de prueba.
2. Abre el ZIP del parche correspondiente a tu edición.
3. Copia **todo su contenido** dentro de `GymSoft_ZTATTUZ_3.5.2` o `GymSoft_Comercial_3.5.2`, según corresponda. Debe quedar junto a `CREAR_INSTALADORES.bat`. Acepta reemplazar los archivos y combinar la carpeta `tests`.
4. Ejecuta `CREAR_INSTALADORES.bat` otra vez.

No basta con copiar solamente `fingerprint_ui_smoke.py`: también necesita los archivos nuevos de apoyo. No es necesario borrar `.venv`, reinstalar Python ni ejecutar SQL. Si descargaste el paquete completo actualizado, ya incluye este parche: extrae esa carpeta y ejecuta su generador normalmente.

## Qué cambia

- La prueba de huella espera cada respuesta y procesa los eventos por turnos. Ya no intenta vaciar toda la cola gráfica mediante `update()` después de cada lectura.
- Los mensajes están simulados durante todo el escenario de prueba, incluso cuando la respuesta tarda. No se necesita pulsar botones para que avance.
- Se comprueba también el caso de una respuesta tardía de guardado e ingreso.
- La prueba del lector tipo teclado espera el cambio de foco confirmado y simula el ritmo del dispositivo sin depender de las pausas del sistema. Los eventos de teclado y las comprobaciones siguen siendo reales en Tk.
- El cierre de la ventana se detecta como una interrupción de la prueba. La limpieza admite una ventana ya destruida y conserva el primer error, en lugar de añadir otro error de `destroy`.
- La consola indica el rol, escala y paso de huella en curso. Las demás etapas muestran un aviso de progreso cada 15 segundos mientras trabajan.
- La etapa de huella tiene un máximo de 120 segundos; las otras etapas, 300 segundos cada una. Si una etapa se bloquea, se detiene con diagnóstico y la compilación falla de forma visible. No se omite ninguna prueba ni se acepta un fallo como aprobado.

## Durante la compilación

Mantén las ventanas de prueba visibles y el escritorio desbloqueado. No tienes que interactuar con ellas. Las pruebas usan un lector simulado, datos ficticios y PostgreSQL local: **no requieren conectar el lector físico**.

La línea «INGRESO NO AUTORIZADO» es un caso que debe comprobarse: simula una tiquetera sin saldo. Después debe continuar con «huella desconocida» y «respuesta de ingreso no confirmada».

Si una etapa falla, el detalle queda en `salida/validacion/<nombre_de_la_etapa>.log`, y el resultado general en `salida/validacion/RESUMEN_PRUEBAS.txt`. Para el problema comunicado, el registro es `salida/validacion/fingerprint_ui_smoke.log`.

Este parche modifica únicamente la validación y su generador de informes. Se conserva la versión 3.5.2 del programa, el controlador y las funciones de registro y entrada por huella. No modifica bases de datos reales.

## Alcance de la verificación

Las pruebas se ejecutan aquí en Linux con Tk real, lector simulado y PostgreSQL local. La regresión cubre una cola gráfica continuamente ocupada, tiempos máximos, una ventana cerrada, avisos tardíos, ingresos permitidos/denegados y las demás funciones incluidas en la validación completa. El error específico de tu instalación de Windows no se reprodujo aquí; se corrigieron las esperas sin límite efectivo y la limpieza que reveló el registro. La generación de los EXE y el funcionamiento del lector físico deben comprobarse en Windows.

Resultado local de esta edición: **ZTATTUZ: PASS**, **22 etapas** completas, **84 pruebas de Python**.
