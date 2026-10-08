# Validación 3.3.0 — 8 de septiembre de 2026

Entorno local: Linux, Python, Tk con Xvfb y PostgreSQL PGlite. No se crearon datos de prueba en los gimnasios comerciales reales.

| Verificación | Resultado |
|---|---|
| Pruebas Python | 52 correctas |
| Seguridad PostgreSQL | 54 comprobaciones |
| Contratos | 64 RPC y 14 tablas |
| Operaciones de propietario y pagos | 35 comprobaciones |
| Editor, importación y borrado aislado | 159 comprobaciones |
| Huella opcional y consumo de entradas | 27 comprobaciones |
| Meses, saldos, seguimiento y permisos | 70 comprobaciones |
| Diseño, navegación y formularios | 138 comprobaciones al 100 % y 125 % |
| Escritura de fechas, tiqueteras y seguimiento | 34 comprobaciones gráficas al 100 % y 125 % |

Se probaron meses y años bisiestos, ausencia de ingresos y visitas ficticias en traslados, reintentos sin duplicación, rechazo de superposiciones, conservación de cupos vendidos, rangos exclusivos, períodos inclusivos y permisos por rol y gimnasio.

Supabase devolvió `success: true` al aplicar la migración comercial. La consulta posterior de comprobación fue bloqueada por el límite de uso de la revisión automática. No se intentó eludir el bloqueo; se adjunta la consulta de solo lectura para revisión manual.

El asesor de seguridad posterior mantuvo los avisos previos: siete tablas privadas sin políticas directas, 47 funciones heredadas con ejecución privilegiada y protección de contraseñas filtradas no activada. No se añadieron avisos. Referencias: [políticas](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [funciones](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable) y [contraseñas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

No se compiló ni ejecutó el instalador en Windows desde este entorno. Las pruebas de Tk no sustituyen la comprobación real de Windows, accesos directos, DPI y lector físico. La compilación en Windows ejecuta pruebas gráficas y verifica el recurso del icono antes de generar los instaladores.
