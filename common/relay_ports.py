"""Read-only COM discovery, including incomplete Windows USB metadata.

Discovery never opens a serial connection and never sends relay commands.
Only the existing CH340/CH341 USB identities are eligible for selection.
"""
import re
import sys


def is_relay_port(item):
    return (item.get('vid') == 0x1A86 and item.get('pid') in (0x7523, 0x5523)
            and bool(re.fullmatch(r'COM[1-9][0-9]{0,3}', item.get('port', ''))))


def usb_identity(text):
    """Use numeric hardware IDs, never a friendly name such as 'USB Serial'."""
    if not isinstance(text, str):
        return None
    pairs = re.findall(r'\bVID_([0-9a-f]{4})&PID_([0-9a-f]{4})\b', text, re.I)
    pairs += re.findall(r'\bUSB VID:PID=([0-9a-f]{4}):([0-9a-f]{4})\b', text, re.I)
    identities = {(int(vid, 16), int(pid, 16)) for vid, pid in pairs}
    return next(iter(identities)) if len(identities) == 1 else None


def _port_info(port):
    result = dict(port=str(port.device).upper(), description=port.description or 'Puerto USB',
                  vid=port.vid, pid=port.pid, serial_number=port.serial_number or '',
                  location=port.location or '')
    identity = usb_identity(getattr(port, 'hwid', ''))
    if identity and all(result[key] is None or result[key] == value
                        for key, value in zip(('vid', 'pid'), identity)):
        result['vid'], result['pid'] = identity
    return result


def _windows_ports():
    """Present Ports-class devices only; no stale Enum\\USB registry sweep.

    Reuse the pointer-sized SetupAPI signatures from pinned pySerial 3.5.
    Read HardwareID even when a generic device instance ID hides its VID/PID.
    """
    import ctypes as C
    from serial.tools import list_ports_windows as api

    guids = (api.GUID * 8)()
    count = api.DWORD()
    if not api.SetupDiClassGuidsFromName('Ports', guids, len(guids), C.byref(count)):
        raise OSError('No se pudo consultar la clase de puertos de Windows.')
    if count.value > len(guids):
        raise OSError('El inventario de puertos de Windows no está completo.')

    def property_text(handle, device, name):
        buffer = C.create_unicode_buffer(4096)
        if not api.SetupDiGetDeviceRegistryProperty(handle, C.byref(device), name, None,
                C.byref(buffer), C.sizeof(buffer), None):
            return ''
        return buffer[:].replace('\0', ' ')

    result = []
    for guid in guids[:count.value]:
        handle = api.SetupDiGetClassDevs(C.byref(guid), None, None, api.DIGCF_PRESENT)
        if handle in (None, 0, -1, C.c_void_p(-1).value):
            raise OSError('No se pudo consultar los dispositivos presentes.')
        try:
            for index in range(256):
                device = api.SP_DEVINFO_DATA()
                device.cbSize = C.sizeof(device)
                if not api.SetupDiEnumDeviceInfo(handle, index, C.byref(device)):
                    break
                hardware = property_text(handle, device, api.SPDRP_HARDWAREID)
                identity = usb_identity(hardware)
                if identity is None or identity[0] != 0x1A86 or identity[1] not in (0x7523, 0x5523):
                    continue
                key = api.SetupDiOpenDevRegKey(handle, C.byref(device), api.DICS_FLAG_GLOBAL,
                    0, api.DIREG_DEV, api.KEY_READ)
                if key in (None, 0, -1, C.c_void_p(-1).value):
                    continue
                try:
                    port = C.create_unicode_buffer(256)
                    length = api.DWORD(C.sizeof(port))
                    if api.RegQueryValueEx(key, 'PortName', None, None, C.byref(port), C.byref(length)) != 0:
                        continue
                finally:
                    api.RegCloseKey(key)
                name = port.value.upper()
                if not re.fullmatch(r'COM[1-9][0-9]{0,3}', name):
                    continue
                result.append(dict(port=name, vid=identity[0], pid=identity[1],
                    description='CH340 / CH341 · Windows', serial_number='', location=''))
        finally:
            api.SetupDiDestroyDeviceInfoList(handle)
    return result


def available_ports():
    from serial.tools import list_ports
    error = None
    try:
        ports = [_port_info(port) for port in list_ports.comports()]
    except OSError as failure:
        error, ports = failure, []
    # The native lookup is quick, read-only and needed only for missing metadata.
    if sys.platform == 'win32' and (not any(is_relay_port(p) for p in ports)
                                    or any(p['vid'] is None or p['pid'] is None for p in ports)):
        try:
            native = _windows_ports()
        except OSError:
            if error:
                raise error
        else:
            by_port = {p['port']: p for p in ports}
            identities = {}
            for item in native:
                if is_relay_port(item):
                    identities.setdefault(item['port'], set()).add((item['vid'], item['pid']))
            for item in native:
                if not is_relay_port(item) or len(identities[item['port']]) != 1:
                    continue
                previous = by_port.get(item['port'])
                # Explicit conflicting IDs must never be reclassified as a relay.
                if previous is not None:
                    if any(previous[key] is not None and previous[key] != item[key] for key in ('vid', 'pid')):
                        continue
                    previous['vid'], previous['pid'] = item['vid'], item['pid']
                else:
                    by_port[item['port']] = item
            ports = list(by_port.values())
            error = None
    if error:
        raise error
    return sorted(ports, key=lambda p: p['port'])
