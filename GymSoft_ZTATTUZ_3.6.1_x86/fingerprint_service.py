"""Worker-owned capture, enrollment, cloud verification and automatic check-in."""
import queue
import threading
import time
from digitalpersona_native import NativeReader, BadScan, ReaderBusy, ReaderError
from fingerprint_diagnostics import record


class FingerprintService:
    RELEASE_LIMIT = 3.0
    ENROLLMENT_SECONDS = 150

    def __init__(self, store, register, factory=NativeReader):
        self.store, self.register, self.factory = store, register, factory
        self.commands = queue.Queue(); self.events = queue.Queue()
        self.stop_event = threading.Event(); self.enabled = threading.Event()
        self.enabled.set(); self.lock = threading.Lock(); self.epoch = 0
        self.last = {}; self._status = None; self.cancel_event = threading.Event()
        self.reader = None; self.target = None; self.phase = None; self.pending = None
        self.enrollment_open = False; self.samples = 0; self.deadline = 0
        self.release_at = None; self.templates = {}; self.synced = False
        self.baseline = None
        self.thread = threading.Thread(target=self.run, daemon=True, name='DigitalPersonaReader')

    def start(self): self.thread.start()
    def send(self, kind, value=None):
        if kind == 'cancel': self.cancel_event.set()
        self.commands.put((kind, value))
    def pause(self, paused):
        with self.lock:
            if paused == (not self.enabled.is_set()): return
            self.epoch += 1
            self.enabled.clear() if paused else self.enabled.set()
    def close(self): self.stop_event.set(); self.pause(True)
    def status(self, message):
        if self._status != message:
            self._status = message; self.events.put(('status', message))
    def sync(self):
        self.templates = self.store.load(); self.synced = True
        self.events.put(('templates', list(self.templates)))
    def finish_sdk(self):
        if self.enrollment_open:
            self.enrollment_open = False
            self.reader.enroll_finish()
    def end(self, result, message):
        target = self.target
        try: self.finish_sdk()
        except Exception as error: record('finish_sdk', error)
        self.target = self.phase = self.pending = None
        self.status(message)
        self.events.put(('enrollment_end', {'result':result, 'message':message, 'client_id':target}))
        record('enrollment_' + result)

    def confirmed_save(self, proposed):
        """One write; a lost acknowledgement is resolved by a read, never a retry."""
        changed = [k for k in set(proposed) | set(self.templates) if proposed.get(k) != self.templates.get(k)]
        write_error = None
        if changed:
            try: self.store.save(proposed)
            except Exception as error:
                write_error = error; record('cloud_write', error)
        try:
            actual = self.store.load()
        except Exception as error:
            record('cloud_readback', error)
            self.synced = False
            raise RuntimeError('No se pudo confirmar el guardado en la nube. Revisa la conexión y vuelve a consultar la huella antes de repetir el registro.') from error
        self.templates = actual; self.synced = True
        self.events.put(('templates', list(actual)))
        keys = changed or ([self.target] if self.target is not None else [])
        if any(actual.get(k) != proposed.get(k) for k in keys):
            if write_error: raise write_error
            raise RuntimeError('La base de datos no confirmó la huella esperada. Actualiza y vuelve a registrar la huella.')
        record('cloud_readback_confirmed')

    def command(self, kind, value):
        if kind == 'cancel':
            if self.target is not None: self.end('cancelled', 'Lectura cancelada. Se conserva la huella anterior, si existía.')
        elif kind in ('enroll', 'verify'):
            if self.reader is None or not self.synced:
                self.end('failed', 'El lector todavía no está listo. ' + (self._status or 'Comprueba el controlador y la conexión.'))
                return
            if self.target is not None:
                self.end('cancelled', 'Lectura anterior cancelada.')
            self.sync()
            self.cancel_event.clear(); self.target = int(value); self.samples = 0
            self.baseline = (self.templates.get(self.target), getattr(self.store, 'revisions', {}).get(self.target))
            self.deadline = time.monotonic() + self.ENROLLMENT_SECONDS
            # Never carry a wait left by an earlier, unidentified scan into enrollment.
            self.release_at = None
            if kind == 'enroll':
                self.reader.enroll_start(); self.enrollment_open = True; self.phase = 'capture'
                self.status('Coloca el mismo dedo varias veces. Mantén su yema apoyada hasta que se confirme cada muestra.')
            else:
                if self.target not in self.templates:
                    self.end('failed', 'Este cliente no tiene una huella registrada en la nube.'); return
                self.phase = 'verify_only'
                self.status('Coloca el dedo registrado para comprobarlo. Esta prueba no registra una entrada.')
            record('start_' + kind)
        elif kind == 'delete':
            self.sync()
            proposed = dict(self.templates); proposed.pop(int(value), None)
            self.confirmed_save(proposed)
            self.events.put(('template_deleted', int(value)))
            self.status('Huella eliminada. Se comprobó su eliminación en la nube.')

    def process_sample(self, sample):
        if self.phase == 'capture':
            keys = list(self.templates)
            hits = self.reader.match(sample, list(self.templates.values()))
            if any(keys[h] != self.target for h in hits):
                self.end('failed', 'Esta huella ya pertenece a otro cliente. No se guardó un nuevo registro.'); return
            completed = self.reader.enroll_add(sample); self.samples += 1
            record('sample_accepted')
            if completed is None:
                self.status(f'Muestra {self.samples} aceptada. Retira el dedo y colócalo otra vez. Aún no está guardada.')
            else:
                self.finish_sdk(); self.pending = completed; self.phase = 'verify_new'
                self.deadline = time.monotonic() + 60
                self.status('Muestras completas. Retira el dedo y colócalo una vez más para comprobar la huella antes de guardarla.')
            return
        if self.phase in ('verify_new', 'verify_only'):
            self.sync()  # Recheck another computer's replacements/deletions.
            if self.phase == 'verify_new' and self.baseline != (self.templates.get(self.target), getattr(self.store, 'revisions', {}).get(self.target)):
                self.end('failed', 'La huella cambió en otro equipo durante el registro. Se conservó ese cambio; actualiza antes de continuar.'); return
            template = self.pending if self.phase == 'verify_new' else self.templates.get(self.target)
            if not template:
                self.end('failed', 'La huella ya no está disponible. Actualiza y vuelve a registrarla.'); return
            if self.reader.match(sample, [template]) != [0]:
                self.status('La comprobación no coincide. Retira el dedo y vuelve a colocar el mismo dedo.'); return
            keys = list(self.templates)
            if any(keys[h] != self.target for h in self.reader.match(sample, list(self.templates.values()))):
                self.end('failed', 'La huella coincide con otro cliente. No se modificó el registro.'); return
            if self.cancel_event.is_set() or self.stop_event.is_set(): return
            if self.phase == 'verify_new':
                self.status('Huella comprobada. Guardando y verificando en la nube…')
                proposed = dict(self.templates); proposed[self.target] = template
                self.confirmed_save(proposed)
                self.end('saved', 'Huella registrada y verificada correctamente.\n\nQuedó guardada en la base de datos del gimnasio. Puedes guardar y cerrar el formulario. La comprobación no registra asistencia.')
            else:
                self.end('verified', 'Huella reconocida correctamente. Está guardada en la nube. Esta prueba no registra asistencia.')

    def run(self):
        retry = sync_at = 0; lease = None
        try:
            import sys
            if sys.platform == 'win32':
                lease = ReaderLease()
                while not self.stop_event.is_set() and not lease.acquire():
                    self.status('El lector está activo en otra aplicación. Ciérrala para utilizarlo aquí.')
                    try:
                        kind, value = self.commands.get_nowait()
                        if kind in ('enroll', 'verify'): self.end('failed', self._status)
                    except queue.Empty: pass
                    self.stop_event.wait(.5)
                if self.stop_event.is_set(): return
            while not self.stop_event.is_set():
                try:
                    kind, value = self.commands.get_nowait()
                    if kind == 'retry': retry = sync_at = 0
                    else: self.command(kind, value)
                except queue.Empty: pass
                except Exception as error:
                    record('command', error); self.end('failed', str(error))
                if self.target is None and time.monotonic() >= sync_at:
                    try: self.sync()
                    except Exception as error:
                        self.synced = False; self.status(str(error)); record('cloud_sync', error)
                    sync_at = time.monotonic() + 15
                if not self.synced:
                    self.stop_event.wait(.2); continue
                if self.reader is None:
                    if time.monotonic() < retry: self.stop_event.wait(.15); continue
                    try:
                        self.reader = self.factory(); self.release_at = None
                        model = getattr(self.reader, 'model', None)
                        ready = f'DigitalPersona U.are.U {model} listo. ' if model else 'Lector listo. '
                        self.status(ready + ('Coloca el dedo para registrar la entrada.' if self.templates else
                                    'Todavía no hay huellas registradas; usa Registrar huella en el cliente.'))
                        record('reader_ready')
                    except Exception as error:
                        self.status(str(error)); record('reader_open', error); retry = time.monotonic() + 5
                    continue
                try:
                    if self.target is not None and time.monotonic() > self.deadline:
                        self.end('failed', 'No se completó la lectura a tiempo. No se guardó una nueva huella. Retira el dedo y vuelve a registrar siguiendo cada indicación.')
                    if not self.enabled.is_set() and self.target is None:
                        self.stop_event.wait(.15); continue
                    if self.release_at is not None:
                        # Some drivers retain finger_detected after the finger was
                        # removed. A stale flag must not block capture indefinitely.
                        if self.reader.finger_present():
                            if time.monotonic() - self.release_at < self.RELEASE_LIMIT:
                                self.stop_event.wait(.12); continue
                            if self.target is None:
                                # Keep a held finger from creating a new entry
                                # every cooldown period. Probe the sensor when
                                # its status is stale, but discard repeat images
                                # until it reports absence or capture times out.
                                if self.reader.read() is not None:
                                    self.status('Retira el dedo del lector antes de registrar otra entrada.')
                                    self.stop_event.wait(.12); continue
                        self.release_at = None
                    epoch = self.epoch; sample = self.reader.read()
                    if sample is None:
                        self.stop_event.wait(.03); continue
                    self.release_at = time.monotonic()
                    if self.stop_event.is_set(): break
                    if self.target is not None:
                        if not self.cancel_event.is_set(): self.process_sample(sample)
                        continue
                    if epoch != self.epoch or not self.enabled.is_set(): continue
                    self.sync()
                    keys = list(self.templates); hits = self.reader.match(sample, list(self.templates.values()))
                    if len(hits) != 1:
                        message = 'Huella no reconocida. Regístrala o vuelve a colocar el dedo.' if not hits else 'Lectura ambigua. Vuelve a colocar el dedo.'
                        if self._status != message: self.events.put(('unrecognized', message))
                        self.status(message); continue
                    client = keys[hits[0]]; now = time.monotonic()
                    if now - self.last.get(client, -100) < 10: continue
                    if epoch != self.epoch or not self.enabled.is_set(): continue
                    self.last[client] = now
                    try:
                        result = self.register(client, 'HUELLA BIOMÉTRICA')
                        if not isinstance(result, dict) or result.get('result') not in ('PERMITIDA', 'DENEGADA'):
                            raise ValueError('No se recibió un resultado de entrada válido.')
                        self.events.put(('access', result)); self.status('Entrada comprobada. Retira el dedo.')
                        record('checkin_response')
                    except Exception as error:
                        record('checkin_uncertain', error); self.pause(True)
                        self.events.put(('uncertain', 'No se pudo confirmar la entrada. Revisa el historial antes de reactivar la lectura.'))
                except ReaderBusy as error:
                    self.status(str(error)); self.stop_event.wait(.2)
                except BadScan as error:
                    self.status(str(error)); self.release_at = time.monotonic(); record('capture_quality', error)
                except Exception as error:
                    record('capture_or_enrollment', error)
                    if self.target is not None: self.end('failed', str(error))
                    # A cloud failure is not a USB disconnection. Reopen only a
                    # reader that reports a native failure; never repeat a write.
                    if isinstance(error, ReaderError):
                        try: self.reader.close()
                        except Exception: pass
                        self.reader = None; retry = time.monotonic() + 3
                    self.status(str(error)); self.stop_event.wait(.2)
        except Exception as error:
            record('worker', error)
            if self.target is not None: self.end('failed', 'No se pudo completar la lectura. Cierra y vuelve a abrir la aplicación.')
            self.status('No se pudo iniciar el lector. Cierra y vuelve a abrir la aplicación.')
        finally:
            if self.reader:
                try: self.finish_sdk()
                except Exception: pass
                self.reader.close()
            if lease: lease.close()


