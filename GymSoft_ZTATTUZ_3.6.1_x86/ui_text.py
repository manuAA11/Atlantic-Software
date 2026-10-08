"""Presentación en español; los valores internos del servidor se conservan."""
from gym_time import parse_instant

STATES={
 'payment_status':{'posted':'Vigente','void':'Anulado'},
 'result':{'PERMITIDA':'Autorizada','DENEGADA':'No autorizada'},
 'role':{'admin':'Administración','receptionist':'Recepción','system':'Sistema'},
 'status':{'PROGRAMADA':'Programada','CANCELADA':'Cancelada','COMPLETADA':'Completada',
           'RESERVADA':'Reservada','PENDING':'Pendiente','PROCESSING':'En proceso',
           'SENT':'Enviado','FAILED':'No enviado','SKIPPED':'Omitido',
           'active':'Activo','trialing':'En prueba','expired':'Vencido',
           'suspended':'Suspendido','cancelled':'Cancelado'},
}
OWNER_ACTIONS={
 'gym_created':'Gimnasio creado','gym_profile_edited':'Datos del gimnasio actualizados',
 'subscription_renewed':'Mensualidad registrada','status_changed':'Estado de suscripción actualizado',
 'contract_changed':'Contrato actualizado','grace_granted':'Período de gracia concedido',
 'device_registered':'Equipo registrado','device_changed':'Acceso del equipo actualizado',
 'user_changed':'Acceso del usuario actualizado','invite_created':'Invitación creada',
 'invite_redeemed':'Invitación utilizada','email_assigned':'Correo y rol asignados',
 'invitation_revoked':'Invitación revocada','backup_exported':'Respaldo descargado',
 'record_edited':'Registro corregido','record_deleted':'Registro eliminado','database_imported':'Respaldo importado',
}
DETAIL_LABELS={'reason':'Motivo','email':'Correo electrónico','user_id':'ID de usuario','device_id':'ID de equipo',
 'id':'ID','role':'Rol','before_role':'Rol anterior','months':'Meses','amount':'Valor','reference':'Referencia',
 'currency':'Moneda','status':'Estado','name':'Nombre','plan':'Plan','table':'Tabla','rows':'Registros',
 'price':'Precio','devices':'Límite de equipos','users':'Límite de usuarios','days':'Días','trial_days':'Días de prueba',
 'blocked':'Bloqueado','enabled':'Habilitado','before':'Antes','after':'Después','source_gym_id':'Gimnasio de origen',
 'before_counts':'Registros anteriores','import_counts':'Registros importados','period_until':'Vigencia hasta',
 'period_from':'Vigencia desde','recorded_by':'Registrado por','created_at':'Fecha de registro',
 'gym_id':'ID del gimnasio','idempotency_key':'Identificador de operación','timezone':'Zona horaria',
 'contact_email':'Correo de contacto','monthly_price':'Mensualidad','max_devices':'Límite de equipos',
 'max_users':'Límite de usuarios','period_end':'Vencimiento','grace_until':'Gracia hasta',
 'active':'Activo','first_name':'Nombres','last_name':'Apellidos','full_name':'Nombre completo',
 'document':'Documento','phone':'Teléfono','birth_date':'Fecha de nacimiento',
 'payment_method':'Método de pago','payment_reference':'Referencia de pago','payment_status':'Estado del pago',
 'start_date':'Inicio','end_date':'Fin','notes':'Notas','updated_at':'Última modificación',
 'payment_revision':'Revisión del pago','amount_paid':'Valor pagado','stock_quantity':'Existencias',
 'quantity':'Cantidad','total_amount':'Total','sale_price':'Precio de venta','unit_price':'Precio unitario'}

def state_text(field,value):
    return STATES.get(field,{}).get(str(value),value)

def state_value(field,text):
    return next((raw for raw,label in STATES.get(field,{}).items() if label==text),text)

def readable(value,field=''):
    if value is None:return 'Sin dato'
    if isinstance(value,bool):return 'Sí' if value else 'No'
    if isinstance(value,dict):
        return '; '.join(f'{DETAIL_LABELS.get(k,k.replace("_"," ").capitalize())}: {readable(v,k)}' for k,v in value.items())
    if isinstance(value,list):return ', '.join(readable(v) for v in value) or 'Sin registros'
    return str(state_text(field,value))

