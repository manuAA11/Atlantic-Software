# Atlantic Tech Software: políticas de este repositorio

Estos requisitos vienen del usuario y se aplican a todo cambio de Multi-Gym.

- Continúa desde el código recuperado; no reimplementes ni retires funciones existentes.
- Revisa las funciones comunes en Comercial y ZTATTUZ x86/x64. Conserva las funciones exclusivas de cada producto y su compatibilidad con instalaciones actuales.
- Usa siempre el Atlantic UI Kit extraído del diseño aprobado de Gym Soft: `common/atlantic_ui.py`, `desktop_ui.py`, `responsive_ui.py`, `ui_visuals.py`, formularios y navegación existentes. Conserva el modo oscuro de Gym. Reutiliza los componentes en lugar de introducir diseños distintos por pantalla.
- Tipografía nativa: macOS `.AppleSystemUIFont`/system y Windows Segoe UI/system. No distribuir archivos de SF Pro ni otras fuentes propietarias.
- Identidad aprobada: Atlantic Gym Administrador usa el icono G azul; Recepción usa el G cian. Usa `assets/atlantic` y las copias de recursos incluidas por edición. No sustituirlos por placeholders ni inventar otra marca. La referencia fue adjuntada por el usuario el 8 de octubre de 2026.
- Firma discreta: `© Atlantic Tech Software — All rights reserved. By Manuel Cuellar`. Aplica nombres, firma y recursos a ventanas, acceso, configuración, ejecutables, información del producto y futuros instaladores, sin cambiar IDs de instalación ni directorios históricos.
- El servidor es la fuente de verdad para membresías, congelación, acceso, vencimientos, consumo diario y reloj. No recalcular esos estados en UI.
- Preservar siete días de congelación por defecto, máximo una por membresía salvo excepción administrativa motivada, extensión de vencimiento, bloqueo de entrada/relé, conservación de cupos y una entrada consumida por día local.
- Preservar DATE para calendario, TIMESTAMPTZ para instantes y zona IANA del gimnasio. No inventar eventos 00:00 al importar fechas ni desplazar masivamente horas históricas.
- WhatsApp, chatbot, automatizaciones y Wompi deben usar el backend compartido, credenciales privadas del servidor y Vault. Nunca guardar secretos en el escritorio, repositorio, evidencias ni paquetes.
- Pruebas locales, PGlite y hardware simulado no acreditan pilotos externos, dos sesiones PostgreSQL, Windows o lector/relé físicos. Identifica claramente cada alcance.
- No marcar la actualización como terminada ni producir instaladores finales hasta cumplir `release_readiness.json` con evidencia válida de la versión. No desactivar pruebas, gates o comprobación de iconos para forzar un PASS.
- Cada tarea cloud ya es aislada. Usa el checkout existente; no crear worktrees salvo petición explícita.
- Mantén los requisitos detallados en `docs/REQUISITOS_CIERRE_MULTIGYM.txt` y las diferencias/pedientes en `docs/ESTADO_CIERRE.md`.
