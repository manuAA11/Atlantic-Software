"""Stable historical device identity; never regenerated on application update."""
import hashlib
import platform
import uuid

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
