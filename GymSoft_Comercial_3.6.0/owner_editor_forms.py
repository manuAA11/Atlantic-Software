"""Validación y archivos del editor del propietario, independientes de Tk."""
from __future__ import annotations
from datetime import date, datetime
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from owner_forms import required, email
from ui_text import state_value

TABLES = {
    'Clientes': 'clients', 'Planes': 'plans', 'Pagos y membresías': 'memberships',
    'Entradas': 'checkins', 'Personal': 'trainers', 'Jornadas': 'staff_shifts',
    'Rutinas': 'routines', 'Ejercicios': 'exercises', 'Clases': 'classes',
    'Reservas': 'reservations', 'Productos e inventario': 'store_products',
    'Ventas de tienda': 'store_sales', 'Gastos': 'accounting_expenses',
    'Mensajes (consulta)': 'marketing_messages', 'Auditoría (consulta)': 'audit_logs',
}
LABELS = dict(zip(
    'id document first_name last_name full_name phone email birth_date emergency_contact medical_notes active name duration_days price entry_limit start_date end_date amount payment_method payment_reference notes payment_status checkin_at method result specialty hourly_rate hire_date check_in_at check_out_at hourly_rate_snapshot goal day_name sets reps weight position starts_at capacity status sku sale_price stock_quantity low_stock_threshold quantity unit_price customer_name sold_at expense_date category description vendor receipt_reference client_id plan_id product_id trainer_id class_id routine_id membership_id total_amount amount_paid created_at'.split(),
    ['ID','Documento','Nombres','Apellidos','Nombre completo','Teléfono','Correo','Nacimiento (AAAA-MM-DD)',
     'Contacto de emergencia','Notas médicas','Activo','Nombre','Duración (días)','Precio','Límite de entradas',
     'Inicio (AAAA-MM-DD)','Fin (AAAA-MM-DD)','Valor','Método de pago','Referencia de pago','Notas','Estado del pago',
     'Entrada (fecha y hora UTC)','Método','Resultado','Especialidad','Tarifa por hora','Contratación (AAAA-MM-DD)',
     'Inicio de jornada (UTC)','Fin de jornada (UTC)','Tarifa de jornada','Objetivo','Día','Series','Repeticiones','Peso','Orden',
     'Inicio de clase (UTC)','Cupo','Estado','SKU','Precio de venta','Existencias','Alerta de inventario','Cantidad',
     'Precio unitario','Cliente','Venta (fecha y hora UTC)','Fecha del gasto','Categoría','Descripción','Proveedor',
     'Comprobante','ID cliente','ID plan','ID producto','ID personal','ID clase','ID rutina','ID membresía','Total',
     'Valor pagado','Creación (UTC)']))
LABELS.update(duration_months='Vigencia en meses calendario (solo tiqueteras)', initial_entries_used='Entradas utilizadas antes del traslado', carryover_key='Identificador del traslado')
ENUMS = {'payment_status': ['posted','void'], 'result': ['PERMITIDA','DENEGADA']}

def profile_params(gym, raw):
    tz=required(raw.get('timezone'), 'Zona horaria', 1, 100)
    try: ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError('Zona horaria inválida. Ejemplo: America/Bogota.') from error
    return {'p_gym_id': gym['id'], 'p_name': required(raw.get('name'),'Nombre',1,120),
            'p_email': email(raw.get('email')), 'p_timezone':tz,
            'p_plan':required(raw.get('plan'),'Plan comercial',1,80),
            'p_reason':required(raw.get('reason'),'Motivo',3,500)}

def email_params(gym, raw):
    roles={'Administración':'admin','Recepción':'receptionist'}
    if raw.get('role') not in roles: raise ValueError('Selecciona Administración o Recepción.')
    return {'p_gym_id':gym['id'],'p_email':email(raw.get('email')),
            'p_role':roles[raw['role']],'p_reason':required(raw.get('reason'),'Motivo',3,500)}

def confirmation(gym, raw):
    if raw.get('name') != gym['name']: raise ValueError('Escribe exactamente el nombre del gimnasio mostrado.')
    return {'p_name':raw['name'],'p_reason':required(raw.get('reason'),'Motivo',3,500)}

def record_patch(columns, original, raw):
    patch={}
    for col in columns:
        if not col['editable']: continue
        name=col['name']; text=raw.get(name,'').strip(); kind=col['type']; label=LABELS.get(name,name)
        if not text and col['nullable']:
            value=None
        elif kind=='boolean':
            if text not in ('Sí','No'): raise ValueError(f'{label}: selecciona Sí o No.')
            value=text=='Sí'
        elif kind in ('bigint','integer','smallint'):
            try:
                if not text or text.lstrip('-').isdigit() is False: raise ValueError()
                value=int(text)
            except ValueError as error: raise ValueError(f'{label}: escribe un entero sin separadores de miles.') from error
        elif kind=='date' and text:
            try: value=date.fromisoformat(text).isoformat()
            except ValueError as error: raise ValueError(f'{label}: usa AAAA-MM-DD.') from error
        elif kind.startswith('timestamp') and text:
            try:
                dt=datetime.fromisoformat(text.replace('Z','+00:00'))
                if dt.tzinfo is None: raise ValueError()
                value=dt.isoformat()
            except ValueError as error: raise ValueError(f'{label}: incluye la zona; ejemplo 2026-09-07T09:00:00+00:00.') from error
        else: value=state_value(name,text)
        if len(text)>5000: raise ValueError(f'{label}: máximo 5.000 caracteres en el editor.')
        if value!=original.get(name): patch[name]=value
    if not patch: raise ValueError('No hay cambios para guardar.')
    return patch

def read_backup(path):
    p=Path(path)
    if p.stat().st_size>20*1024*1024: raise ValueError('El respaldo supera el límite de 20 MB de esta importación.')
    data=json.loads(p.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or data.get('format') not in ('GymSoft-CLOUD-1','GymSoft-CLOUD-2') or not isinstance(data.get('tables'),dict):
        raise ValueError('Selecciona un respaldo JSON de Gym soft. No se ejecutan archivos SQL.')
    return data

def write_backup(path, data):
    """Sustitución atómica; un fallo no destruye un respaldo anterior."""
    destination=Path(path); temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,
                                         prefix='.gymsoft-backup-',suffix='.tmp',delete=False) as file:
            temporary=Path(file.name)
            json.dump(data,file,ensure_ascii=False,indent=2,allow_nan=False)
            file.flush();os.fsync(file.fileno())
        os.replace(temporary,destination)
    finally:
        if temporary and temporary.exists(): temporary.unlink()
