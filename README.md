# Atlantic Software · Multi-Gym

Código recuperado de Gym Soft Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64. Checkpoint de desarrollo; no es un instalador final.

## Carpetas

- `GymSoft_Comercial_3.6.0`: Administración, Recepción y panel privado del propietario.
- `GymSoft_ZTATTUZ_3.6.1_x86` y `GymSoft_ZTATTUZ_3.6.1_x64`: Administración y Recepción ZTATTUZ por arquitectura.
- `common`, `backend`, `supabase`, `onboarding`, `deployment`: motores compartidos, servicios y migraciones.
- `evidence`: evidencia histórica del ZIP y resultados de esta instancia, identificados por separado.
- `docs/REQUISITOS_CIERRE_MULTIGYM.txt`: requisitos de cierre del usuario.

## Estado

Se preserva congelación, tiqueteras, reloj del gimnasio, Marketing, WhatsApp/chatbot y Wompi. Ver `docs/Informe_Actualizacion_20261008.md` para el estado histórico; los resultados de esta instancia están en `evidence/current-instance-20261008`. Los iconos y runtimes Windows originales fueron excluidos del ZIP. Las pruebas de empaquetado fallan por `icono.ico` ausente; no se han generado instaladores. Los pilotos externos y hardware siguen pendientes de verificación.

## Desarrollo local

Python 3.13 con Tk 8.6 y Node.js LTS. Instalar los requisitos de cada edición y ejecutar `npm ci` dentro de ella. `python run_validation.py --data-only` ejecuta datos; `python run_validation.py --ui-only` ejecuta interfaz. En Linux las pruebas gráficas requieren un display y cada suite paralela debe usar uno distinto. No reinstalar dependencias durante las pruebas.

Backend compartido: desde la raíz ejecutar `node --test backend/tests/*.test.mjs`. Las pruebas locales usan datos ficticios, PGlite y adaptadores de hardware. No acreditan Windows, hardware o Meta/Wompi reales.

Los cambios deben conservar la lógica del servidor como fuente de verdad y cumplir los requisitos de cierre. No ejecutar el esquema inicial sobre una base existente. Consultar las guías de despliegue antes de aplicar migraciones.
