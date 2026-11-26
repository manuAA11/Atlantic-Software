# Modelo de crecimiento (no capacidad garantizada)

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
Supuestos ilustrativos: usuarios móviles activos mensuales totales U; 20 días/mes, dos sesiones/día, seis lecturas/sesión, 8.000 bytes comprimidos/lectura sin cache; optimizado cuatro lecturas/sesión de 5.000 bytes. No son tamaños medidos de producción. Son datos autenticados uncached. Base = U×20×2×6×8.000; alternativa = U×20×2×4×5.000, reducción hipotética 58,3% de este componente exclusivamente.

| U totales | Lecturas base/mes | GB base | GB alternativa |
|---:|---:|---:|---:|
| 100 | 24.000 | 0,192 | 0,080 |
| 500 | 120.000 | 0,960 | 0,400 |
| 1.000 | 240.000 | 1,920 | 0,800 |
| 5.000 | 1.200.000 | 9,600 | 4,000 |

Si U es por gimnasio, multiplicar por G. Si U total se reparte entre G gimnasios, no multiplicar otra vez. En GB decimales, sin uploads, imágenes, push, auth, escritorio, Socket, RPC internos, backups ni HTTP overhead.

Escenario adicional explícito de escritorio por gimnasio: un puesto 12h/día, 26 días/mes, lista de huellas 240 veces/hora de 80.000 bytes hipotéticos = 5,9904 GB/mes/gimnasio. Delta hipotética: misma frecuencia con respuestas vacías de 200 bytes y dos cambios/día de 1.000 bytes = 0,015028 GB/mes. Estos bytes NO se midieron; el ahorro requiere D aprobado, no lo aporta B1.

| Gimnasios | Huellas full GB hipotéticos | Delta GB hipotéticos | Mobile 100 por gym GB base | 500 por gym | 1.000 por gym | 5.000 por gym |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5,9904 | 0,015028 | 0,192 | 0,960 | 1,920 | 9,600 |
| 5 | 29,952 | 0,075140 | 0,960 | 4,800 | 9,600 | 48,000 |
| 10 | 59,904 | 0,150280 | 1,920 | 9,600 | 19,200 | 96,000 |
| 25 | 149,760 | 0,375700 | 4,800 | 24,000 | 48,000 | 240,000 |
| 50 | 299,520 | 0,751400 | 9,600 | 48,000 | 96,000 | 480,000 |

Cron actual está a nivel proyecto, no multiplicar automáticamente por G. Dos proyectos con marketing 1 min: 86.400 ticks/30d; notices 5 min: 8.640/30d ZTATTUZ; freezes 86.400 ejecuciones SQL/30d ambos, no Edge. Lotes pueden crecer con G y necesitar más ticks; modelar backlog y tiempo máximo. Si se crea un proyecto por cliente, cron sí crece por proyecto, pero Free tiene límites de proyectos: no es estrategia validada.

Free ofrece 5 GB uncached y 5 GB cached separados por organización, no 10 GB intercambiables. Debe quedar margen para escritorio, auth y servicios; 5.000 usuarios en escenario optimizado no garantizan Free. CPU, memoria, conexiones y Realtime no pueden inferirse sólo de GB o número de gimnasios. Medir p95, filas, planes, concurrencia y colas con datos sintéticos representativos antes de prometer capacidad.

## Monitorización ligera preparada, sin servicio desplegado

Usar Usage/Observability nativos, exportación diaria revisada y baseline al inicio/final del piloto. Registrar cached/uncached por servicio; conexiones/CPU/RAM nativas; API/HTTP errores; funciones conteo y p50/p95; auth/reconexiones sin tokens; estado de colas/leases y resultado cron. Medir cache/dedupe hit por sesión con contadores locales agregados, no logs de payload.

Umbrales para cada cuota real Q: 50%, 70%, 85%, 95%. Egress Free uncached 5 GB: 2,5; 3,5; 4,25; 4,75 GB (cached igual, independiente). Para API/Functions/Realtime/Storage confirmar cuota vigente y aplicar Q×umbral; no inventar cuota API que sea sólo métrica. Distinguir plan actual y unidad de facturación.

Especificación de alertas: estado por organización/recurso/período, aviso sólo al cruzar un umbral nuevo, deduplicado; reset al nuevo ciclo; marcar muestra desconocida si falta Usage. Aviso 50 revisar drivers, 70 aplicar cambios validados, 85 detener ampliación, 95 evaluar continuidad/plan sin desactivar recepción. No se configuraron alertas ni destinatarios externos; herramientas actuales no exponen creación de alertas de Usage. No añadir polling frecuente para monitorizar polling.