def service_status(settings,now=None):
    """Un registro antiguo no acredita que el servicio siga conectado."""
    if settings.get('last_error'):return 'Requiere revisión','danger'
    if not settings.get('phone_number_id'):return 'Sin configurar','warning'
    last=settings.get('last_worker_at')
    if not last:return 'Pendiente de activar','warning'
    try:
        stamp=parse_instant(last)
        current=parse_instant(now if now is not None else settings.get('server_now'))
        elapsed=(current-stamp).total_seconds()
    except ValueError:return 'Estado no disponible','warning'
    if not 0<=elapsed<=900:return 'Sin actividad reciente','warning'
    if not settings.get('whatsapp_enabled'):return 'Envíos pausados','warning'
    return 'En servicio','success'

MARKETING_ACTIVITY_LABELS={'MARKETING_META_CONNECTED': 'WhatsApp conectado', 'MARKETING_META_DISCONNECTED': 'WhatsApp desconectado', 'MARKETING_WOMPI_CONNECTED': 'Wompi conectado', 'MARKETING_WOMPI_DISCONNECTED': 'Wompi desconectado', 'MARKETING_PAYMENT_PROCESSED': 'Pago online confirmado', 'MARKETING_PAYMENT_REQUIRES_REVIEW': 'Pago online requiere revisión', 'MARKETING_MEMBERSHIP_RENEWED': 'Membresía renovada online', 'MARKETING_CHATBOT_VERIFIED': 'Cliente verificado por chatbot', 'MARKETING_CHATBOT_VERIFICATION_FAILED': 'Verificación de chatbot fallida', 'MARKETING_HUMAN_HANDOFF': 'Chatbot derivado a atención humana', 'MARKETING_HUMAN_MESSAGE': 'Chatbot pausado por respuesta humana', 'MARKETING_CONSENT_GRANTED': 'Autorización de WhatsApp concedida', 'MARKETING_CONSENT_REVOKED': 'Autorización de WhatsApp retirada', 'MARKETING_AUTOMATION_CREATED': 'Automatización creada', 'MARKETING_AUTOMATION_UPDATED': 'Automatización editada', 'MARKETING_AUTOMATION_ENABLE': 'Automatización activada', 'MARKETING_AUTOMATION_PAUSE': 'Automatización pausada', 'MARKETING_AUTOMATION_DUPLICATE': 'Automatización duplicada', 'MARKETING_AUTOMATION_DELETE': 'Automatización eliminada', 'MARKETING_TEMPLATE_SAVED': 'Plantilla de WhatsApp guardada', 'MARKETING_FEATURES_UPDATED': 'Configuración de Marketing actualizada', 'MARKETING_SETUP_ACTIVATED': 'Marketing activado', 'MARKETING_SANDBOX_CLIENT_CREATED': 'Cliente de pruebas creado', 'MARKETING_TEST_MESSAGE_QUEUED': 'Mensaje de prueba programado', 'MARKETING_CHATBOT_LINK_APPROVED': 'Cliente vinculado al chatbot', 'MARKETING_CHATBOT_LINK_REJECTED': 'Vinculación al chatbot rechazada', 'MARKETING_CONVERSATION_BOT': 'Chatbot reactivado', 'MARKETING_CONVERSATION_HUMAN': 'Chatbot derivado a atención humana', 'MARKETING_MESSAGE_HUMAN': 'Respuesta humana por WhatsApp', 'MARKETING_MESSAGE_RECEIVED': 'Mensaje recibido por WhatsApp', 'MARKETING_MESSAGE_QUEUED': 'Mensaje WhatsApp programado', 'MARKETING_MESSAGE_SENT': 'Mensaje WhatsApp enviado', 'MARKETING_MESSAGE_DELIVERED': 'Mensaje WhatsApp entregado', 'MARKETING_MESSAGE_READ': 'Mensaje WhatsApp leído', 'MARKETING_MESSAGE_FAILED': 'Envío WhatsApp fallido', 'MARKETING_MESSAGE_UNCERTAIN': 'Envío WhatsApp sin confirmación', 'MARKETING_MESSAGE_SKIPPED': 'WhatsApp omitido', 'MARKETING_MESSAGE_NO_CONSENT': 'WhatsApp omitido por falta de autorización'}
