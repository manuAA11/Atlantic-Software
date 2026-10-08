"""Rangos exclusivos para el seguimiento de tiqueteras."""
TICKET_BUCKETS = (
    ('empty', 'Sin entradas', 0, 0),
    ('one_five', '1–5 entradas', 1, 5),
    ('six_ten', '6–10 entradas', 6, 10),
    ('eleven_fifteen', '11–15 entradas', 11, 15),
    ('sixteen_twenty', '16–20 entradas', 16, 20),
    ('over_twenty', 'Más de 20 entradas', 21, None),
)


def ticket_groups(rows):
    groups = {key: [] for key, *_ in TICKET_BUCKETS}
    for row in rows:
        remaining = int(row['entries_remaining'])
        for key, _title, low, high in TICKET_BUCKETS:
            if remaining >= low and (high is None or remaining <= high):
                groups[key].append(row)
                break
    return groups


def spreadsheet_text(value):
    text = str(value if value is not None else '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
