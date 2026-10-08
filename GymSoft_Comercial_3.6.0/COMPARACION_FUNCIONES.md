# Comparación con la base y actualizaciones disponibles

Se comparó esta edición con `ZTATTUZ_archivos_actuales.zip`, el parche de pagos `ZTATTUZ_Pagos_2_0_1_ADAPTADO_v2.zip` y el de gastos `ZTATTUZ_gastos_recepcion_2_0_4.zip`. También se revisaron los parches de finanzas/auditoría y de ventanas oscuras disponibles. Los originales no se modificaron.

| Área | Conservado / disponible en Gym soft Comercial |
| --- | --- |
| Clientes | Crear, editar, eliminar; datos personales, foto y búsqueda |
| Pagos | Registrar/renovar, historial por cliente, corregir valor/método/referencia, anular y ver auditoría |
| Finanzas | Ingresos, gastos, utilidad, distribuciones, auditoría y acceso al gestor de pagos |
| Gastos | Administración crea/edita/elimina; Recepción crea y el servidor identifica al responsable |
| Acceso | Entradas, historial, lectores HID/flujo biométrico y validación de vigencia/tiquetera |
| Tienda | Productos, imágenes, inventario, ventas y estadísticas de tienda |
| Personal | Entrenadores, turnos, asistencia y contabilidad del personal |
| Rutinas y clases | Rutinas, ejercicios, clases y reservas |
| Marketing | Configuración, contactos, autorizaciones y registros de actividad |
| Datos | Importación/exportación Excel, respaldos y sincronización en vivo |
| Comercial | Separación por gym_id, invitaciones, roles, suscripción, autorización de equipos y panel privado |

Comparación estructural de funciones/métodos de la base disponible (no es una prueba de toda interacción):

| Archivo | Base disponible | Comercial | Ausentes |
| --- | ---: | ---: | ---: |
| app.py | 178 | 181 | 0 |
| reception_app.py | 80 | 81 | 0 |
| cloud_database.py | 72 | 72 | 0 |

Se normalizó el cambio de nombre `GymControlApp` a `GymSoftApp`. Se mantienen las adaptaciones comerciales de seguridad; no se copiaron claves, logos ni la conexión del gimnasio original. Los parches de pagos y gastos se comprobaron mediante pruebas de llamadas PostgreSQL, corrección/anulación, totales y auditoría.

Alcance: esta comparación cubre los archivos y parches anteriores disponibles para esta entrega. No demuestra igualdad con modificaciones adicionales que solo existan en otro computador. La biometría física, el instalador y la apariencia en Windows requieren prueba en el equipo de destino.
