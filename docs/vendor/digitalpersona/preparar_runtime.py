"""Restore the supplied Runtime without publishing SDK or changing vendor bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EDITIONS = {
    "GymSoft_Comercial_3.6.0": "x64",
    "GymSoft_ZTATTUZ_3.6.1_x64": "x64",
    "GymSoft_ZTATTUZ_3.6.1_x86": "x86",
}
MANIFEST = HERE / "sdk-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, metadata: dict) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Falta el archivo original: {path}")
    if path.stat().st_size != metadata["bytes"] or sha256(path) != metadata["sha256"]:
        raise ValueError(f"Integridad incorrecta: {path}")


def restore(sdk: Path, manifest: dict, editions: tuple[str, ...] = tuple(EDITIONS)) -> None:
    verify_file(sdk, manifest["source_archive"])
    for edition in editions:
        target = ROOT / edition / "DigitalPersonaRuntime"
        if not (ROOT / edition).is_dir() or target.is_symlink():
            raise ValueError(f"Edición o destino inválido: {target}")
    # Read and authenticate every selected entry before writing the project.
    payloads = {}
    with zipfile.ZipFile(sdk) as archive:
        for metadata in [manifest["license"]] + [
            file for runtime in manifest["runtimes"].values() for file in runtime["files"]
        ]:
            data = archive.read(metadata["source_path"])
            if len(data) != metadata["bytes"] or hashlib.sha256(data).hexdigest() != metadata["sha256"]:
                raise ValueError(f"Entrada SDK alterada: {metadata['source_path']}")
            payloads[metadata["source_path"]] = data
    for edition in editions:
        architecture = EDITIONS[edition]
        target = ROOT / edition / "DigitalPersonaRuntime"
        entries = manifest["runtimes"][architecture]["files"] + [manifest["license"]]
        for metadata in entries:
            path = target / metadata["path"]
            if path.exists():
                verify_file(path, metadata)
                continue
            if any(parent.is_symlink() for parent in path.parents if parent != ROOT.parent):
                raise ValueError(f"Destino contiene enlace simbólico: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(payloads[metadata["source_path"]])
            verify_file(path, metadata)


def verify(manifest: dict, editions: tuple[str, ...] = tuple(EDITIONS)) -> None:
    for edition in editions:
        architecture = EDITIONS[edition]
        target = ROOT / edition / "DigitalPersonaRuntime"
        runtime = manifest["runtimes"][architecture]
        for metadata in runtime["files"] + [manifest["license"]]:
            verify_file(target / metadata["path"], metadata)
        print(f"PASS {edition}: Runtime {architecture}, {len(runtime['files'])} archivos originales + EULA")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdk", nargs="?", type=Path, help="ZIP original reconstruido DigitalPersona 3.4.0")
    parser.add_argument("--verify", action="store_true", help="Comprobar los recursos ya restaurados")
    parser.add_argument("--edition", action="append", choices=EDITIONS, help="Restaurar/verificar solo esta edición; puede repetirse")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    editions = tuple(args.edition or EDITIONS)
    if not args.verify and args.sdk is None:
        parser.error("Indica el ZIP SDK original o usa --verify.")
    try:
        if not args.verify:
            restore(args.sdk, manifest, editions)
        verify(manifest, editions)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Runtime no preparado: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
