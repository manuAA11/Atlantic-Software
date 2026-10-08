# Verificación de Gym soft para ZTATTUZ 3.4.5

- Fuentes: Gym soft Comercial 3.4.5 y últimos archivos disponibles de ZTATTUZ, incluidos pagos y gastos de Recepción.
- 35 pruebas Python: planes, fechas, importes, lectura, reintento de acceso, errores y configuración del instalador.
- 30 comprobaciones de actualización: comparación de registros anteriores en las 21 tablas originales; actualización repetida; cuentas, saldos y API anterior conservados.
- 20 comprobaciones de permisos y aislamiento.
- 38 contratos RPC y 15 contratos de columnas de tablas.
- 27 comprobaciones de cupos y lectura; 65 de vigencia, traslado, seguimiento y permisos de tiqueteras.
- 99 comprobaciones de una jornada de gimnasio usando las clases Python reales y PostgreSQL local. El detalle de cada caso y métodos ejercitados está en `simulacion_gimnasio.json`.
- 9 etapas gráficas con datos simulados: ventanas, tamaños, lectores, fechas, consultas en segundo plano, desplegables, movimiento/maximización, pagos y columnas estables.

## Base original

Actualización `ztatuz_gymsoft_345_compatibility` aplicada al proyecto original `srmquhwpawgipncmvfjf`. La comprobación posterior devuelve versión 3.4.5. Los recuentos anteriores y posteriores coinciden: 59 clientes, 61 membresías, 5 planes, 8 gastos, 4 accesos, 0 ventas y 0 entradas.

Las RPC nuevas rechazan ejecución anónima. `gym_branding` tiene RLS: lectura por miembros del gimnasio y escritura solo por Administración. Los cambios de pagos, entradas y tiqueteras validan el rol y el gimnasio en el servidor.

La revisión de Supabase conserva avisos previos sobre RPC históricas `SECURITY DEFINER` y protección de contraseñas filtradas no activada; no se han declarado resueltos como parte de este traslado. La nueva implementación de pagos coloca la función privilegiada en el esquema privado. Referencias: [avisos sobre ejecución anónima](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [ejecución autenticada](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable), [protección de contraseñas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Límites de la comprobación

Las pruebas se ejecutaron en Linux con Tk y PostgreSQL local; las de maximización simulan el estado del sistema cuando no existe un gestor de ventanas. No se han compilado ejecutables Windows en este entorno. El generador los compila en Windows, comprueba su icono y ejecuta su diagnóstico antes de generar los instaladores.

Windows 10 Mini es una instalación modificada y necesita una comprobación en su equipo. El paquete apunta a x64, como sus instaladores anteriores. El lector físico, correo real y servicio externo de WhatsApp no se pueden certificar mediante esta simulación.