class ReaderLease:
    """One capturer across Admin, Reception and both product editions per session."""
    def __init__(self):
        import ctypes as C
        self.C = C; self.api = C.WinDLL('kernel32',use_last_error=True)
        self.api.CreateMutexW.argtypes = [C.c_void_p,C.c_int,C.c_wchar_p]
        self.api.CreateMutexW.restype = C.c_void_p
        self.api.WaitForSingleObject.argtypes = [C.c_void_p,C.c_uint32]
        self.api.WaitForSingleObject.restype = C.c_uint32
        self.api.ReleaseMutex.argtypes = [C.c_void_p]
        self.api.CloseHandle.argtypes = [C.c_void_p]
        # Keep the legacy name so older releases cannot capture the same reader
        # concurrently with this release (including the 5160).
        self.handle = self.api.CreateMutexW(None,0,'Local\\GymSoftDigitalPersona4500')
        if not self.handle: raise RuntimeError('No se pudo reservar el lector.')
        self.owned = False
    def acquire(self):
        code = self.api.WaitForSingleObject(self.handle,0)
        self.owned = code in (0,0x80)
        if code == 0xffffffff: raise RuntimeError('No se pudo reservar el lector.')
        return self.owned
    def close(self):
        if self.owned: self.api.ReleaseMutex(self.handle)
        self.api.CloseHandle(self.handle)
