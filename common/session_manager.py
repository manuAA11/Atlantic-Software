"""Single owner of rotating Supabase sessions; no UI or hardware dependencies.

Only explicit authentication rejection may replay an API request. Transport errors
never replay writes. Realtime receives access tokens, never refresh tokens.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time


class SessionUnavailable(RuntimeError):
    pass


class SessionOffline(ConnectionError):
    pass


class SessionClockError(RuntimeError):
    pass


class MemorySessionStore:
    """Non-Windows fallback: intentionally never persists credentials in plaintext."""
    def __init__(self):
        self.value = None
        self.lock = threading.RLock()

    def load(self):
        return self.value

    def save(self, value):
        self.value = value

    def clear(self):
        self.value = None

    @contextmanager
    def transaction(self):
        with self.lock:
            yield


class WindowsSessionStore:
    """Current Windows user DPAPI, atomic writes, interprocess refresh exclusion.

    Namespace must distinguish provider and application role, but stays stable
    across upgrades. No machine-wide decryption or unencrypted fallback.
    """
    def __init__(self, namespace, directory=None):
        key = hashlib.sha256(namespace.encode()).hexdigest()
        self.directory = Path(directory or Path(os.environ['LOCALAPPDATA'])/'GymControl'/'sessions')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory/(key+'.dpapi')
        self.lock_path = self.directory/(key+'.lock')
        self.entropy = ('AtlanticGym/session/v1/'+namespace).encode()

    def _crypt(self, value, decrypt=False):
        if sys.platform != 'win32':
            raise OSError('DPAPI requires Windows.')
        class Blob(C.Structure):
            _fields_ = [('size', W.DWORD), ('data', C.POINTER(C.c_ubyte))]
        def blob(data):
            buffer = (C.c_ubyte*len(data)).from_buffer_copy(data)
            return Blob(len(data), buffer), buffer
        source, source_buffer = blob(value)
        entropy, entropy_buffer = blob(self.entropy)
        target = Blob()
        crypt = C.WinDLL('crypt32', use_last_error=True)
        kernel = C.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [C.c_void_p]
        kernel.LocalFree.restype = C.c_void_p
        if decrypt:
            operation = crypt.CryptUnprotectData
            operation.argtypes = [C.POINTER(Blob), C.c_void_p, C.POINTER(Blob), C.c_void_p, C.c_void_p, W.DWORD, C.POINTER(Blob)]
            args = (C.byref(source), None, C.byref(entropy), None, None, 1, C.byref(target))
        else:
            operation = crypt.CryptProtectData
            operation.argtypes = [C.POINTER(Blob), W.LPCWSTR, C.POINTER(Blob), C.c_void_p, C.c_void_p, W.DWORD, C.POINTER(Blob)]
            args = (C.byref(source), 'Atlantic Gym session', C.byref(entropy), None, None, 1, C.byref(target))
        operation.restype = W.BOOL
        if not operation(*args):
            raise C.WinError(C.get_last_error())
        try:
            return C.string_at(target.data, target.size)
        finally:
            kernel.LocalFree(C.cast(target.data, C.c_void_p))

    def load(self):
        if not self.path.exists():
            return None
        return json.loads(self._crypt(self.path.read_bytes(), decrypt=True))

    def save(self, value):
        encrypted = self._crypt(json.dumps(value, separators=(',', ':')).encode())
        fd, temporary = tempfile.mkstemp(dir=self.directory, prefix='.session-')
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(encrypted)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def clear(self):
        self.path.unlink(missing_ok=True)

    @contextmanager
    def transaction(self):
        import msvcrt
        with self.lock_path.open('a+b') as lock:
            if lock.seek(0, 2) == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            # Bounded Windows lock acquisition; failure does not log out a user.
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def default_store(namespace):
    return WindowsSessionStore(namespace) if sys.platform == 'win32' else MemorySessionStore()


def revoked(error):
    return str(getattr(error, 'code', '')) in {
        'refresh_token_not_found', 'refresh_token_already_used', 'session_not_found',
        'session_expired', 'user_banned', 'user_not_found', 'invalid_refresh_token',
    }


class SessionManager:
    def __init__(self, client, store, *, clock=time.time, monotonic=time.monotonic, wait=time.sleep):
        self.client, self.auth, self.store = client, client.auth, store
        self.clock, self.monotonic = clock, monotonic
        self.wait = wait
        self.lock = threading.RLock()
        self.session = None
        self.state = 'SIGNED_OUT'
        self.retry_at = 0.
        self.failures = 0
        self.last_tick = clock()
        self.stop_event = threading.Event()
        self.worker = None
        self.persistence_error = False
        self.local = threading.local()
        self.requests = threading.Condition()
        self.active_requests = 0
        self.maintenance = False
        self.auth.on_auth_state_change(self._changed)
        # SDK methods such as sign_out/get_user also use the serialized owner.
        self.auth.get_session = self.ensure

    @contextmanager
    def request(self):
        with self.requests:
            if self.maintenance:
                raise RuntimeError('Se está preparando una actualización. Espera su resultado.')
            self.active_requests += 1
        try:
            yield
        finally:
            with self.requests:
                self.active_requests -= 1
                self.requests.notify_all()

    @contextmanager
    def quiesce(self, timeout=30):
        with self.requests:
            if self.maintenance:
                raise RuntimeError('Ya hay una actualización en preparación.')
            self.maintenance = True
            if not self.requests.wait_for(lambda: self.active_requests == 0, timeout):
                self.maintenance = False
                raise TimeoutError('Hay operaciones pendientes; la aplicación permanecerá abierta.')
        try:
            yield
        finally:
            with self.requests:
                self.maintenance = False
                self.requests.notify_all()

    @contextmanager
    def _guard(self):
        with self.lock:
            if getattr(self.local, 'active', False):
                yield
            else:
                with self.store.transaction():
                    self.local.active = True
                    try:
                        yield
                    finally:
                        self.local.active = False

    def _changed(self, event, session):
        # Invoked synchronously within a serialized auth operation. Never log tokens.
        if event in {'SIGNED_IN', 'TOKEN_REFRESHED'} and session:
            self.session = session
            self.state = 'ONLINE'
            self.retry_at = 0.
            self.failures = 0
            try:
                self.store.save(session.model_dump(mode='json'))
                self.persistence_error = False
            except OSError:
                # Keep the newly rotated token in memory; never reload its old parent.
                self.persistence_error = True
        elif event == 'SIGNED_OUT':
            self.session = None
            self.store.clear()
            self.state = 'SIGNED_OUT'

    def _bind_session(self, session):
        """Apply a peer's rotated credential to every pinned SDK transport.

        Updating PostgREST alone leaves cached Edge/Storage clients and Auth
        headers on the previous access token. Use the same SDK binding callback
        as a normal TOKEN_REFRESHED event, without rotating or emitting events.
        """
        token = session.access_token if session else self.client.supabase_key
        header = 'Bearer '+token
        if self.client.options.headers.get('Authorization') != header:
            bind = getattr(self.client, '_listen_to_auth_events', None)
            if callable(bind):
                bind('TOKEN_REFRESHED' if session else 'SIGNED_OUT', session)
            self.client.options.headers['Authorization'] = header
            auth_headers = getattr(self.auth, '_headers', None)
            if isinstance(auth_headers, dict):
                auth_headers['Authorization'] = header
        self.client.postgrest.auth(token)

    def _load(self):
        from supabase_auth.types import Session
        if self.persistence_error and self.session:
            self.store.save(self.session.model_dump(mode='json'))
            self.persistence_error = False
            return self.session
        value = self.store.load()
        if value:
            previous = self.session.access_token if self.session else None
            self.session = Session.model_validate(value)
            if self.session.access_token != previous:
                self.state = 'ONLINE'
                self.retry_at = 0.
                self.failures = 0
        else:
            self.session = None
            if self.state != 'AUTH_REQUIRED':
                self.state = 'SIGNED_OUT'
        self._bind_session(self.session)
        return self.session

    def restore(self):
        with self._guard():
            return self._load()

    def ensure(self, *, force=False, rejected_token=None):
        with self._guard():
            # A second process may already have rotated the same stored session.
            self._load()
            session = self.session
            if not session:
                if self.state != 'AUTH_REQUIRED':
                    self.state = 'SIGNED_OUT'
                return None
            if rejected_token and session.access_token != rejected_token:
                return session
            if not force and (session.expires_at or 0) > self.clock()+90:
                return session
            if self.monotonic() < self.retry_at:
                raise SessionOffline('Sin conexión de sesión. Se reintentará automáticamente.')
            self.state = 'RECOVERING'
            try:
                response = self.auth.refresh_session(session.refresh_token)
                if not response.session:
                    raise SessionUnavailable('La sesión necesita autenticación.')
                # The pinned SDK normally emits TOKEN_REFRESHED. An adapter
                # without that callback must still persist and bind the result.
                if self.session is not response.session:
                    self._changed('TOKEN_REFRESHED', response.session)
                self._bind_session(response.session)
                self.state = 'ONLINE'
                self.failures = 0
                self.retry_at = 0.
                return self.session
            except Exception as error:
                if revoked(error) or isinstance(error, SessionUnavailable):
                    self.session = None
                    self.store.clear()
                    self.state = 'AUTH_REQUIRED'
                    raise SessionUnavailable('La sesión fue revocada. Inicia sesión de nuevo.') from None
                self.failures += 1
                self.retry_at = self.monotonic()+min(60., 2.**min(self.failures, 6))
                self.state = 'OFFLINE'
                raise SessionOffline('No se pudo recuperar la conexión. La sesión se conserva.') from None

    def operation(self, name, *args, **kwargs):
        with self._guard():
            return getattr(self.auth, name)(*args, **kwargs)

    def logout(self):
        with self._guard():
            try:
                self.auth.sign_out({'scope': 'local'})
            finally:
                self.session = None
                self.store.clear()
                self.state = 'SIGNED_OUT'
                self.close()
                self._bind_session(None)

    def tick(self):
        now = self.clock()
        resumed = now-self.last_tick > 90 or now < self.last_tick-10
        self.last_tick = now
        if resumed:
            self.retry_at = 0.
        return self.ensure()

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        def run():
            while not self.stop_event.wait(10):
                try:
                    self.tick()
                except Exception:
                    # UI reads state. No tokens or server error payloads in logs.
                    pass
        self.worker = threading.Thread(target=run, name='Atlantic-Session', daemon=True)
        self.worker.start()

    def close(self):
        self.stop_event.set()


class AuthFacade:
    def __init__(self, manager):
        self.manager = manager

    def get_session(self):
        return self.manager.ensure()

    def get_user(self, jwt=None):
        session = self.manager.ensure()
        if not jwt and session:
            jwt = session.access_token
        return self.manager.operation('get_user', jwt)

    def sign_out(self, *args, **kwargs):
        return self.manager.logout()

    def refresh_session(self, *args, **kwargs):
        return self.manager.ensure(force=True)

    def __getattr__(self, name):
        value = getattr(self.manager.auth, name)
        if callable(value):
            return lambda *args, **kwargs: self.manager.operation(name, *args, **kwargs)
        return value


class DeferredQuery:
    """Build queries after recovery, because SDK replaces PostgREST on refresh."""
    def __init__(self, client, steps):
        self.client, self.steps = client, steps

    def __getattr__(self, name):
        return lambda *args, **kwargs: DeferredQuery(self.client, self.steps+[(name, args, kwargs)])

    def _execute(self):
        query = self.client.raw
        for name, args, kwargs in self.steps:
            query = getattr(query, name)(*args, **kwargs)
        return query.execute()

    def execute(self):
        with self.client.session_manager.request():
            return self._execute_authorized()

    def _execute_authorized(self):
        manager = self.client.session_manager
        if self.client.core_control is not None:
            self.client.core_control.require_operation()
        session = manager.ensure()
        token = session.access_token if session else None
        refreshed = False
        future_attempt = 0
        delays = (1., 2., 3.)
        while True:
            try:
                return self._execute()
            except Exception as error:
                # PostgREST rejects JWT before executing SQL. Never retry generic
                # 401, transport errors, timeouts or an ambiguous write.
                if not token or str(getattr(error, 'code', '')) not in {'PGRST301', 'PGRST303'}:
                    raise
                message = str(getattr(error, 'message', error)).casefold()
                if 'jwt issued at future' in message or 'jwt not yet valid' in message:
                    # A fresh token needs time, not another rotation. This runs
                    # in the existing IO worker and never bypasses server checks.
                    if future_attempt == len(delays):
                        raise SessionClockError(
                            'El servidor todavía no pudo validar la sesión. '
                            'Espera unos segundos y vuelve a intentarlo.') from None
                    manager.wait(delays[future_attempt])
                    future_attempt += 1
                    continue
                if refreshed:
                    raise
                session = manager.ensure(force=True, rejected_token=token)
                token = session.access_token if session else None
                refreshed = True


class ManagedFunctions:
    def __init__(self, client):
        self.client=client

    def invoke(self, *args, **kwargs):
        with self.client.session_manager.request():
            if self.client.core_control is not None:
                self.client.core_control.require_operation()
            self.client.session_manager.ensure()
            # No replay: an Edge write may have succeeded before a lost response.
            return self.client.raw.functions.invoke(*args, **kwargs)


class ManagedClient:
    def __init__(self, raw, manager):
        self.raw, self.session_manager = raw, manager
        self.core_control = None
        self.auth = AuthFacade(manager)

    @property
    def functions(self):
        return ManagedFunctions(self)

    def table(self, *args, **kwargs):
        return DeferredQuery(self, [('table', args, kwargs)])

    def rpc(self, *args, **kwargs):
        return DeferredQuery(self, [('rpc', args, kwargs)])

    def __getattr__(self, name):
        return getattr(self.raw, name)


def managed_client(url, key, namespace, *, create_client=None, store=None):
    from supabase import ClientOptions
    if create_client is None:
        from supabase import create_client
    raw = create_client(url, key, options=ClientOptions(auto_refresh_token=False, persist_session=False))
    manager = SessionManager(raw, store if store is not None else default_store(namespace))
    client = ManagedClient(raw, manager)
    # Raw SDK callback references raw.auth, not the facade, preserving its headers.
    return client
