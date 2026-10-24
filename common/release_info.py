"""Canonical platform version; product and architecture remain build parameters."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

VERSION = '3.8.0'
CHANNEL = 'beta'
SUPPORTED_SCHEMAS = frozenset({'core-1'})


def metadata(product, bits, *, repository=None):
    commit='unknown'
    if repository is not None:
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repository,stderr=subprocess.DEVNULL,text=True,timeout=3).strip()
        except (OSError,subprocess.SubprocessError):pass
    return dict(product=product,version=VERSION,architecture=f'windows-x{86 if bits==32 else 64}',channel=CHANNEL,
        build_date=datetime.now(timezone.utc).isoformat(),commit=commit)


def runtime_metadata(product, bits, repository=None):
    root=Path(getattr(sys,'_MEIPASS',Path(sys.executable).parent))
    path=root/'build-info.json'
    if getattr(sys,'frozen',False) and path.is_file():
        value=json.loads(path.read_text())
        if value.get('version')!=VERSION or value.get('product')!=product or value.get('architecture')!=f'windows-x{86 if bits==32 else 64}':
            raise ValueError('La identidad del paquete no coincide con el programa.')
        return value
    return metadata(product,bits,repository=repository)
