"""One OFF-only reconnection after a completed, failed relay pulse cleanup.

Keep the accepted driver and its ordering/watchdog rules in door_access intact.
This policy never retries an access, ON, authorization or check-in. A recovered
write confirms transmission only; the LCUS-1 does not report contact position.
"""
from __future__ import annotations

from .door_access import DoorController, matches_port, open_relay, relay_failure


class _TrackedConnection:
    """A native close must actually return successfully before reopening."""

    def __init__(self, native):
        self.native = native
        self.close_succeeded = False

    def __getattr__(self, name):
        return getattr(self.native, name)

    def close(self):
        self.native.close()
        self.close_succeeded = True


class RecoveringDoorController(DoorController):
    """Allow one fresh secure cycle, with the existing equipment lock/cleanup.

    Reopening is allowed only after the old handle's real close succeeds,
    when a completed ON cycle failed writing/draining its final OFF. An ON
    failure, canceled/stuck write, failed close, changed identity/configuration,
    shutdown or missing port keeps the fault latched. Each new pulse gets at
    most one reconnection; a permanent error cannot start a retry loop.
    """

    def __init__(self, *args, transport=open_relay, **kwargs):
        self._native_transport = transport
        self._last_connection = None
        self._recovering_off = False
        super().__init__(*args, transport=self._open_tracked, **kwargs)

    def _open_tracked(self, config):
        if self._recovering_off:
            # Validate again immediately before opening, including transports
            # injected by callers. Never follow a changed COM to another USB.
            if not any(matches_port(config, item) for item in self.ports_provider()):
                raise OSError('La identidad USB seleccionada cambió.')
        native = self._native_transport(config)
        if (self._recovering_off and self._last_connection is not None and
                native is self._last_connection.native):
            # A custom factory could have reopened the same Python object.
            # Dispose that handle as well; do not leave an untracked port open.
            native.close()
            raise OSError('La recuperación requiere un puerto nuevo.')
        tracked = _TrackedConnection(native)
        self._last_connection = tracked
        return tracked

    def _current_recovery_config(self, config, generation):
        return (not self.offline and not self._stop.is_set() and config.enabled and
                generation == self._generation and self.store.load() == config)

    def _recover_terminal_off(self, error, config, generation):
        previous = self._last_connection
        details = relay_failure(error, config.port)
        if (previous is None or not previous.close_succeeded or self._session is not None or
                details['stage'] not in ('final_rest_write', 'final_rest_drain') or
                details['error_type'] not in ('SerialException', 'SerialTimeoutException',
                                             'OSError', 'PermissionError', 'TimeoutError')):
            return False
        try:
            if not self._current_recovery_config(config, generation):
                return False
            self._record('relay_off_recovery_start', port=config.port,
                         reason='one_fresh_handle', **details)
            self._status('Restableciendo la comunicación del relé; la apertura no se repite.', 'warning')
            # Interruptible settling time, once per failed pulse, off the UI.
            if self._stop.wait(0.2) or not self._current_recovery_config(config, generation):
                self._record('relay_off_recovery_skipped', port=config.port, reason='configuration_or_shutdown')
                return False
            self._recovering_off = True
            try:
                # Direct call to the unchanged secure path: OFF only, no
                # database write/claim, no pulse timer, no recursive policy.
                # Its nonblocking equipment lock also covers Admin/Reception.
                super()._execute('secure', config, None, self.clock(), generation)
            finally:
                self._recovering_off = False
            current = self._last_connection
            if (current is previous or not current.close_succeeded or self._fault or
                    not self._current_recovery_config(config, generation)):
                self._fault = True
                self._record('relay_off_recovery_skipped', port=config.port, reason='secure_cycle_incomplete')
                return False
            self._record('relay_off_recovery_succeeded', port=config.port,
                         reason='off_only', state='Reposo (OFF enviado)')
            self._status('Comunicación del relé recuperada: OFF enviado. Comprueba la puerta; la apertura no se repitió.')
            return True
        except Exception as recovery_error:
            self._fault = True
            self._record('relay_off_recovery_failed', port=config.port,
                         **relay_failure(recovery_error, config.port), state='Desconocido')
            return False

    def _execute(self, kind, config, payload, created, generation):
        try:
            return super()._execute(kind, config, payload, created, generation)
        except Exception as error:
            if kind in ('access', 'manual', 'test') and self._recover_terminal_off(error, config, generation):
                return None
            raise
