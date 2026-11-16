# Reintento de captura incompleta · Atlantic Gym 3.8.8

Reporte: el programa responde, pero a veces parece no reaccionar al dedo o devuelve una captura incompleta. No se dispone todavía del diagnóstico del lector físico.

Se reprodujo con sensor simulado que BadScan iniciaba o reiniciaba release_at, la espera de retirada reservada a una muestra aceptada. Cuando el dedo seguía presente, el siguiente intento quedaba en espera y una imagen válida podía descartarse como repetida. Ahora una captura incompleta conserva el estado previo de retirada y permite un nuevo intento con una pausa interrumpible de 120 ms para evitar un ciclo ocupado.

La misma corrección se aplica a identificación, registro y comprobación. Una mala captura no cuenta como muestra ni crea asistencia. Una espera ya establecida por una captura aceptada se conserva, incluso si falla una lectura posterior del sensor. No cambia el adaptador nativo, el umbral de coincidencia, la validación de identidades, la sincronización de huellas, las escrituras ni el relé.

Pruebas nuevas: reintento con dedo presente, fallos consecutivos, registro sin contabilizar muestra fallida, comprobación sin guardar/asistencia, huella desconocida rechazada, protección tras captura válida y cierre durante recuperación. Antes de corregir fallaban seis de siete casos. Después pasan las siete regresiones y las 43 pruebas existentes de adaptador/servicio disponibles localmente por perfil (50 por perfil). La guarda restaura exclusivamente el bloque BadScan exacto para comprobar el SHA256 histórico del resto del trabajador; el adaptador nativo conserva su SHA256 completo. No se desactiva ninguna prueba ni gate.

Es una mejora de recuperación reproducida en software, no una certificación de calidad de captura física ni una confirmación de la causa de todos los casos reportados. No se modifican plantillas existentes ni datos productivos. Windows, publicación, descargas y alcance del piloto se registran con el commit exacto al terminar su validación. La entrega final, lector/relé físico e instalación nativa Windows32 mantienen sus aceptaciones pendientes.
