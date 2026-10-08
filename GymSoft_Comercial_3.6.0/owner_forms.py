"""Validación local alineada con los RPC; el servidor sigue autorizando todo."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROLES = {'Administración': 'admin', 'Recepción': 'receptionist',
         'admin': 'admin', 'receptionist': 'receptionist'}


def required(value, label, minimum=1, maximum=4000):
    text = str(value or '').strip()
    if not minimum <= len(text) <= maximum:
        raise ValueError(f'{label}: escribe entre {minimum} y {maximum} caracteres.')
    return text


def integer(value, label, low, high):
    text = str(value).strip()
    if not re.fullmatch(r'[0-9]+', text) or not low <= int(text) <= high:
        raise ValueError(f'{label}: escribe un número entero entre {low} y {high}.')
    return int(text)


def amount(value):
    text = str(value).strip()
    # Admite importe sin miles y los formatos de miles habituales, sin adivinar.
    if re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{1,2})?', text):
        text = text.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?', text):
        text = text.replace(',', '')
    elif re.fullmatch(r'[0-9]+,[0-9]{1,2}', text):
        text = text.replace(',', '.')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', text):
        raise ValueError('Valor: usa por ejemplo 200000, 200.000 o 200000,50; no incluyas $ ni la moneda.')
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError('Valor no válido.') from None
    if not number.is_finite() or not 0 <= number <= Decimal('9999999999.99'):
        raise ValueError('Valor fuera del rango permitido.')
    return format(number.quantize(Decimal('0.01')), 'f')


def currency(value):
    code = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z]{3}', code):
        raise ValueError('Moneda: usa tres letras, por ejemplo COP o USD.')
    return code


def email(value):
    value = str(value).strip().lower()
    if not re.fullmatch(r'[^ @\s]+@[^ @\s]+\.[^ @\s]+', value):
        raise ValueError('Escribe un correo completo, por ejemplo nombre@correo.com.')
    return value


def renewal_params(gym, form):
    reference = required(form['reference'], 'Referencia del pago', 3, 160)
    return {'p_gym_id': gym['id'], 'p_months': integer(form['months'], 'Meses', 1, 120),
            'p_amount': amount(form['amount']), 'p_currency': currency(gym['currency']),
            'p_reference': reference,
            'p_idempotency_key': str(uuid.uuid5(uuid.NAMESPACE_URL, gym['id'] + '|' + reference))}


def contract_params(gym, form):
    devices = integer(form['devices'], 'Equipos', 1, 100)
    users = integer(form['users'], 'Usuarios', 1, 1000)
    if devices < int(gym.get('active_devices') or 0) or users < int(gym.get('active_users') or 0):
        raise ValueError('Desactiva primero los equipos o usuarios que superan el nuevo límite.')
    return {'p_gym_id': gym['id'], 'p_price': amount(form['price']), 'p_currency': currency(form['currency']),
            'p_max_devices': devices, 'p_max_users': users, 'p_notes': str(form['notes']).strip()[:4000]}


def new_gym_params(form):
    zone = required(form['timezone'], 'Zona horaria')
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('Zona horaria no válida. Ejemplo: America/Bogota.') from None
    return {'p_name': required(form['name'], 'Nombre', 2, 120), 'p_email': email(form['email']),
            'p_monthly_price': amount(form['price']), 'p_currency': currency(form['currency']),
            'p_max_devices': integer(form['devices'], 'Equipos', 1, 100),
            'p_trial_days': integer(form['days'], 'Días de prueba', 1, 90), 'p_timezone': zone}


def invite_params(gym, form):
    if form['role'] not in ROLES:
        raise ValueError('Selecciona Administración o Recepción.')
    return {'p_gym_id': gym['id'], 'p_email': email(form['email']), 'p_role': ROLES[form['role']]}


def grace_params(gym, form):
    return {'p_gym_id': gym['id'], 'p_days': integer(form['days'], 'Días de gracia', 1, 30),
            'p_reason': required(form['reason'], 'Motivo', 3)}
