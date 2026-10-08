from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

PRODUCT_NAME = 'Atlantic Gym'
ADMIN_NAME = PRODUCT_NAME + " Administrador"
RECEPTION_NAME = PRODUCT_NAME + " Recepción"
VERSION = '3.6.0'

def resource_root() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))

def load_config(*, validate: bool = True) -> dict[str, str]:
    path = resource_root() / 'gymsoft_config.json'
    value = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    config = {
        'supabase_url': os.environ.get('GYMSOFT_SUPABASE_URL', value.get('supabase_url', '')).strip().rstrip('/'),
        'supabase_publishable_key': os.environ.get('GYMSOFT_SUPABASE_KEY', value.get('supabase_publishable_key', '')).strip(),
    }
    if not validate:
        return config
    url, key = config['supabase_url'], config['supabase_publishable_key']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.username or parsed.password:
        raise ValueError('El proveedor debe configurar el proyecto comercial en gymsoft_config.json antes de generar el instalador.')
    # Impide usar accidentalmente la conexión del proyecto de origen.
    if hashlib.sha256(parsed.hostname.encode()).hexdigest() == '04964743226cd3b81e02087451b283aea9a54e311cc98594b180798dcd09b807':
        raise ValueError('Esta edición requiere un proyecto comercial NUEVO.')
    if key.startswith('sb_secret_'):
        raise ValueError('No uses una clave secreta. Solo se admite la clave publicable.')
    if not key.startswith('sb_publishable_'):
        try:
            payload = key.split('.')[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
            if claims.get('role') != 'anon':
                raise ValueError()
        except Exception as error:
            raise ValueError('Usa una clave publicable de Supabase; nunca service_role.') from error
    return config
