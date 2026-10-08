"""Validación de planes por días y tiqueteras configurables."""
from calendar import monthrange
from datetime import date, datetime, timedelta
from money_input import parse_amount


def validate_plan(name, days, price, entry_limit=None):
    name = str(name).strip()
    try:
        days = int(str(days))
        price = parse_amount(price)
        limit = None if entry_limit is None else int(str(entry_limit))
    except (ValueError, TypeError):
        raise ValueError('Escribe números enteros en días, precio y cantidad de entradas.') from None
    if not name:
        raise ValueError('Escribe el nombre del plan.')
    if not 1 <= days <= 36500 or price < 0:
        raise ValueError('La vigencia debe ser de al menos un día y el precio no puede ser negativo.')
    if limit is not None and not 1 <= limit <= 1000000:
        raise ValueError('La tiquetera debe incluir entre 1 y 1.000.000 de entradas.')
    return name, days, price, limit


def plan_label(plan, money):
    allowance = (f"{plan['entry_limit']} entradas · " if plan.get('entry_limit') is not None else '')
    return f"{plan['name']} · {allowance}{plan_duration(plan)} · {money(plan['price'])}"


def validate_months(value, entry_limit):
    if value is None:
        return None
    try:
        months = int(str(value))
    except (ValueError, TypeError):
        raise ValueError('Escribe un número entero de meses.') from None
    if entry_limit is None or not 1 <= months <= 120:
        raise ValueError('La vigencia de una tiquetera debe ser de 1 a 120 meses.')
    return months


def plan_duration(plan):
    months = plan.get('duration_months')
    if months is not None:
        return f"{months} {'mes calendario' if int(months) == 1 else 'meses calendario'}"
    return f"{plan['duration_days']} días"


def plan_end_date(plan, start):
    if isinstance(start, str):
        start = date.fromisoformat(start)
    months = plan.get('duration_months')
    if months is None:
        return start + timedelta(days=int(plan['duration_days']) - 1)
    index = start.year * 12 + start.month - 1 + int(months)
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return date(year, month, min(start.day, monthrange(year, month)[1])) - timedelta(days=1)


def carryover_values(plan, start, used, today):
    try:
        start = date.fromisoformat(start)
        used = int(str(used))
    except (ValueError, TypeError):
        raise ValueError('Revisa la fecha de inicio y las entradas ya utilizadas.') from None
    limit = plan.get('entry_limit')
    if limit is None or not 0 <= used <= int(limit):
        raise ValueError('Las entradas utilizadas deben estar entre cero y el cupo de la tiquetera.')
    if start > today:
        raise ValueError('Una tiquetera ya iniciada no puede comenzar en una fecha futura.')
    return used, plan_end_date(plan, start)


def membership_request(gym_id, client_id, plan_id, start_date, amount,
                       payment_method, payment_reference='', notes='', *,
                       carryover=False, initial_entries_used=0, request_id=None):
    if carryover:
        from uuid import UUID
        try:
            request_id = str(UUID(str(request_id)))
            used = int(str(initial_entries_used))
        except (ValueError, TypeError, AttributeError):
            raise ValueError('La solicitud de traslado no es válida. Abre de nuevo el formulario.') from None
        return 'register_ticket_carryover', {
            'p_gym_id': gym_id, 'p_client_id': int(client_id), 'p_plan_id': int(plan_id),
            'p_start': start_date, 'p_entries_used': used,
            'p_notes': notes.strip(), 'p_request_id': request_id,
        }
    if initial_entries_used:
        raise ValueError('Usa «Tiquetera ya iniciada» para trasladar entradas utilizadas.')
    return 'add_membership_accumulating', {
        'p_gym_id': gym_id, 'p_client_id': int(client_id), 'p_plan_id': int(plan_id),
        'p_requested_start': start_date, 'p_amount': int(amount),
        'p_payment_method': payment_method.strip(),
        'p_payment_reference': payment_reference.strip(), 'p_notes': notes.strip(),
    }


def membership_form_values(start, amount):
    try:
        start = datetime.strptime(str(start).strip(), '%d/%m/%Y').date().isoformat()
    except ValueError:
        raise ValueError('Escribe una fecha válida en formato DD/MM/AAAA.') from None
    try:
        amount = parse_amount(amount)
    except ValueError:
        raise ValueError('Escribe un valor pagado válido, sin decimales.') from None
    if amount < 0:
        raise ValueError('El valor pagado no puede ser negativo.')
    return start, amount
