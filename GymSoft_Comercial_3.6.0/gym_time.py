"""Absolute server timestamps displayed in the gym's IANA timezone.

Naive legacy display strings stay unchanged; guessing their zone would shift history twice.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_ZONE = 'America/Bogota'

def timezone_for(owner):
    for item in (owner, getattr(owner, 'cloud', None), getattr(owner, 'db', None)):
        cloud = getattr(item, 'cloud', item)
        zone = getattr(cloud, 'timezone', None)
        if isinstance(zone, str) and zone:
            return zone
    return DEFAULT_ZONE

def local_datetime(value, zone=DEFAULT_ZONE):
    if isinstance(value, date) and not isinstance(value, datetime):
        raise ValueError('Una fecha de calendario no contiene una hora de evento.')
    if isinstance(value, str) and len(value.strip()) == 10:
        raise ValueError('Una fecha de calendario no contiene una hora de evento.')
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        return result
    return result.astimezone(ZoneInfo(zone))

def display_timestamp(value, zone=DEFAULT_ZONE, *, seconds=True):
    if value in (None, ''):
        return ''
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and len(value.strip()) == 10:
        return value
    try:
        return local_datetime(value, zone).strftime('%Y-%m-%d %H:%M:%S' if seconds else '%Y-%m-%d %H:%M')
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        return str(value)

def parse_instant(value):
    """Require an absolute instant; never assign a timezone to ambiguous input."""
    if isinstance(value, str) and len(value.strip()) == 10:
        raise ValueError('El evento necesita fecha, hora y zona horaria.')
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('El evento necesita una zona horaria explícita.')
    return dt

def local_wall_instant(value, zone):
    """Interpret an explicitly entered gym calendar time; reject DST gaps/ambiguity."""
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is not None:
        return dt
    tz = ZoneInfo(zone)
    candidates = []
    from datetime import timezone
    for fold in (0, 1):
        aware = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                         dt.second, dt.microsecond, tzinfo=tz, fold=fold)
        back = aware.astimezone(timezone.utc).astimezone(tz)
        if (back.year, back.month, back.day, back.hour, back.minute, back.second, back.microsecond) == (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond):
            if not any(x.timestamp() == aware.timestamp() for x in candidates):
                candidates.append(aware)
    if len(candidates) != 1:
        raise ValueError('Esta hora local es inexistente o ambigua. Indica un offset explícito.')
    return candidates[0]

def business_today(widget):
    """Locate the connected gym for dialogs; never substitute the PC clock."""
    for obj in (widget, widget.winfo_toplevel(), getattr(widget, 'master', None)):
        db = getattr(obj, 'db', None)
        if db is not None:
            return db._today()
    raise ValueError('Consulta la fecha del gimnasio antes de abrir este formulario.')

def gym_clock(client, gym_id):
    clock = client.rpc('gym_local_clock', {'p_gym_id': gym_id}).execute().data
    if not isinstance(clock, dict):
        raise ValueError('El servidor no devolvió un reloj válido.')
    parse_instant(clock['now'])
    ZoneInfo(clock['timezone'])
    return clock

def ticket_access_note(result):
    if result.get('frozen'):
        return result.get('denial_message', 'Membresía congelada.')
    if result.get('result') != 'PERMITIDA':
        return ''
    if result.get('already_consumed_today'):
        return 'Ya registraste una entrada hoy. No se descontó otra entrada de tu tiquetera.'
    if result.get('ticket_consumed'):
        return f"Se descontó una entrada. Disponibles: {result.get('entries_remaining', 0)}."
    return ''

def checkin_label(row):
    if row.get('result') != 'PERMITIDA':
        return row.get('result', '')
    if row.get('already_consumed_today'):
        return 'Reentrada · sin descuento'
    if row.get('ticket_consumed'):
        return 'Autorizada · 1 entrada'
    return row.get('result', '')
