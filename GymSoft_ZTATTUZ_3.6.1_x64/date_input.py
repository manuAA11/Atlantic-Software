"""Máscara de fecha compartida: respeta la selección y la posición del cursor."""
import tkinter as tk


def format_digits(value, *, deleting=False):
    digits = ''.join(c for c in value if c.isascii() and c.isdigit())[:8]
    result = digits[:2]
    if len(digits) > 2 or (len(digits) == 2 and not deleting):
        result += '/' + digits[2:4]
    if len(digits) > 4 or (len(digits) == 4 and not deleting):
        result += '/' + digits[4:]
    return result


def attach_date_mask(entry, variable):
    if getattr(entry, '_date_mask_attached', False):
        return
    entry._date_mask_attached = True
    state = {'text': variable.get(), 'job': None, 'changing': False}

    def apply():
        state['job'] = None
        if not entry.winfo_exists():
            return
        raw = variable.get()
        cursor = entry.index(tk.INSERT)
        previous = state['text']
        deleting = (len(raw) < len(previous) or
                    sum(c.isdigit() for c in raw) < sum(c.isdigit() for c in previous))
        formatted = format_digits(raw, deleting=deleting)
        if formatted != raw:
            # Tk ya ejecutó su inserción. La máscara se aplica después, no dentro
            # del trace donde Tk todavía no ha adelantado el cursor.
            count = sum(c.isascii() and c.isdigit() for c in raw[:cursor])
            position = 0
            seen = 0
            while position < len(formatted) and seen < count:
                seen += formatted[position].isdigit()
                position += 1
            if not deleting:
                while position < len(formatted) and formatted[position] == '/':
                    position += 1
            state['changing'] = True
            variable.set(formatted)
            state['changing'] = False
            entry.icursor(position)
        state['text'] = formatted

    def schedule(*_):
        if state['changing']:
            return
        if state['job'] is not None:
            entry.after_cancel(state['job'])
        state['job'] = entry.after_idle(apply)

    trace = variable.trace_add('write', schedule)

    def cleanup(event):
        if event.widget is not entry:
            return
        if state['job'] is not None:
            entry.after_cancel(state['job'])
        variable.trace_remove('write', trace)

    entry.bind('<Destroy>', cleanup, add='+')
