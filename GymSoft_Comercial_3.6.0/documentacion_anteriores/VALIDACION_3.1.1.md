# Gym soft Comercial 3.1.1 · Registro de validación

Fecha: 7 de septiembre de 2026. Entorno de pruebas: Linux, Python 3.12 y PostgreSQL local mediante PGlite. El generador de instaladores exige Python 3.13 de 64 bits en Windows.

## Resultados ejecutados

| Verificación | Resultado | Alcance |
| --- | --- | --- |
| Pruebas Python | 38 aprobadas | Formularios, importes, archivos, recuperación del panel, configuración de instaladores, traducción de estados y avisos de operaciones inciertas. |
| Seguridad y operación | 54 aprobadas | Aislamiento entre gimnasios, RLS, roles, invitaciones, equipos, vencimiento, gracia, suspensión, pagos, entradas, gastos, respaldo y auditoría. |
| Contratos de llamadas | 60 RPC y 14 tablas aprobados | Correspondencia entre llamadas Python y firmas/columnas del SQL. |
| Propietario y pagos | 35 aprobadas | Parámetros reales de formularios, renovación idempotente, contrato, estados y accesos. |
| Editor del propietario | 159 aprobadas | Edición de las tablas permitidas, conflictos, inventario, usuarios e invitaciones, validación de importación, reconstrucción de relaciones, reversión y eliminación aislada. |
| Comparación con el servidor | 124 funciones coincidentes | Firmas, cuerpos de código, modo SECURITY DEFINER/INVOKER y configuración; sólo se normalizaron los saltos de línea CRLF/LF. |

Las operaciones de prueba que escriben o eliminan datos se ejecutaron en la base local. En el proyecto comercial se consultaron metadatos y avisos de seguridad; no se realizaron cobros, importaciones ni eliminaciones reales.

## Comprobaciones que requieren Windows o servicios externos

- No se compiló ni ejecutó un EXE Windows en este entorno. No se presenta el ZIP de código como un instalador compilado.
- `CREAR_INSTALADORES.bat` ejecuta las pruebas Python y `tests/windows_ui_smoke.py` antes de compilar. Esta prueba comprueba la visibilidad del acceso, las respuestas Sí/No, formularios, diálogos oscuros, archivos, pagos, gastos y editor. Si falla, se detiene la compilación.
- Tras compilar, el generador verifica que cada EXE contenga los tamaños del icono GS. La apariencia del acceso directo instalado y el comportamiento de la caché de Windows necesitan una comprobación en el escritorio real.
- Falta la prueba de una instalación nueva y una actualización con dos equipos y cuentas de un gimnasio de prueba. Las pruebas locales no sustituyen esta comprobación de extremo a extremo.
- No hay funciones de envío desplegadas en el proyecto comercial para WhatsApp. Los envíos automáticos quedan pendientes de activación del servicio y de su configuración externa. No se enviaron mensajes a contactos reales.
- No se probó un lector físico o integración biométrica en este entorno.

## Revisión de Supabase

El proyecto `bawrakwhzkxmhmgkczqu` informa `gymsoft-commercial`, base 3.0.0 y editor 3.1.0. No es necesaria una nueva instalación SQL para pasar la aplicación a 3.1.1.

La revisión automática devolvió estos avisos, que no deben confundirse con pruebas funcionales fallidas:

- **7 avisos informativos de RLS sin políticas en tablas privadas.** La denegación directa es intencional; las operaciones pasan por funciones con comprobación de propietario o licencia. No se añadieron políticas abiertas para silenciar el aviso. [Referencia de Supabase](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
- **47 avisos sobre funciones SECURITY DEFINER ejecutables por usuarios autenticados.** Son puntos de entrada sujetos a comprobaciones de identidad, rol y acceso. Las suites verifican los recorridos cubiertos; no constituyen una auditoría exhaustiva independiente. [Referencia de Supabase](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).
- **Protección frente a contraseñas filtradas desactivada en Auth.** Está pendiente revisar su activación desde la configuración de autenticación del proyecto. [Configuración de Supabase](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

No se detectaron avisos de RLS deshabilitada en esta consulta. Los avisos anteriores se registran de forma explícita; no se afirma que el proyecto tenga cero avisos.

## Repetir las pruebas

Desde la carpeta del código, con las dependencias instaladas:

```text
python -m unittest discover -s tests -p "test_*.py"
python tests/extract_contracts.py
npm ci
npm test
```

En Windows: `VERIFICAR_INTERFAZ.bat`, o `CREAR_INSTALADORES.bat` para verificar y compilar.
