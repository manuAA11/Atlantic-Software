from __future__ import annotations
import hashlib
import platform
import queue
import threading
import uuid
from desktop_ui import messagebox
from typing import Any

from device_identity import device_identifier
from common.deployment_profile import PROFILE

def check_license(cloud: Any) -> dict[str, Any]:
    if PROFILE.license_rpc is None:
        # Existing provider has no commercial license RPC. Core is the licensing
        # authority and enforces explicit suspension in ManagedClient operations.
        control = getattr(cloud.client, 'core_control', None)
        if control is not None:
            control.require_operation()
        return {'allowed': True, 'authority': 'core'}
    result = cloud.client.rpc(PROFILE.license_rpc, {
        'p_device_hash': device_identifier(), 'p_device_name': platform.node() or 'Computador',
    }).execute().data
    if not isinstance(result, dict) or not isinstance(result.get('allowed'), bool):
        raise ValueError('Respuesta de licencia inválida.')
    cloud.license_status = result
    return result

def start_license_monitor(window: Any, cloud: Any) -> None:
    """Revisa cada 45 s sin cerrar por una interrupción temporal de red.

    Una respuesta explícita del servidor que deniega la licencia sigue
    cerrando el programa. Un error de transporte, en cambio, se marca como
    transitorio, se avisa una sola vez y se vuelve a intentar automáticamente.
    """
    if PROFILE.license_rpc is None:
        return  # Common Core heartbeat already monitors this provider.
    results: queue.Queue[Any] = queue.Queue()
    def worker() -> None:
        try:
            results.put(check_license(cloud))
        except Exception as error:
            results.put({
                'allowed': None,
                'transient_error': True,
                'message': 'No se pudo verificar la suscripción en este momento. '
                           'Gym soft permanecerá abierto y volverá a intentarlo '
                           'automáticamente cuando la conexión esté disponible.',
                'detail': str(error),
            })
    def collect() -> None:
        if not window.winfo_exists():
            return
        if getattr(window, '_foreground_io', False):
            # Entregar primero el resultado del pago en curso. La denegación
            # se conserva en la cola y se aplica en cuanto termine la espera.
            window.after(250, collect)
            return
        try:
            result = results.get_nowait()
        except queue.Empty:
            window.after(250, collect)
            return
        if result.get('transient_error'):
            # Una caída breve de Wi‑Fi o del servicio no debe expulsar al
            # personal ni perder una pantalla abierta. No repetimos el aviso
            # cada 45 segundos; las operaciones individuales siguen mostrando
            # su propio estado si necesitan conexión.
            if not getattr(window, '_license_network_notice', False):
                messagebox.showwarning(
                    'Conexión temporal no disponible',
                    result.get('message', 'No se pudo verificar la suscripción ahora.'),
                    parent=window,
                )
                window._license_network_notice = True
            window.after(45000, launch)
            return
        window._license_network_notice = False
        if result.get('allowed') is not True:
            messagebox.showerror('Acceso a Gym soft', result.get('message', 'Acceso no disponible.'), parent=window)
            window.close_app()
            return
        window.after(45000, launch)
    def launch() -> None:
        threading.Thread(target=worker, daemon=True, name='GymSoft-License').start()
        window.after(250, collect)
    window.after(45000, launch)
