# Validación de Gym soft Comercial 3.2.0

Fecha: 8 de septiembre de 2026.

## Comprobaciones realizadas

| Área | Resultado |
| --- | --- |
| Python: formularios, presentación, resiliencia, empaquetado, huella y planes | 46 pruebas aprobadas |
| Ventanas Tk: acceso, avisos, archivos, pagos, gastos y editor | Prueba gráfica aprobada |
| Diseño: Administración, Recepción y Propietario; navegación, formularios y pestañas | 138 comprobaciones aprobadas con ventanas de 800 × 550, 960 × 640 y tamaños mayores, y escalas tipográficas de 100 % y 125 % |
| Lector con eventos Tk reales | Aprobados: lectura con/sin Enter, código escrito/pegado, foco fuera del buscador, repetición, pausa, formularios y consulta pendiente invalidada |
| PostgreSQL local: seguridad y reglas del negocio | 54 comprobaciones aprobadas |
| Contratos de comunicación con el servidor | 60 llamadas RPC y 14 contratos de tablas aprobados |
| Operaciones del propietario y pagos | 35 comprobaciones aprobadas |
| Editor del propietario | 159 comprobaciones aprobadas |
| Huella opcional y tiqueteras en PostgreSQL local | 27 comprobaciones aprobadas, con cupos de 15 y 20 entradas, consumo, agotamiento, renovación, mensualidades y aislamiento por gimnasio |
| Comparación con 3.1.1 | No se eliminaron métodos de las aplicaciones ni del editor. Los archivos SQL permanecen iguales. |

Las pruebas de base de datos utilizan PostgreSQL local mediante PGlite con datos ficticios. No modifican gimnasios, pagos ni registros reales.

La comprobación gráfica se ejecutó en Tk sobre Linux con una pantalla virtual y fuentes escalables de reemplazo para las fuentes Windows. Comprueba la distribución y el comportamiento de las ventanas con distintos tamaños de texto; no sustituye la verificación del ejecutable en Windows.

## Verificación al compilar en Windows

`CREAR_INSTALADORES.bat` ejecuta las pruebas de Python y los tres recorridos gráficos antes de compilar. Después comprueba que los tres ejecutables incorporen el icono GS antes de crear los instaladores.

Queda pendiente probar los ejecutables instalados en Windows, sus accesos directos y un lector físico compatible, usando la configuración real del equipo al 100 % y al 125 %. El ZIP contiene código fuente y scripts de compilación, no ejecutables compilados en este entorno.

La captura automática reconoce códigos que llegan como teclado. No integra por sí sola lectores que requieren el SDK específico de su fabricante. El filtrado de lecturas repetidas actúa durante cinco segundos dentro de cada instancia de Gym soft.
