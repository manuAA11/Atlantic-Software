# Revisión de compilación 1 — 26 de septiembre de 2026

Validación completa nueva: **PASS**, 23 etapas y 113 pruebas de Python. Incluye 124 controles gráficos de huella con respuestas tardías y la regresión de esperas. Lector simulado y Tk real en Linux; falta comprobar la compilación en Windows. Consulta `VERIFICACION_COMPILACION_3.5.2_R1.json` y `LEEME_PARCHE_COMPILACION_3.5.2.md`.

A continuación se conserva el informe original de la entrega 3.5.2.

# Verificación de Comercial 3.5.2

Resultado local: PASS. Lector simulado, interfaz Tk real y PostgreSQL local con datos ficticios.

- Pruebas de Python de la revisión final: **106**.
- Formulario biométrico: **80** comprobaciones al 100 % y 125 %.
- Gestor, primer ingreso desde cualquier sección, ingreso permitido/denegado, huella desconocida y avisos: **124** comprobaciones gráficas.
- Servicio biométrico + almacenamiento + RPC reales + PostgreSQL local: **28** comprobaciones completas en Administración y Recepción.
- Etapas generales de datos: **11**, todas PASS.
- Etapas generales de interfaz: **11**, todas PASS.
- Simulación de una jornada de gimnasio: **107** comprobaciones.

Se comprobó que una captura incompleta no guarda una huella, que el aviso de éxito requiere comparación y lectura de confirmación en la base, que una respuesta perdida no repite la escritura y que la comprobación del formulario no consume entradas. El ingreso normal sí consulta el plan y descuenta la tiquetera cuando corresponde. Se cubrieron rechazo de planes vencidos, clientes inactivos, falta de plan, cupo agotado, huella eliminada y lecturas repetidas.

La revisión de la captura incluye consulta de estado con tamaño variable según el SDK, calibración, captura de hasta cuatro segundos fuera del hilo de interfaz, espera acotada entre muestras y códigos de diagnóstico. El fallo observado en el equipo físico no pudo reproducirse con ese dispositivo aquí. Las correcciones cubren los defectos encontrados en el código; no equivalen a una certificación del lector real.

Se consultaron las bases de Comercial y ZTATTUZ: ambas tenían **0 huellas** en la última comprobación del 26 de septiembre de 2026. No se extrajeron plantillas, no se escribieron huellas de prueba y no se modificó SQL en producción.

Los resultados completos y huellas SHA-256 del código están en `salida/validacion/ENTREGA_3.5.2.json` y `codigo_biometrico_3.5.2.json`. Los registros originales de las pruebas se conservan. Las comprobaciones finales amplían las pruebas de Python y de entrada por huella incluidas en las ejecuciones generales.

**Pendiente:** generar los ejecutables en Windows y comprobar el dispositivo físico con el controlador instalado, incluida la instalación concreta de Windows 10 Mini. La compilación utiliza un lector simulado y no exige conectar hardware. Las pruebas no garantizan ausencia absoluta de errores ni rendimiento idéntico en todos los equipos.
