# Cambios desde el checkpoint original

Versiones de desarrollo conservadas: Comercial 3.6.0 y ZTATTUZ 3.6.1. No se anuncia una nueva versión final.

- Recuperado el último arreglo de rutas Edge: soporta el prefijo interno `/marketing`, mantiene autenticación del scheduler y rechaza prefijos parecidos. Suite backend pasa de 54 a 56 pruebas.
- Recuperada la resolución explícita de `extensions.gen_random_bytes` para el scheduler con search_path vacío. Migración correctiva aditiva; la migración histórica aplicada no se reescribe.
- Recuperados índices de claves foráneas para Marketing/congelación y el script de pruebas aisladas de concurrencia PostgreSQL.
- Centralizados colores y tipografía del Atlantic UI Kit sin cambiar el modo oscuro aprobado ni las reglas del servidor.
- Aplicados nombres Atlantic Gym, firma del autor y diferenciación azul Administrador/cian Recepción a ventanas, configuración, metadatos PE y futuros instaladores. Se conservan IDs, nombres técnicos y carpetas históricas de actualización.
- Corregido desbordamiento al 125 % por nombre largo en la barra lateral y referencia de icono cian faltante en el instalador Comercial.
- Añadidas comprobaciones de branding con Tk real y prueba HTTP/backend/SQL del flujo chatbot → membresía congelada → enlace → evento de pago firmado → renovación idempotente. Transportes externos/Vault de esta prueba son simulados.
- Restauradas instrucciones reproducibles de cloud, auditoría, respaldos y procedimientos externos/Windows. Los controles de aceptación final se conservan.
- Corregida reaplicación del actualizador de Marketing: reemplazo idempotente de políticas de Recepción y triggers de pertenencia, consentimiento, eventos y vinculación. El generador conserva snapshots históricos de migraciones.
- Ampliada compatibilidad a CPython 3.13/3.14 estándar; selección de arquitectura explícita, rutas Python Install Manager, reutilización comprobada y respaldo de entornos incompatibles sin borrar datos/configuración. Comercial utiliza el mismo preparador para configuración y panel privado.
- Añadidos accesos de fuentes `INICIAR_ADMINISTRADOR.bat`/`INICIAR_RECEPCION.bat`. Se comprueba aceptación antes de instalar dependencias de build y se explica cómo continuar las pruebas; el gate sigue activo en batch y Python.
- Corregido el módulo dinámico `PIL._tkinter_finder` faltante al empaquetar imágenes Tk con PyInstaller/Pillow. Verificado con un programa de prueba congelado en Linux/Python 3.14; no constituye un instalador Windows ni aceptación física.
