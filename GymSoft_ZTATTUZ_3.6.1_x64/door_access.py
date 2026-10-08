"""ZTATTUZ: pulsos LCUS-1 después de una entrada biométrica confirmada.

No contiene llamadas Tk ni consultas de autorización alternativas. Un fallo
USB nunca repite el registro en nube. Ninguna prueba necesita un relé real.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import sqlite3
import sys
import threading
import time
from uuid import uuid4

RELAY_ON = bytes.fromhex('A0 01 01 A2')
RELAY_OFF = bytes.fromhex('A0 01 00 A1')
BIOMETRIC_METHOD = 'HUELLA BIOMÉTRICA'


@dataclass(frozen=True)
class DoorConfig:
    enabled: bool = False
    port: str = ''
    seconds: float = 3.0
    vid: int | None = None
    pid: int | None = None
    serial_number: str = ''
    location: str = ''

    def validate(self):
        if type(self.enabled) is not bool:
            raise ValueError('El estado del relé no es válido.')
        if not isinstance(self.seconds, (int, float)) or not math.isfinite(self.seconds) or not 1 <= self.seconds <= 10:
            raise ValueError('La apertura debe durar entre 1 y 10 segundos.')
        if self.enabled and (not re.fullmatch(r'COM[1-9][0-9]{0,3}', self.port) or
                             self.vid != 0x1A86 or self.pid not in (0x7523, 0x5523)):
            raise ValueError('Selecciona el puerto CH340 del LCUS-1 conectado a este computador.')
        return self


class ConfigStore:
    def __init__(self, folder, gym_id):
        self.folder = Path(folder)
        self.gym_id = str(gym_id)
        scope = hashlib.sha256(self.gym_id.encode()).hexdigest()[:20]
        self.path = self.folder / ('puerta_' + scope + '.json')

    def load(self):
        if not self.path.exists():
            return DoorConfig()
        value = json.loads(self.path.read_text(encoding='utf-8'))
        if value.get('gym_id') != self.gym_id or value.get('schema') != 1:
            raise ValueError('La configuración de puerta no corresponde a este gimnasio.')
        return DoorConfig(**value['config']).validate()

    def save(self, config):
        config.validate()
        self.folder.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.' + uuid4().hex + '.tmp')
        try:
            temp.write_text(json.dumps({'schema': 1, 'gym_id': self.gym_id,
                'config': asdict(config)}, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)


def available_ports():
    from serial.tools import list_ports
    return [dict(port=p.device, description=p.description or 'Puerto USB',
                 vid=p.vid, pid=p.pid, serial_number=p.serial_number or '', location=p.location or '')
            for p in list_ports.comports()]


def matches_port(config, item):
    return (item.get('port') == config.port and item.get('vid') == config.vid and
            item.get('pid') == config.pid and
            all(not getattr(config, field) or item.get(field) == getattr(config, field)
                for field in ('serial_number', 'location')))


def open_relay(config):
    # Importar pySerial no abre puertos; nunca se usa serial_for_url ni se
    # envían comandos a dispositivos descubiertos sin selección explícita.
    import serial
    if not any(matches_port(config, item) for item in available_ports()):
        raise OSError('El puerto seleccionado no corresponde al LCUS-1 conectado.')
    return serial.Serial(port=config.port, baudrate=9600, bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         timeout=0.2, write_timeout=0.35, xonxoff=False,
                         rtscts=False, dsrdtr=False)


class RelayBusy(Exception):
    pass


@contextmanager
def equipment_lock(folder, port):
    """Exclusión entre Administración y Recepción, incluso para restablecer."""
    path = Path(folder) / ('rele_' + hashlib.sha256(port.encode()).hexdigest()[:16] + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as file:
        file.seek(0, 2)
        if file.tell() == 0:
            file.write(b'0'); file.flush()
        file.seek(0)
        try:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RelayBusy() from error
        try:
            yield
        finally:
            file.seek(0)
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


class DoorController:
    """Una sola orden en curso. Sin colas de aperturas ni reintentos tardíos."""
    def __init__(self, store, *, transport=open_relay, offline=False, clock=time.monotonic):
        self.store, self.transport, self.clock = store, transport, clock
        self.offline = offline
        self.events = queue.Queue(maxsize=32)
        self._commands = queue.Queue(maxsize=1)
        self._guard = threading.Lock()
        self._stop = threading.Event()
        self._cancel = threading.Event()
        self._pending = False
        self._fault = False
        self._generation = 0
        self._thread = threading.Thread(target=self._work, name='ZTATTUZ-LCUS1', daemon=True)
        self._thread.start()
        if offline:
            self._status('Control de puerta: simulación; USB desactivado.')
        else:
            try:
                if store.load().enabled:
                    self.secure()
                else:
                    self._status('Puerta automática: desactivada.')
            except (OSError, ValueError, TypeError):
                self._status('Puerta desactivada: revisa su configuración.', 'error')

    def _status(self, message, kind='info'):
        while True:
            try:
                self.events.put_nowait((kind, message)); return
            except queue.Full:
                try: self.events.get_nowait()
                except queue.Empty: pass

    def save_config(self, config):
        config.validate()
        with self._guard:
            if self._pending:
                raise ValueError('Espera a que termine el ciclo del relé antes de cambiar la configuración.')
            self.store.save(config)
            self._generation += 1
        if config.enabled:
            self.secure()
        else:
            self._status('Puerta automática: desactivada.')

    def _queue(self, kind, config, payload=None):
        with self._guard:
            if self._stop.is_set() or self.offline:
                return False
            if self._pending:
                self._status('Relé ocupado: hay un ciclo en curso. No se acumulan aperturas.', 'warning')
                return False
            self._pending = True
            self._cancel.clear()
            self._commands.put_nowait((kind, config, payload, self.clock(), self._generation))
            return True

    def secure(self):
        """Solo envía OFF. Restablecer nunca abre la puerta."""
        try:
            config = self.store.load()
            if not config.enabled: return False
            return self._queue('secure', config)
        except (ValueError, TypeError, OSError):
            self._status('No se pudo leer la configuración del relé.', 'error'); return False

    def submit(self, result, client_id, method, *, override=False):
        # Se llama inmediatamente después del RPC, en el mismo hilo de I/O.
        # No aceptar resultados construidos por la vista, históricos o manuales.
        if (method != BIOMETRIC_METHOD or override or not isinstance(result, dict) or
                result.get('result') != 'PERMITIDA' or result.get('frozen') or result.get('override')):
            return False
        try:
            if int(result['id']) != int(client_id) or int(client_id) <= 0:
                return False
            stamp = datetime.fromisoformat(result['checkin_at'].replace('Z', '+00:00'))
            if stamp.tzinfo is None: return False
            config = self.store.load()
            if not config.enabled: return False
            if self._fault:
                self._status('Entrada registrada; revisa el relé y pulsa Restablecer. No se envió apertura.', 'error')
                return False
            return self._queue('access', config, (int(client_id), stamp.isoformat()))
        except (KeyError, ValueError, TypeError, OSError):
            self._status('Entrada registrada; no se pudo preparar la apertura. Revisa Puerta / relé.', 'error')
            return False

    def test_pulse(self):
        """Únicamente desde la confirmación explícita del administrador."""
        try:
            config = self.store.load()
            return bool(config.enabled and not self._fault and self._queue('test', config))
        except (ValueError, TypeError, OSError):
            self._status('Revisa la configuración antes de probar el relé.', 'error'); return False

    def manual_pulse(self):
        """Apertura deliberada del personal; no registra ni consume entradas."""
        try:
            config = self.store.load()
            return bool(config.enabled and not self._fault and self._queue('manual', config))
        except (ValueError, TypeError, OSError):
            self._status('Revisa la configuración antes de abrir la puerta.', 'error'); return False

    def _claim(self, client_id, stamp):
        # Compartido por los dos ejecutables del mismo usuario/equipo. Se
        # conserva la marca incluso si falla el USB: nunca repetir la orden.
        self.store.folder.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256((self.store.gym_id + '/' + str(client_id) + '/' + stamp).encode()).hexdigest()
        person = hashlib.sha256((self.store.gym_id + '/' + str(client_id)).encode()).hexdigest()
        # El contexto de SQLite confirma/revierte, pero NO cierra la conexión.
        # closing libera el archivo también al retornar por duplicado o fallar.
        with closing(sqlite3.connect(self.store.folder / 'puerta_eventos.db', timeout=0.3)) as db:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS events (event TEXT PRIMARY KEY, person TEXT, at REAL)')
                db.execute('CREATE INDEX IF NOT EXISTS person_at ON events(person, at)')
                db.execute('CREATE INDEX IF NOT EXISTS event_age ON events(at)')
                db.execute('BEGIN IMMEDIATE')
                now = time.time()
                if db.execute('SELECT 1 FROM events WHERE event=? OR (person=? AND at>?) LIMIT 1',
                              (key, person, now - 10)).fetchone():
                    return False
                db.execute('INSERT INTO events VALUES (?,?,?)', (key, person, now))
                db.execute('DELETE FROM events WHERE at<?', (now - 86400 * 30,))
                return True

    @staticmethod
    def _write(connection, data):
        if connection.write(data) != len(data):
            raise OSError('Escritura incompleta al relé.')
        # No cerrar con el último OFF aún en la cola del controlador. flush()
        # no tiene un plazo propio: aquí se limita explícitamente la espera.
        deadline = time.monotonic() + 0.4
        while connection.out_waiting:
            if time.monotonic() >= deadline:
                raise TimeoutError('El controlador USB no terminó de transmitir.')
            time.sleep(0.005)

    def _execute(self, kind, config, payload, created, generation):
        if self._stop.is_set() or generation != self._generation or self.store.load() != config:
            return
        if self.clock() - created > 2:
            self._status('La orden caducó. No se abrió la puerta con una respuesta retrasada.', 'warning'); return
        with equipment_lock(self.store.folder, config.port):
            if kind == 'access' and not self._claim(*payload):
                self._status('Entrada repetida: no se envió otra apertura.', 'warning'); return
            connection = self.transport(config)
            try:
                # Siempre partir de OFF. No se mantiene abierto el puerto entre
                # accesos, para poder usar Administración o Recepción.
                self._write(connection, RELAY_OFF)
                if kind != 'secure':
                    if (self._stop.is_set() or self._cancel.is_set() or
                            self.clock() - created > 2 or self.store.load() != config):
                        return
                    self._write(connection, RELAY_ON)
                    if kind in ('manual', 'test'):
                        try:
                            with (self.store.folder / 'puerta.log').open('a', encoding='utf-8') as file:
                                file.write(datetime.now().isoformat(timespec='seconds') +
                                           (' APERTURA_MANUAL\n' if kind == 'manual' else 'PRUEBA_APERTURA\n'))
                        except OSError: pass
                    self._status(f'Orden de apertura enviada · {config.seconds:g} s. Espera a que termine el ciclo.', 'opening')
                    self._cancel.wait(config.seconds)
            finally:
                try:
                    self._write(connection, RELAY_OFF)
                finally:
                    connection.close()
            self._fault = False
            self._status('Relé listo: orden OFF enviada. Apertura automática por huella activada.')

    def _work(self):
        while not self._stop.is_set():
            try: command = self._commands.get(timeout=0.2)
            except queue.Empty: continue
            try:
                self._execute(*command)
            except RelayBusy:
                self._status('Otra ventana está usando el relé. No se acumuló una apertura.', 'warning')
            except Exception as error:
                # No registrar documentos, nombres ni plantillas biométricas.
                self._fault = True
                self._status('No se pudo completar la orden USB. Revisa la puerta y el cable; después pulsa Restablecer. '
                             'La asistencia no se repite.', 'error')
                try:
                    self.store.folder.mkdir(parents=True, exist_ok=True)
                    with (self.store.folder / 'puerta.log').open('a', encoding='utf-8') as file:
                        file.write(datetime.now().isoformat(timespec='seconds') + ' ' + type(error).__name__ + '\n')
                except OSError: pass
            finally:
                with self._guard: self._pending = False
                self._commands.task_done()

    def close(self):
        self._stop.set(); self._cancel.set()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=2)


class DoorDatabase:
    """Decora el RPC real; su resultado y los errores de red se conservan."""
    def __init__(self, database, door):
        self.database, self.door = database, door

    def __getattr__(self, name):
        return getattr(self.database, name)

    def register_checkin(self, client_id, method, **kwargs):
        # El código escrito/HID y el botón manual conservan la asistencia, pero
        # no son una identificación del lector DigitalPersona.
        return self.database.register_checkin(client_id, method, **kwargs)

    def register_fingerprint_checkin(self, client_id, method):
        # Exclusivo del callback de FingerprintService tras una coincidencia.
        # La verificación de inscripción no llama a este método.
        result = self.database.register_checkin(client_id, method)
        self.door.submit(result, client_id, method)
        return result
