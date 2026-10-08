from __future__ import annotations
import hashlib
import platform
import queue
import threading
import uuid
from desktop_ui import messagebox
from typing import Any

def device_identifier() -> str:
    if platform.system() == 'Windows':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                raw = str(winreg.QueryValueEx(key, 'MachineGuid')[0])
        except OSError:
            raw = f'{uuid.getnode()}|{platform.node()}'
    else:
        raw = f'{uuid.getnode()}|{platform.node()}|{platform.system()}'
    return hashlib.sha256(('gymsoft-v3|' + raw).encode()).hexdigest()

def check_license(cloud: Any) -> dict[str, Any]:
    result = cloud.client.rpc('commercial_check_license', {
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
