# Gym soft Comercial 3.3.2

Corrección de compilación — 9 de septiembre de 2026:

- Las pruebas gráficas activan la configuración DPI antes de crear Tk, igual que las aplicaciones.
- Las ventanas de prueba se ajustan al área útil del monitor y el punto de consulta se limita a su zona visible y al contenedor geométrico.
- Se distinguen los controles tapados de las consultas sin resultado. El diagnóstico incluye ventana, escala, área útil y sección probada.
- Se comprueban una ventana en el borde del monitor, pestañas y tablas tapadas intencionalmente, y una consulta que devuelve `None`. Los fallos reales siguen deteniendo la compilación.
- Se entrega un parche para reutilizar la carpeta 3.3.2 y sus dependencias. No cambia la versión del programa ni necesita SQL.

Cambios de la aplicación incluidos desde la entrega inicial:

- Corrige los contenedores que tapaban pestañas y tablas después de adaptar el diseño. Afectaba, entre otras pantallas, a Configuración y Estadísticas.
- Mantiene visibles esos controles al cambiar de sección y volver, reducir la ventana o ampliarla. Conserva el desplazamiento y el selector de pestañas para espacios pequeños.
- Sustituye la casilla de huella por un estado explícito («activada» o «pausada») y un botón «Pausar lectura» o «Activar lectura». El estado se comparte entre las pantallas de cada aplicación.
- Amplía las pruebas gráficas: comprueban que el contenido recibe el ratón y no queda tapado, además del tamaño. Incluyen clics reales sobre el control de lectura y una lectura simulada después de reactivarlo.
- Conserva la corrección de carga de usuarios e invitaciones de 3.3.1 y las tiqueteras, fechas y seguimiento de 3.3.0. No requiere SQL adicional.
