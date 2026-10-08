"""Prepare a supported CPython environment while preserving existing files."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import struct
import subprocess
import sys
import sysconfig
from uuid import uuid4
import venv


SUPPORTED_VERSIONS = ((3, 13), (3, 14))


def runtime_is_supported(version, bits, expected_bits, implementation='cpython', gil_disabled=False):
    return (tuple(version[:2]) in SUPPORTED_VERSIONS and bits == expected_bits
            and implementation == 'cpython' and not gil_disabled)


def require_runtime(bits: int) -> None:
    if not runtime_is_supported(sys.version_info, struct.calcsize('P') * 8, bits,
                                sys.implementation.name, sysconfig.get_config_var('Py_GIL_DISABLED')):
        raise RuntimeError(f'Necesitas CPython 3.13 o 3.14 de {bits} bits (edicion estandar con GIL). '
                           f'Este interprete es {sys.version.split()[0]} de {struct.calcsize("P") * 8} bits.')


def environment_python(environment: Path) -> Path:
    return environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def interpreter_info(executable: Path) -> dict | None:
    code = ("import json,sys,struct,sysconfig;print(json.dumps({'version':list(sys.version_info[:2]),"
            "'bits':struct.calcsize('P')*8,'prefix':sys.prefix,'base_prefix':sys.base_prefix,"
            "'implementation':sys.implementation.name,'gil_disabled':sysconfig.get_config_var('Py_GIL_DISABLED')}))")
    try:
        result = subprocess.run([str(executable), '-I', '-c', code], capture_output=True,
                                text=True, timeout=20, check=True)
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def valid_environment(environment: Path, bits: int) -> bool:
    info = interpreter_info(environment_python(environment))
    return bool(info and runtime_is_supported(info.get('version', []), info.get('bits'), bits,
                                             info.get('implementation'), info.get('gil_disabled'))
                and Path(info['prefix']).resolve() == environment.resolve()
                and Path(info['prefix']).resolve() != Path(info['base_prefix']).resolve())


def prepare_environment(root: Path, bits: int) -> str:
    # Check the replacement interpreter BEFORE renaming any existing files.
    require_runtime(bits)
    root = root.resolve()
    environment = root / '.venv'
    if valid_environment(environment, bits):
        info = interpreter_info(environment_python(environment))
        print(f'Entorno listo: Python {".".join(map(str, info["version"]))} de {bits} bits.')
        return 'reused'
    backup = None
    if environment.exists() or environment.is_symlink():
        backup = root / ('.venv_respaldo_' + datetime.now().strftime('%Y%m%d_%H%M%S')
                         + '_' + uuid4().hex[:8])
        environment.rename(backup)
        print('Entorno anterior conservado en: ' + backup.name)
    print(f'Creando .venv con Python {sys.version.split()[0]} de {bits} bits...')
    try:
        venv.EnvBuilder(with_pip=True).create(environment)
        if not valid_environment(environment, bits):
            raise RuntimeError('No se pudo comprobar la version y arquitectura del nuevo entorno.')
    except Exception:
        if backup is not None:
            print('La copia del entorno anterior sigue disponible en: ' + backup.name)
        raise
    print(f'Entorno listo: Python {sys.version.split()[0]} de {bits} bits.')
    return 'created'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bits', type=int, choices=(32, 64), required=True)
    parser.add_argument('--check', action='store_true', help='Only check the current interpreter; do not change files.')
    parser.add_argument('--check-environment', action='store_true', help='Only check .venv; do not change files.')
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parent
        if args.check:
            require_runtime(args.bits)
        elif args.check_environment:
            return 0 if valid_environment(root / '.venv', args.bits) else 1
        else:
            prepare_environment(root, args.bits)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('No se pudo preparar Python: ' + str(error))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
