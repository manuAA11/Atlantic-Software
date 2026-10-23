# Apariencia de Atlantic Gym

Atlantic Gym permite elegir dos temas desde **Configuración → Apariencia**:

- **Oscuro**: diseño existente y opción predeterminada para instalaciones que todavía no han elegido un tema.
- **Minimal**: fondo azul uniforme, iconos circulares, paneles y botones redondeados, pestañas sin relieve hundido y textos que comparten el fondo de su panel. Conserva las funciones y la navegación actuales.

Seleccionar un tema y pulsar **Aplicar tema** lo cambia sin cerrar la aplicación, reconstruir páginas ni reiniciar formularios. Administración y Recepción ofrecen el mismo selector; también está disponible en la pestaña Apariencia de Sistema y avisos.

La elección se conserva en el perfil local del usuario de Windows, en `AtlanticGym/appearance.json`, fuera de los archivos de conexión y de las carpetas históricas del gimnasio. Al volver a abrir Administración o Recepción se carga esa preferencia. No se cambia el tema de otros equipos ni de otras ventanas que estén ejecutándose en otro proceso. Las versiones x86 y x64 comparten el mismo kit y la misma preferencia.

La escritura es atómica. Si no se puede guardar, se informa del problema y se conserva el tema activo. Si el archivo falta, está dañado o contiene un tema desconocido, se usa Oscuro.

Minimal conserva los controles nativos de Tk: teclado, foco, estados deshabilitados, variables, comandos y listas desplegables. Los gráficos decorativos no participan en el cálculo del diseño adaptable. Los iconos del ejecutable y la identidad Atlantic aprobada se conservan. La ventana de acceso de Minimal tiene una presentación amplia y oculta su bloque lateral cuando la ventana es pequeña.

## Validación

- `python -m unittest tools.test_theme_settings`: persistencia, datos inválidos y fallos durante la sustitución atómica.
- `python tools/theme_ui_smoke.py`: Tk real, Administración y Recepción al 100/125 %, alternancia repetida, conservación de formulario/selección, teclado, botones deshabilitados, acceso y restauración de Oscuro. `ATLANTIC_TEST_EDITION` selecciona la variante a importar.
- La validación de Windows ejecuta estas pruebas para Comercial x64 y ZTATTUZ x86/x64.
- Las pruebas gráficas usan datos simulados y no acreditan lector, relé o un piloto físico.

Este cambio no migra datos, publica actualizaciones remotas ni sustituye instalaciones de clientes. Los paquetes anteriores a este cambio no incluyen los temas nuevos.
