"""Optional LCUS-1 pulses after a server-confirmed fingerprint/code check-in.

No contiene llamadas Tk ni consultas de autorización alternativas. Un fallo
USB nunca repite el registro en nube. Ninguna prueba necesita un relé real.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
from zoneinfo import ZoneInfo

RELAY_ON = bytes.fromhex('A0 01 01 A2')
RELAY_OFF = bytes.fromhex('A0 01 00 A1')
BIOMETRIC_METHOD = 'HUELLA BIOMÉTRICA'
CODE_METHOD = 'CÓDIGO'
# LCUS-1 coil commands, NOT physical door motion. With COM/NC:
# ON energizes the coil, opens NC and releases the magnet. OFF restores NC.
UNLOCK_NC = RELAY_ON
REST_NC = RELAY_OFF


@dataclass(frozen=True)
class DoorConfig:
    enabled: bool = False
    port: str = ''
    seconds: float = 3.0
    vid: int | None = None
    pid: int | None = None
    serial_number: str = ''
    location: str = ''
    baudrate: int = 9600

    @property
    def automatic_door_enabled(self): return self.enabled

    @property
    def door_unlock_seconds(self): return self.seconds

    def validate(self):
        if type(self.enabled) is not bool:
            raise ValueError('El estado del relé no es válido.')
        if type(self.seconds) not in (int, float) or not math.isfinite(self.seconds) or not 1 <= self.seconds <= 10:
            raise ValueError('La apertura debe durar entre 1 y 10 segundos.')
        if type(self.baudrate) is not int or self.baudrate not in (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200):
            raise ValueError('La velocidad serial no es válida.')
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
        if value.get('gym_id') != self.gym_id or value.get('schema') not in (1, 2):
            raise ValueError('La configuración de puerta no corresponde a este gimnasio.')
        config = dict(value['config'])
        if value['schema'] == 2:
            config['enabled'] = config.pop('automatic_door_enabled')
            config['seconds'] = config.pop('door_unlock_seconds')
        return DoorConfig(**config).validate()

    def save(self, config):
        config.validate()
        self.folder.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.' + uuid4().hex + '.tmp')
        try:
            fields = asdict(config)
            fields['automatic_door_enabled'] = fields.pop('enabled')
            fields['door_unlock_seconds'] = fields.pop('seconds')
            temp.write_text(json.dumps({'schema': 2, 'gym_id': self.gym_id,
                'config': fields}, ensure_ascii=False, indent=2), encoding='utf-8')
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
    config.validate()
    if not config.enabled:
        raise ValueError('La puerta automática está desactivada.')
    if not any(matches_port(config, item) for item in available_ports()):
        raise OSError('El puerto seleccionado no corresponde al LCUS-1 conectado.')
    return serial.Serial(port=config.port, baudrate=config.baudrate, bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                         timeout=0.2, write_timeout=0.35, xonxoff=False,
                         rtscts=False, dsrdtr=False)


class RelayBusy(Exception):
    pass


class PulseSession:
    """Independent OFF deadline, cancelable writes and one terminal OFF attempt.

    A watchdog cannot guarantee physical contacts after USB/power/OS failure.
    The independent exit circuit and installation checks remain essential.
    """
    def __init__(self, controller, connection, config, kind):
        self.controller, self.connection, self.config = controller, connection, config
        self.kind = kind
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.writing = threading.Event()
        self.finished = False
        self.error = None
        self.timer = None

    def write(self, frame):
        if self.finished: raise TimeoutError('El ciclo del relé ya terminó.')
        self.writing.set()
        try: self.controller._write(self.connection, frame)
        finally: self.writing.clear()

    def arm(self):
        self.timer = threading.Timer(self.config.seconds, self.finish, kwargs={'reason': 'watchdog'})
        self.timer.daemon = True
        self.timer.start()

    def finish(self, *, reason='finally'):
        with self.lock:
            first = not self.finished
            self.finished = True
        if not first:
            self.done.wait(1.5)
            return self.done.is_set() and self.error is None
        if self.timer: self.timer.cancel()
        self.controller._cancel.set()
        try:
            if self.writing.is_set():
                cancel = getattr(self.connection, 'cancel_write', None)
                if cancel: cancel()
            self.controller._write(self.connection, REST_NC)
            self.controller._record('relay_rest_sent' if self.kind == 'secure' else 'relay_unlock_end', port=self.config.port, reason=reason,
                                    command=REST_NC.hex(), state='Reposo (OFF enviado)')
        except Exception as error:
            self.error = error
            self.controller._fault = True
            self.controller._record('relay_rest_failed', port=self.config.port,
                                    error=type(error).__name__, state='Desconocido')
            self.controller._status('No se confirmó la orden de reposo. Revisa el relé y la puerta presencialmente.', 'error')
        finally:
            try: self.connection.close()
            except Exception as error:
                self.error = self.error or error
                self.controller._fault = True
            self.done.set()
        return self.error is None


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
    def __init__(self, store, *, transport=open_relay, offline=False, clock=time.monotonic,
                 admin_authorized=False, timezone_name='America/Bogota', ports_provider=available_ports):
        self.store, self.transport, self.clock = store, transport, clock
        self.admin_authorized, self.ports_provider = admin_authorized, ports_provider
        try: self.zone = ZoneInfo(timezone_name)
        except (ValueError, TypeError, KeyError): self.zone = ZoneInfo('America/Bogota')
        self._state_guard = threading.Lock()
        self._log_guard = threading.Lock()
        self._state = dict(connection='Sin comprobar', state='Reposo solicitado', last_command='—', last_error='—')
        self._session = None
        self.offline = offline
        self.events = queue.Queue(maxsize=32)
        self._commands = queue.Queue(maxsize=1)
        self._guard = threading.Lock()
        self._stop = threading.Event()
        self._cancel = threading.Event()
        self._pending = False
        self._fault = False
        self._generation = 0
        self._thread = threading.Thread(target=self._work, name='Atlantic-LCUS1', daemon=True)
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
        if kind == 'error':
            with self._state_guard: self._state['last_error'] = message
        while True:
            try:
                self.events.put_nowait((kind, message)); return
            except queue.Full:
                try: self.events.get_nowait()
                except queue.Empty: pass

    def save_config(self, config):
        if not self.admin_authorized:
            raise PermissionError('Solo Administración/Propietario puede configurar la puerta.')
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
        if (method not in (BIOMETRIC_METHOD, CODE_METHOD) or override or not isinstance(result, dict) or
                result.get('result') != 'PERMITIDA' or result.get('frozen') or result.get('override') or result.get('duplicate_read')):
            return False
        try:
            if int(result['id']) != int(client_id) or int(client_id) <= 0:
                return False
            if not isinstance(result.get('checkin_at'), str): return False
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
        if not self.admin_authorized: return False
        try:
            config = self.store.load()
            return bool(config.enabled and not self._fault and self._queue('test', config))
        except (ValueError, TypeError, OSError):
            self._status('Revisa la configuración antes de probar el relé.', 'error'); return False

    def manual_pulse(self):
        """Apertura deliberada del personal; no registra ni consume entradas."""
        if not self.admin_authorized: return False
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
        if self._fault and kind != 'secure':
            self._status('Relé pendiente de restablecer. No se reenvía una liberación.', 'error')
            return
        if self.clock() - created > 2:
            self._status('La orden caducó. No se abrió la puerta con una respuesta retrasada.', 'warning'); return
        with equipment_lock(self.store.folder, config.port):
            if kind == 'access' and not self._claim(*payload):
                self._status('Entrada repetida: no se envió otra apertura.', 'warning'); return
            connection = self.transport(config)
            session = PulseSession(self, connection, config, kind)
            self._session = session
            with self._state_guard: self._state['connection'] = 'USB conectado; relé sin confirmación física'
            try:
                # Siempre partir de OFF. No se mantiene abierto el puerto entre
                # accesos, para poder usar Administración o Recepción.
                session.write(REST_NC)
                self._record('relay_rest_start', port=config.port, command=REST_NC.hex(), state='Reposo (OFF enviado)')
                if kind != 'secure':
                    if (self._stop.is_set() or self._cancel.is_set() or
                            self.clock() - created > 2 or self.store.load() != config):
                        return
                    session.arm()
                    session.write(UNLOCK_NC)
                    if session.finished: return
                    if kind in ('manual', 'test'):
                        try:
                            with (self.store.folder / 'puerta.log').open('a', encoding='utf-8') as file:
                                file.write(datetime.now().isoformat(timespec='seconds') +
                                           (' APERTURA_MANUAL\n' if kind == 'manual' else 'PRUEBA_APERTURA\n'))
                        except OSError: pass
                    self._record('relay_unlock_start', port=config.port, command=UNLOCK_NC.hex(), state='Liberando (ON enviado)',
                                 member_id=payload[0] if payload else None, reason=kind)
                    self._status(f'Liberar puerta · orden enviada por {config.seconds:g} s.', 'opening')
                    self._cancel.wait(config.seconds)
            finally:
                success = session.finish()
                self._session = None
            if not success: raise OSError('No se completó el retorno del relé a reposo.')
            self._fault = False
            self._status('Relé en reposo: OFF enviado. El contacto y la puerta requieren comprobación física.')

    def snapshot(self):
        config = self.store.load()
        with self._state_guard: value = dict(self._state)
        if not config.enabled:
            value['connection'] = 'Desactivado; no se consulta USB'
            value['state'] = 'Desconocido; comprobar puerta' if self._fault else 'Control automático desactivado'
        return dict(value, port=config.port or 'Sin configurar', seconds=config.seconds, enabled=config.enabled)

    def _record(self, event, **fields):
        # Only whitelisted technical fields; no biometric data, names or tokens.
        allowed = {'port', 'reason', 'command', 'state', 'member_id', 'decision', 'error', 'stage'}
        fields = {key: value for key, value in fields.items() if key in allowed and value is not None}
        with self._state_guard:
            if 'command' in fields: self._state['last_command'] = event + ' · ' + fields['command']
            if 'state' in fields: self._state['state'] = fields['state']
            if 'error' in fields: self._state['last_error'] = str(fields['error'])
        try:
            self.store.folder.mkdir(parents=True, exist_ok=True)
            line = dict(at=datetime.now(timezone.utc).astimezone(self.zone).isoformat(timespec='seconds'),
                        timezone=str(self.zone), event=event, **fields)
            with self._log_guard:
                path = self.store.folder / 'puerta.log'
                if path.exists() and path.stat().st_size > 1024 * 1024:
                    os.replace(path, self.store.folder / 'puerta.log.1')
                with path.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(line, ensure_ascii=False) + '\n')
        except OSError: pass

    def _check_connection(self):
        config = self.store.load()
        if self.offline or not config.enabled: return
        found = any(matches_port(config, item) for item in self.ports_provider())
        with self._state_guard:
            previous = self._state['connection']
            self._state['connection'] = ('Puerto USB presente; comprobar relé' if found else 'Desconectado')
        if not found:
            self._fault = True
            self._cancel.set()
            if previous != 'Desconectado':
                self._record('relay_disconnected', port=config.port, error='USB_DISCONNECTED')
                self._status('Relé USB desconectado. Reconecta y restablece a reposo antes de otra liberación.', 'error')
        elif previous == 'Desconectado':
            self._record('relay_reconnected_requires_rest', port=config.port)

    def _work(self):
        check_at = self.clock() + 2
        while not self._stop.is_set():
            try: command = self._commands.get(timeout=0.2)
            except queue.Empty:
                if self.clock() >= check_at:
                    try: self._check_connection()
                    except (OSError, ValueError, TypeError):
                        self._status('No se pudo comprobar el puerto del relé.', 'error')
                    check_at = self.clock() + 2
                continue
            try:
                self._execute(*command)
            except RelayBusy:
                self._status('Otra ventana está usando el relé. No se acumuló una apertura.', 'warning')
            except Exception as error:
                # No registrar documentos, nombres ni plantillas biométricas.
                self._fault = True
                self._record('relay_error', error=type(error).__name__, stage='serial', state='Desconocido')
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
        session = self._session
        if session: session.finish(reason='shutdown')
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=2)


class DoorDatabase:
    """Decora el RPC real; su resultado y los errores de red se conservan."""
    def __init__(self, database, door):
        self.database, self.door = database, door

    def __getattr__(self, name):
        return getattr(self.database, name)

    def register_checkin(self, client_id, method, **kwargs):
        return self._register(client_id, method, kwargs)

    def register_fingerprint_checkin(self, client_id, method):
        # Exclusivo del callback de FingerprintService tras una coincidencia.
        # La verificación de inscripción no llama a este método.
        return self._register(client_id, method, {})

    def _claim_read(self, client_id):
        # BEFORE the server write: shared by both applications on this PC.
        self.door.store.folder.mkdir(parents=True, exist_ok=True)
        person = hashlib.sha256((self.door.store.gym_id + '/' + str(client_id)).encode()).hexdigest()
        with closing(sqlite3.connect(self.door.store.folder / 'puerta_eventos.db', timeout=.3)) as db:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS reads (person TEXT PRIMARY KEY, at REAL)')
                db.execute('BEGIN IMMEDIATE')
                now = time.time()
                prior = db.execute('SELECT at FROM reads WHERE person=?', (person,)).fetchone()
                if prior and 0 <= now - prior[0] < .75: return False
                db.execute('INSERT OR REPLACE INTO reads VALUES (?,?)', (person, now))
                db.execute('DELETE FROM reads WHERE at<?', (now - 86400,))
                return True

    def _register(self, client_id, method, kwargs):
        automatic = method in (BIOMETRIC_METHOD, CODE_METHOD) and not kwargs.get('override')
        self.door._record('member_identified', member_id=int(client_id), stage='identification')
        if automatic and not self._claim_read(client_id):
            self.door._record('duplicate_read_ignored', member_id=int(client_id))
            return dict(id=int(client_id), result='DUPLICADA', duplicate_read=True)
        try:
            result = self.database.register_checkin(client_id, method, **kwargs)
        except Exception as error:
            self.door._cancel.set()
            self.door._record('backend_error', member_id=int(client_id), error=type(error).__name__, stage='backend')
            raise
        if not isinstance(result, dict) or result.get('result') not in ('PERMITIDA', 'DENEGADA'):
            self.door._cancel.set()
            self.door._record('backend_invalid_response', member_id=int(client_id), stage='backend')
            raise ValueError('El servidor no confirmó el acceso; no se solicitó liberar la puerta.')
        self.door._record('access_decision', member_id=int(client_id), decision=result['result'],
                          reason=result.get('status', ''), stage='membership')
        if automatic: self.door.submit(result, client_id, method)
        return result
