"""Package the complete Atlantic application with its incorporated object Runtime.

Development sources only: this never compiles, approves, or produces final installers.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SDK_MANIFEST = ROOT / "docs/vendor/digitalpersona/sdk-manifest.json"
SHARED = {"backend", "common", "supabase", "onboarding", "deployment", "assets", "docs", "evidence", "tools", "recovery", "research"}
ROOT_FILES = {"AGENTS.md", ".env.example", ".gitignore", "CHANGELOG_EN_DESARROLLO.md", "ESTADO_IMPLEMENTACION.md", "GUIA_CONGELACION_Y_HORAS.md", "INFORME_VALIDACION_EN_DESARROLLO.md", "temporal_inventory.txt", "temporal_inventory_current.txt"}
PRODUCTS = {
    "AtlanticGym": {"GymSoft_Comercial_3.6.0": "x64"},
    "ZTATTUZ": {"GymSoft_ZTATTUZ_3.6.1_x64": "x64", "GymSoft_ZTATTUZ_3.6.1_x86": "x86"},
}
REQUIRED = ("app.py", "reception_app.py", "atlantic_ui.py", "desktop_ui.py", "icono.ico", "icono_recepcion.ico", "requirements.txt", "requirements-build.txt", "release_readiness.json", "release_gate.py", "gymsoft_config.json", "tests/backend_sql_flow.mjs", "preparar_entorno.py", "PREPARAR_PYTHON.bat", "CREAR_INSTALADORES.bat", "INICIAR_ADMINISTRADOR.bat", "INICIAR_RECEPCION.bat", "build_windows.py")
PRIVATE_PATTERN = re.compile(rb"(?<![A-Za-z0-9])(?:sb_secret|prv_(?:test|prod)|(?:test|prod)_(?:events|integrity))_[A-Za-z0-9_-]{16,}")
JWT_PATTERN = re.compile(rb"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}")
FORBIDDEN_DIRS = {".git", ".venv", "node_modules", "__pycache__", "salida", "dist", "build", ".temp", ".pytest_cache"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_relative(name: str) -> None:
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or ".." in path.parts or ":" in name:
        raise ValueError(f"Ruta inválida para el paquete: {name}")
    if any(part in FORBIDDEN_DIRS or part.startswith(".venv_respaldo_") for part in path.parts):
        raise ValueError(f"Archivo local no distribuible: {name}")
    if any(part.lower() in {"sdk", "samples", "headers", "include"} for part in path.parts):
        raise ValueError(f"SDK fuente no permitido en el paquete de aplicación: {name}")
    if (path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example"
            or path.suffix.lower() in {".pem", ".key", ".pyc"}):
        raise ValueError(f"Archivo privado o temporal no distribuible: {name}")


def check_no_secrets(name: str, data: bytes) -> None:
    if PRIVATE_PATTERN.search(data) or re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data):
        raise ValueError(f"Credencial privada detectada; no se empaqueta: {name}")
    for token in JWT_PATTERN.findall(data):
        try:
            payload = json.loads(base64.urlsafe_b64decode(token.split(b".")[1] + b"==="))
        except (ValueError, UnicodeError):
            continue
        if isinstance(payload, dict) and payload.get("role") == "service_role":
            raise ValueError(f"JWT privado de servidor detectado; no se empaqueta: {name}")
    if PurePosixPath(name).name == "gymsoft_config.json":
        config = json.loads(data.decode("utf-8-sig"))
        if set(config) != {"supabase_url", "supabase_publishable_key"}:
            raise ValueError(f"La configuración de escritorio debe ser únicamente publicable: {name}")


def select_sources(names: list[str], editions: dict[str, str]) -> list[str]:
    selected = []
    for name in sorted(set(names)):
        if not name:
            continue
        top = PurePosixPath(name).parts[0]
        if top in SHARED or top in editions or name in ROOT_FILES:
            validate_relative(name)
            selected.append(name)
    return selected


def runtime_entries(edition: str, architecture: str, sdk: dict) -> dict[str, dict]:
    metadata = sdk["runtimes"][architecture]["files"] + [sdk["license"]]
    return {f"{edition}/DigitalPersonaRuntime/{file['path']}": file for file in metadata}


def validate_component_inventory(name: str, expected_runtime: dict[str, dict]) -> None:
    path = PurePosixPath(name)
    if "DigitalPersonaRuntime" in path.parts and name not in expected_runtime:
        if path.name not in {".gitignore", "MANIFEST.json", "README.md"}:
            raise ValueError(f"Recurso Runtime no autorizado por inventario: {name}")
    if path.suffix.lower() in {".exe", ".dll", ".msi", ".cab"} and name not in expected_runtime:
        raise ValueError(f"Binario externo al Runtime incorporado no permitido: {name}")


def read_sources(root: Path, names: list[str], editions: dict[str, str], sdk: dict) -> dict[str, bytes]:
    expected_runtime = {name: meta for edition, architecture in editions.items()
                        for name, meta in runtime_entries(edition, architecture, sdk).items()}
    selected = set(select_sources(names, editions)) | set(expected_runtime)
    result = {}
    for name in sorted(selected):
        validate_relative(name)
        path = root / name
        if path.is_symlink() or not path.is_file() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"Archivo ausente o enlace no permitido: {name}")
        validate_component_inventory(name, expected_runtime)
        data = path.read_bytes()
        check_no_secrets(name, data)
        if name in expected_runtime:
            meta = expected_runtime[name]
            if len(data) != meta["bytes"] or digest(data) != meta["sha256"]:
                raise ValueError(f"Runtime alterado o arquitectura incorrecta: {name}")
        result[name] = data
    for edition in editions:
        for required in REQUIRED:
            if f"{edition}/{required}" not in result:
                raise ValueError(f"Aplicación incompleta: {edition}/{required}")
    return result


def runtime_terms() -> str:
    return (
        "ATLANTIC GYM: CONDICIONES DEL COMPONENTE DIGITALPERSONA\n\n"
        "Esta entrega es la aplicación Atlantic Gym que incorpora el Runtime DigitalPersona en código objeto. "
        "No se concede una licencia para redistribuir el Runtime de forma independiente ni para redistribuir el SDK, sus headers o sus samples.\n\n"
        "La distribución y utilización de esta aplicación que incorpora el Runtime se sujetan a los términos íntegros de la EULA original "
        "DigitalPersona/Crossmatch incluida en DigitalPersonaRuntime/Licenses/EULA SDK.rtf de cada edición. "
        "Esa EULA se incorpora expresamente a los términos de esta entrega y conserva sus restricciones, avisos y titularidad. "
        "No se amplían los permisos del proveedor ni se modifican sus archivos o sus avisos. "
        "El permiso de redistribución aplicable es §1.2(c): código objeto incorporado a la aplicación, "
        "avisos originales y términos no menos restrictivos.\n\n"
        "Antes de instalar o utilizar el componente, lea y acepte la EULA original. "
        "Si no acepta sus términos, no instale ni utilice el componente. "
        "Los instaladores del proveedor y Atlantic presentan los términos pertinentes durante la instalación.\n"
    )


def package_readme(product: str, editions: dict[str, str]) -> str:
    return (
        f"# {product}: aplicación completa en desarrollo\n\n"
        "Incluye la aplicación Atlantic recuperada, fuentes, recursos aprobados, configuración pública, backend, migraciones, pruebas "
        "y Runtime DigitalPersona objeto incorporado en cada edición. No necesita reconstruir partes ni crear carpetas Runtime. "
        "No incluye SDK fuentes/headers/samples, secretos, datos de clientes, venv ni node_modules.\n\n"
        "Esta entrega sigue EN DESARROLLO: no es un instalador final ni acredita pilotos externos o hardware. "
        "El manifiesto APP_MANIFEST.json autentica todos sus archivos y registra la aceptación pendiente. "
        "Conserve release_readiness.json; no cambie los criterios para forzar la generación final.\n\n"
        "1. Extraiga el ZIP en una carpeta nueva.\n"
        "2. Abra la carpeta de su edición y ejecute INICIAR_ADMINISTRADOR.bat o INICIAR_RECEPCION.bat. "
        "Estos accesos preparan las dependencias y abren la aplicación desde las fuentes.\n"
        "3. Comercial y ZTATTUZ x64 usan CPython 3.13/3.14 estándar de 64 bits. ZTATTUZ x86 usa Python de 32 bits en Windows de 32 bits. "
        "Con el Python 3.14 de 64 bits del usuario, elija la edición x64.\n"
        "4. Configure gimnasio, WhatsApp/Wompi y dispositivos desde la aplicación y su backend según docs/INTEGRACIONES_Y_WINDOWS.md. "
        "No coloque secretos privados en el escritorio.\n"
        "5. CREAR_INSTALADORES.bat genera la entrega final cuando la evidencia válida satisface sus requisitos; "
        "el empaquetado de estas fuentes no altera ese requisito.\n\n"
        "Lea CONDICIONES_RUNTIME.txt y la EULA original incluida antes de instalar/utilizar DigitalPersona. "
        "Runtime objeto únicamente incorporado a Atlantic Gym, con todos los archivos y avisos intactos. "
        "Los paquetes fuente y los instaladores de cada producto son independientes; no mezcle Comercial y ZTATTUZ. "
        "El panel Propietario de Comercial es privado del propietario, no se entrega al cliente.\n\n"
        "Ediciones incluidas: " + ", ".join(editions) + ".\n"
    )


def validate_archive(path: Path, sdk: dict) -> dict:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("CRC incorrecto en el paquete de aplicación.")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Entradas duplicadas en el paquete.")
        for name in names:
            validate_relative(name)
        roots = {PurePosixPath(name).parts[0] for name in names}
        if len(roots) != 1:
            raise ValueError("La entrega debe tener una sola carpeta de aplicación.")
        prefix = roots.pop() + "/"
        manifest = json.loads(archive.read(prefix + "APP_MANIFEST.json"))
        if manifest.get("type") != "APPLICATION_COMPLETE_DEVELOPMENT" or manifest.get("final_release") is not False:
            raise ValueError("El paquete no está identificado como aplicación en desarrollo.")
        editions = PRODUCTS.get(manifest.get("product"))
        if editions is None or manifest.get("editions") != editions:
            raise ValueError("Ediciones o arquitecturas incorrectas.")
        expected_runtime = {name: meta for edition, architecture in editions.items()
                            for name, meta in runtime_entries(edition, architecture, sdk).items()}
        recorded = {prefix + file["path"]: file for file in manifest["files"]}
        if len(recorded) != len(manifest["files"]) or set(names) != set(recorded) | {prefix + "APP_MANIFEST.json"}:
            raise ValueError("El inventario no coincide con el contenido completo.")
        for name, meta in recorded.items():
            if meta["path"] not in {"README.md", "CONDICIONES_RUNTIME.txt"} and not select_sources([meta["path"]], editions):
                raise ValueError(f"Contenido ajeno a esta aplicación: {meta['path']}")
            validate_component_inventory(meta["path"], expected_runtime)
            data = archive.read(name)
            if len(data) != meta["bytes"] or digest(data) != meta["sha256"]:
                raise ValueError(f"Integridad incorrecta: {meta['path']}")
            check_no_secrets(meta["path"], data)
        for edition, architecture in editions.items():
            for name, expected in runtime_entries(edition, architecture, sdk).items():
                data = archive.read(prefix + name)
                if len(data) != expected["bytes"] or digest(data) != expected["sha256"]:
                    raise ValueError(f"Runtime incorrecto en aplicación: {name}")
            for required in REQUIRED:
                if prefix + f"{edition}/{required}" not in recorded:
                    raise ValueError(f"Aplicación incompleta: {edition}/{required}")
        for required in ("README.md", "CONDICIONES_RUNTIME.txt", "docs/vendor/digitalpersona/sdk-manifest.json"):
            if prefix + required not in recorded:
                raise ValueError(f"Falta el aviso/inventario de entrega: {required}")
        return manifest


def restore_runtime_from_package(path: Path, root: Path, editions: list[str], sdk: dict, expected_sha256: str) -> None:
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256) or digest(path.read_bytes()) != expected_sha256.lower():
        raise ValueError("El SHA-256 del paquete completo no coincide con el autorizado.")
    manifest = validate_archive(path, sdk)
    if not editions or any(edition not in manifest["editions"] for edition in editions):
        raise ValueError("La edición seleccionada no pertenece al paquete de aplicación.")
    pending = []
    with zipfile.ZipFile(path) as archive:
        prefix = PurePosixPath(archive.namelist()[0]).parts[0] + "/"
        for edition in editions:
            if not (root / edition).is_dir() or (root / edition).is_symlink():
                raise ValueError(f"No existe la edición de destino: {edition}")
            architecture = manifest["editions"][edition]
            for relative, meta in runtime_entries(edition, architecture, sdk).items():
                target = root / relative
                if any(parent.is_symlink() for parent in target.parents) or target.is_symlink():
                    raise ValueError(f"Destino contiene enlace simbólico: {relative}")
                data = archive.read(prefix + relative)
                if target.exists():
                    if not target.is_file() or len(target.read_bytes()) != meta["bytes"] or digest(target.read_bytes()) != meta["sha256"]:
                        raise ValueError(f"Conserva el recurso existente distinto; no se sobrescribe: {relative}")
                else:
                    pending.append((target, data))
    # All package bytes and existing destinations pass before the first write.
    for target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    print("PASS Runtime original incorporado restaurado: " + ", ".join(editions))


def create_package(root: Path, output: Path, product: str, label: str, source_names: list[str], sdk: dict) -> dict:
    editions = PRODUCTS[product]
    name = f"{product}_APLICACION_COMPLETA_EN_DESARROLLO_{label}"
    entries = read_sources(root, source_names, editions, sdk)
    entries["README.md"] = package_readme(product, editions).encode("utf-8")
    entries["CONDICIONES_RUNTIME.txt"] = runtime_terms().encode("utf-8")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root))
    acceptance = {
        edition: json.loads(entries[f"{edition}/release_readiness.json"])
        for edition in editions
    }
    manifest = {
        "type": "APPLICATION_COMPLETE_DEVELOPMENT", "final_release": False,
        "product": product, "editions": editions, "source_commit": commit,
        "includes_uncommitted_sources": dirty, "supported_python": ["3.13", "3.14"],
        "digitalpersona_source_archive": sdk["source_archive"],
        "runtime_distribution": "Object Runtime incorporated into Atlantic application under original EULA 1.2(c); no standalone Runtime or SDK sources.",
        "acceptance_snapshot": acceptance,
        "files": [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(entries.items())],
    }
    entries["APP_MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    target = output / (name + ".zip")
    temporary = output / (name + ".zip.tmp")
    if target.exists() or temporary.exists():
        raise ValueError(f"La salida ya existe; conserva su respaldo: {target}")
    try:
        with zipfile.ZipFile(temporary, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, data in sorted(entries.items()):
                archive.writestr(name + "/" + relative, data)
        validate_archive(temporary, sdk)
        temporary.rename(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {"file": target.name, "bytes": target.stat().st_size, "sha256": digest(target.read_bytes()), "files": len(entries), "editions": editions, "final_release": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/workspace/deliverables-private"))
    parser.add_argument("--label", default="20261008")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--verify-archive", "--verify-package", dest="verify_archive", type=Path)
    operation.add_argument("--restore-runtime-from-package", type=Path)
    parser.add_argument("--edition", action="append", choices=sorted(edition for editions in PRODUCTS.values() for edition in editions))
    parser.add_argument("--expected-sha256", help="SHA-256 externo conocido del ZIP completo; obligatorio para restauración")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.label):
        parser.error("La etiqueta solo admite letras, cifras, guion y guion bajo.")
    try:
        sdk = json.loads(SDK_MANIFEST.read_text(encoding="utf-8"))
        if args.restore_runtime_from_package:
            if not args.expected_sha256 or not args.edition:
                parser.error("La restauración requiere --edition y --expected-sha256 del ZIP completo autorizado.")
            restore_runtime_from_package(args.restore_runtime_from_package, ROOT, args.edition, sdk, args.expected_sha256)
            return 0
        if args.verify_archive:
            if args.expected_sha256 and digest(args.verify_archive.read_bytes()) != args.expected_sha256.lower():
                raise ValueError("El SHA-256 del paquete completo no coincide con el autorizado.")
            manifest = validate_archive(args.verify_archive, sdk)
            print(f"PASS {args.verify_archive.name}: {len(manifest['files']) + 1} archivos íntegros; Runtime incorporado por arquitectura")
            return 0
        source_names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
        result = {"type": "APPLICATION_COMPLETE_DEVELOPMENT", "final_release": False, "packages": []}
        for product in PRODUCTS:
            item = create_package(ROOT, args.output, product, args.label, source_names, sdk)
            result["packages"].append(item)
            print(json.dumps(item, ensure_ascii=False))
        (args.output / "MANIFEST.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        print(f"Paquete no generado: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
