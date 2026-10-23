"""Controlled installer download and handoff; never executes remote command text."""
from __future__ import annotations
from contextlib import ExitStack, closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlsplit, urljoin
import zipfile

import httpx

TRUSTED_ASSET_HOSTS = {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
STATES = {'NO_UPDATE','UPDATE_AVAILABLE','UPDATE_DOWNLOADED','UPDATE_VERIFIED',
          'UPDATE_INSTALLED','UPDATE_FAILED','UPDATE_ROLLED_BACK'}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Versión inválida.')
    return tuple(int(item) for item in value.split('.'))


@dataclass(frozen=True)
class Release:
    version: str
    architecture: str
    channel: str
    installer_url: str
    sha256: str
    bytes: int
    minimum_schema: str
    policy: str = 'OPTIONAL'
    product: str = 'Atlantic Gym'
    variant: str = 'ztattuz'
    notes: str = ''

    @classmethod
    def parse(cls, value, *, architecture, channel, variant='ztattuz'):
        result = cls(**{key: value[key] for key in cls.__dataclass_fields__ if key in value})
        version_tuple(result.version)
        if value.get('variant') != variant or variant not in {'ztattuz','commercial'}:
            raise ValueError('El instalador pertenece a otra edición del producto.')
        if result.product != 'Atlantic Gym' or result.architecture != architecture or architecture not in {'windows-x86','windows-x64'}:
            raise ValueError('La actualización no corresponde a esta arquitectura o producto.')
        if channel not in {'stable','beta'} or result.channel != channel or result.policy not in {'OPTIONAL','RECOMMENDED','REQUIRED'}:
            raise ValueError('Canal o política de actualización inválidos.')
        if not re.fullmatch(r'[a-f0-9]{64}', result.sha256) or type(result.bytes) is not int or not 0 < result.bytes <= 1073741824:
            raise ValueError('SHA256 o tamaño de actualización inválidos.')
        url = urlsplit(result.installer_url)
        if (url.scheme != 'https' or url.netloc != 'github.com' or url.query or url.fragment
            or not re.fullmatch(r'/manuAA11/Atlantic-Software/releases/download/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.exe', url.path)
            or '..' in url.path):
            raise ValueError('La fuente del instalador no está permitida.')
        if not isinstance(result.minimum_schema, str) or not result.minimum_schema:
            raise ValueError('Falta la compatibilidad de schema.')
        return result


class UpdateJournal:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder/'update-history.json'
        self.value = json.loads(self.path.read_text()) if self.path.exists() else {'state':'NO_UPDATE','history':[],'pending':None,'last_known_good':None}

    def record(self, state, **data):
        if state not in STATES: raise ValueError('Estado no permitido.')
        event = dict(state=state, at=datetime.now(timezone.utc).isoformat(), **data)
        self.value.update(state=state)
        self.value['history'] = (self.value['history']+[event])[-200:]
        self.save()

    def save(self):
        fd, temporary = tempfile.mkstemp(dir=self.folder, prefix='.history-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                json.dump(self.value, output, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally: Path(temporary).unlink(missing_ok=True)


class Updater:
    def __init__(self, folder, architecture, channel, current_version, *, schema_supported, busy=lambda:False,
                 http=None, launcher=None, variant='ztattuz'):
        self.variant = variant
        self.journal = UpdateJournal(folder)
        self.architecture, self.channel, self.current_version = architecture, channel, current_version
        self.schema_supported, self.busy = schema_supported, busy
        self.http = http or httpx.Client(follow_redirects=False, timeout=30)
        self.launcher = launcher or self._launch_windows
        self.lock = threading.Lock()
        self.prepared = None
        self.maintenance = None

    def select(self, releases):
        candidates = []
        for value in releases:
            try: release=Release.parse(value, architecture=self.architecture, channel=self.channel, variant=self.variant)
            except (ValueError, TypeError, KeyError): continue
            if version_tuple(release.version)>version_tuple(self.current_version): candidates.append(release)
        result=max(candidates, key=lambda release:version_tuple(release.version), default=None)
        self.journal.record('UPDATE_AVAILABLE' if result else 'NO_UPDATE', version=result.version if result else self.current_version)
        return result

    def path(self, release):
        # Never use a remote filename or a server-supplied local path.
        return self.journal.folder/f'AtlanticGym-{release.variant}-{release.version}-{release.architecture}-{release.sha256[:12]}.exe'

    def verify(self, release, path):
        Release.parse(vars(release), architecture=self.architecture, channel=self.channel, variant=self.variant)
        path=Path(path)
        if path.is_symlink() or path.resolve().parent!=self.journal.folder or path.resolve()!=self.path(release):
            raise ValueError('Ruta local de actualización inválida.')
        digest=hashlib.sha256(); size=0
        with path.open('rb') as source:
            for block in iter(lambda:source.read(1024*1024), b''):
                size+=len(block);digest.update(block)
        if size!=release.bytes or digest.hexdigest()!=release.sha256:
            raise ValueError('El instalador no coincide con su SHA256 y tamaño publicados.')
        return path

    def download(self, release):
        Release.parse(vars(release), architecture=self.architecture, channel=self.channel, variant=self.variant)
        with self.lock:
            fd, name=tempfile.mkstemp(dir=self.journal.folder, prefix='.download-',suffix='.part')
            path=Path(name)
            try:
                digest=hashlib.sha256(); size=0; url=release.installer_url
                with os.fdopen(fd, 'wb') as output:
                    for redirects in range(6):
                        parsed=urlsplit(url)
                        if parsed.scheme!='https' or parsed.hostname not in TRUSTED_ASSET_HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
                            raise ValueError('Redirección de descarga no permitida.')
                        with self.http.stream('GET',url,headers={'Accept-Encoding':'identity'}) as response:
                            if response.status_code in (301,302,303,307,308):
                                url=urljoin(url,response.headers.get('location',''))
                                continue
                            response.raise_for_status()
                            declared=response.headers.get('content-length')
                            if declared and int(declared)!=release.bytes: raise ValueError('Tamaño remoto inesperado.')
                            for block in response.iter_bytes():
                                size+=len(block)
                                if size>release.bytes: raise ValueError('La descarga supera el tamaño publicado.')
                                output.write(block);digest.update(block)
                            break
                    else: raise ValueError('Demasiadas redirecciones.')
                    output.flush();os.fsync(output.fileno())
                self.journal.record('UPDATE_DOWNLOADED', version=release.version)
                if size!=release.bytes or digest.hexdigest()!=release.sha256: raise ValueError('Descarga incompleta o checksum incorrecto.')
                destination=self.path(release)
                if destination.is_symlink(): raise ValueError('Destino de descarga inválido.')
                os.replace(path,destination)
                self.verify(release,destination)
                self.journal.record('UPDATE_VERIFIED',version=release.version)
                return destination
            except Exception:
                self.journal.record('UPDATE_FAILED',version=release.version,reason='download_or_verification')
                raise
            finally:path.unlink(missing_ok=True)

    def backup(self, roots):
        directory=self.journal.folder/'backups';directory.mkdir(exist_ok=True)
        target=directory/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip')
        with tempfile.TemporaryDirectory() as temporary, zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
            for index, root in enumerate(roots):
                root=Path(root).resolve()
                if not root.exists():continue
                for path in sorted(root.rglob('*')):
                    if path.suffix=='.lock' or not path.is_file() or path.is_symlink() or self.journal.folder in path.resolve().parents:continue
                    name=f'{index}-{root.name}/'+path.relative_to(root).as_posix()
                    if path.suffix.lower() in {'.db','.sqlite','.sqlite3'}:
                        # SQLite backup API includes committed WAL pages consistently.
                        copy=Path(temporary)/'database.sqlite'
                        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(copy)) as destination:
                            source.backup(destination)
                        archive.write(copy,name);copy.unlink()
                    elif path.name.endswith(('-wal','-shm')):continue
                    else:archive.write(path,name)
            archive.writestr('BACKUP_INFO.json',json.dumps({'version':self.current_version,'architecture':self.architecture,'created_at':datetime.now(timezone.utc).isoformat()}))
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:raise ValueError('El respaldo local no es íntegro.')
        return target

    def prepare(self, release, roots, *, quiesce):
        if self.busy(): raise RuntimeError('Finaliza la operación en curso y cierra las otras ventanas de Atlantic Gym antes de actualizar.')
        if not self.schema_supported(release.minimum_schema): raise ValueError('El schema requerido necesita una actualización administrada del servidor.')
        self.verify(release,self.path(release))
        stack=ExitStack()
        try:
            stack.enter_context(quiesce())
            if self.busy():raise RuntimeError('Hay una operación en curso.')
            backup=self.backup(roots)
            self.prepared=release
            self.maintenance=stack
            self.journal.value['pending']=dict(version=release.version,architecture=release.architecture,backup=str(backup),installer=str(self.path(release)),sha256=release.sha256)
            self.journal.save()
            return backup
        except Exception:stack.close();raise

    def launch(self):
        if self.prepared is None:raise RuntimeError('Primero verifica y respalda la actualización.')
        release=self.prepared
        try:
            path=self.verify(release,self.path(release))
            self.launcher(path) # Single verified EXE path. No shell or remote arguments.
            # Installation is confirmed only by the next healthy application startup.
        except Exception:
            self.journal.record('UPDATE_FAILED',version=release.version,reason='installer_handoff')
            self.cancel()
            raise

    def cancel(self):
        if self.maintenance:self.maintenance.close()
        self.maintenance=None;self.prepared=None

    def confirm_started(self, *, healthy):
        pending=self.journal.value.get('pending')
        if healthy and pending and pending['version']==self.current_version and pending['architecture']==self.architecture:
            self.journal.value['last_known_good']=self.current_version
            self.journal.value['pending']=None
            self.journal.record('UPDATE_INSTALLED',version=self.current_version)
        elif healthy and not pending:
            self.journal.value['last_known_good']=self.current_version
            self.journal.save()

    @staticmethod
    def _launch_windows(path):
        if sys.platform!='win32':raise OSError('La instalación requiere Windows.')
        subprocess.Popen([str(path)],shell=False,close_fds=True)
