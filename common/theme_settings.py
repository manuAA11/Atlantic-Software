"""Local appearance only; independent of gym, cloud credentials and architecture."""
import json
import os
from pathlib import Path
import sys
import tempfile

THEMES = {'dark': 'Oscuro', 'minimal': 'Minimal'}


def preference_path():
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'AtlanticGym' / 'appearance.json'


def load_theme(path=None):
    try:
        value = json.loads(Path(path or preference_path()).read_text(encoding='utf-8'))
        name = value.get('theme') if isinstance(value, dict) else None
        return name if name in THEMES else 'dark'
    except (OSError, ValueError, TypeError):
        return 'dark'


def save_theme(name, path=None):
    if name not in THEMES:
        raise ValueError('Selecciona un tema disponible.')
    target = Path(path or preference_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='appearance-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({'theme': name}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
