"""Create small ZIP parts for cloud transfer without changing the source archive."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


PART_BYTES = 25 * 1024 * 1024


def split_archive(source: Path, part_bytes: int = PART_BYTES) -> Path:
    source = source.resolve()
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise ValueError('Selecciona un archivo ZIP valido.')
    if part_bytes < 1 or part_bytes > PART_BYTES:
        raise ValueError('Cada parte debe ser de hasta 25 MiB.')
    destination = source.with_name(source.stem + '_partes')
    if destination.exists():
        raise ValueError('Ya existe la carpeta de partes: ' + str(destination))
    original_size = source.stat().st_size
    with source.open('rb') as stream:
        original_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    count = (original_size + part_bytes - 1) // part_bytes
    destination.mkdir()
    parts = []
    with source.open('rb') as stream:
        for index in range(1, count + 1):
            data = stream.read(part_bytes)
            name = source.stem + f'_parte_{index:03d}_de_{count:03d}.zip'
            metadata = {'format': 'ATLANTIC_ARCHIVE_PART_V1', 'source': source.name,
                        'source_bytes': original_size, 'source_sha256': original_hash,
                        'index': index, 'count': count,
                        'part_sha256': hashlib.sha256(data).hexdigest()}
            with zipfile.ZipFile(destination / name, 'x', compression=zipfile.ZIP_STORED) as archive:
                archive.writestr('MANIFEST.json', json.dumps(metadata, indent=2))
                archive.writestr('fragment.bin', data)
            parts.append(name)
            print(f'Parte {index}/{count}: {name}', flush=True)
    (destination / 'LEER_PRIMERO.txt').write_text(
        'El ZIP original no fue modificado. Adjunta todos los ZIP de esta carpeta.\n'
        'Cada archivo contiene un fragmento y su manifiesto SHA256.\n'
        'Original: ' + source.name + '\nSHA256: ' + original_hash + '\n', encoding='utf-8')
    return destination


def join_archives(parts: list[Path], target: Path) -> None:
    metadata = []
    for path in parts:
        with zipfile.ZipFile(path) as archive:
            item = json.loads(archive.read('MANIFEST.json'))
            if item.get('format') != 'ATLANTIC_ARCHIVE_PART_V1':
                raise ValueError('Formato de parte no reconocido.')
            metadata.append((item, path))
    metadata.sort(key=lambda pair: pair[0]['index'])
    if not metadata:
        raise ValueError('Faltan las partes.')
    first = metadata[0][0]
    if [item['index'] for item, _ in metadata] != list(range(1, first['count'] + 1)):
        raise ValueError('Faltan partes o hay indices repetidos.')
    for item, _ in metadata:
        if any(item[key] != first[key] for key in ('source', 'source_bytes', 'source_sha256', 'count')):
            raise ValueError('Las partes no pertenecen al mismo archivo.')
    if target.exists():
        raise ValueError('El archivo de destino ya existe.')
    temporary = target.with_name(target.name + '.reconstruyendo')
    digest = hashlib.sha256()
    try:
        with temporary.open('xb') as output:
            for item, path in metadata:
                with zipfile.ZipFile(path) as archive:
                    data = archive.read('fragment.bin')
                if hashlib.sha256(data).hexdigest() != item['part_sha256']:
                    raise ValueError('Una parte no coincide con su SHA256.')
                digest.update(data); output.write(data)
        if digest.hexdigest() != first['source_sha256'] or temporary.stat().st_size != first['source_bytes']:
            raise ValueError('El archivo completo no coincide con el original.')
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('El ZIP reconstruido contiene un archivo corrupto.')
        temporary.rename(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', type=Path)
    args = parser.parse_args()
    files = args.files
    gui = not files
    if gui:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        files = [Path(p) for p in filedialog.askopenfilenames(title='Selecciona los ZIP originales de DigitalPersona', filetypes=[('Archivos ZIP', '*.zip')])]
        root.destroy()
    if not files:
        return 0
    try:
        folders = [split_archive(path) for path in files]
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        if gui:
            from tkinter import messagebox
            messagebox.showerror('No se pudo dividir el archivo', str(error))
        return 1
    message = 'Originales conservados. Adjunta todos los ZIP de estas carpetas:\n' + '\n'.join(str(p) for p in folders)
    print(message)
    if gui:
        from tkinter import messagebox
        messagebox.showinfo('Partes listas para adjuntar', message)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
