"""Valores enteros en pesos, sin convertir decimales en importes distintos."""
import re


def parse_amount(value):
    text = str(value).strip()
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{1,3}(?:,[0-9]{3})+)', text):
        raise ValueError('Escribe un valor entero en pesos; por ejemplo, 5000 o 5.000.')
    amount = int(text.replace('.', '').replace(',', ''))
    if amount > 1_000_000_000_000:
        raise ValueError('El valor es demasiado alto. Revisa los dígitos.')
    return amount
