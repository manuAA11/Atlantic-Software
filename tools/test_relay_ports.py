"""Missing USB metadata, present-device fallback and no discovery transmission."""
import ctypes
from pathlib import Path
import struct
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from serial.tools.list_ports_common import ListPortInfo
from common import relay_ports
from common.door_access import DoorConfig, open_relay


def port(name='COM4', vid=None, pid=None, hwid='n/a'):
    value = ListPortInfo(name)
    value.vid, value.pid, value.hwid = vid, pid, hwid
    value.description = 'USB Serial'
    return value


def native(name='COM4', pid=0x7523):
    return dict(port=name, vid=0x1A86, pid=pid, description='CH340', serial_number='', location='')


class Discovery(unittest.TestCase):
    def discover(self, primary, fallback=()):
        with patch('serial.tools.list_ports.comports', return_value=primary), \
             patch.object(relay_ports, 'sys', NS(platform='win32')), \
             patch.object(relay_ports, '_windows_ports', return_value=list(fallback)), \
             patch('serial.Serial', side_effect=AssertionError('Discovery must never open a COM')):
            return relay_ports.available_ports()

    def test_com4_with_incomplete_metadata_uses_present_hardware_identity(self):
        found = self.discover([port()], [native()])
        self.assertEqual(len(found), 1)
        self.assertTrue(relay_ports.is_relay_port(found[0]))
        self.assertEqual(found[0]['port'], 'COM4')

    def test_numeric_hardware_id_recovers_ids_without_native_lookup(self):
        for hwid in ('USB VID:PID=1A86:7523 SER=synthetic', r'usb\vid_1a86&pid_7523\synthetic'):
            with self.subTest(hwid=hwid), patch.object(relay_ports, '_windows_ports') as lookup:
                with patch('serial.tools.list_ports.comports', return_value=[port(hwid=hwid)]), \
                     patch.object(relay_ports, 'sys', NS(platform='win32')):
                    self.assertTrue(relay_ports.is_relay_port(relay_ports.available_ports()[0]))
                lookup.assert_not_called()

    def test_friendly_name_alone_never_identifies_a_relay(self):
        device = port()
        device.description = 'CH340 LCUS-1 relay COM4'
        self.assertFalse(relay_ports.is_relay_port(self.discover([device])[0]))

    def test_known_other_usb_device_is_not_reclassified(self):
        found = self.discover([port(vid=0x0403, pid=0x6001)], [native()])
        self.assertEqual(found[0]['vid'], 0x0403)
        self.assertFalse(relay_ports.is_relay_port(found[0]))

    def test_partial_conflicting_identity_and_ambiguous_native_com_are_rejected(self):
        for device, fallback in ((port(vid=0x0403), [native()]),
                                 (port(), [native(), native(pid=0x5523)])):
            self.assertFalse(relay_ports.is_relay_port(self.discover([device], fallback)[0]))

    def test_other_device_ids_hidden_in_hwid_do_not_override_explicit_ids(self):
        device = port(vid=0x0403, pid=0x6001, hwid='USB VID:PID=1A86:7523')
        self.assertFalse(relay_ports.is_relay_port(self.discover([device])[0]))

    def test_native_present_com_survives_missing_primary_entry(self):
        self.assertEqual(self.discover([], [native()]), [native()])

    def test_primary_oserror_can_recover_from_native_present_devices(self):
        with patch('serial.tools.list_ports.comports', side_effect=OSError()), \
             patch.object(relay_ports, 'sys', NS(platform='win32')), \
             patch.object(relay_ports, '_windows_ports', return_value=[native()]):
            self.assertEqual(relay_ports.available_ports(), [native()])

    def test_known_serial_number_and_location_are_preserved(self):
        device = port()
        device.serial_number, device.location = 'synthetic', 'USB-A'
        found = self.discover([device], [native()])[0]
        self.assertEqual((found['serial_number'], found['location']), ('synthetic', 'USB-A'))

    def test_rest_and_pulse_open_path_uses_the_same_recovered_identity(self):
        with patch('serial.tools.list_ports.comports', return_value=[port()]), \
             patch.object(relay_ports, 'sys', NS(platform='win32')), \
             patch.object(relay_ports, '_windows_ports', return_value=[native()]), \
             patch('serial.Serial') as serial:
            connection = open_relay(DoorConfig(enabled=True, port='COM4', vid=0x1A86, pid=0x7523))
            self.assertIs(connection, serial.return_value)
            serial.assert_called_once()
            self.assertEqual(serial.call_args.kwargs['port'], 'COM4')
            self.assertEqual(serial.call_args.kwargs['baudrate'], 9600)
            connection.write.assert_not_called()


class NativeDiscovery(unittest.TestCase):
    def test_native_lookup_uses_present_devices_and_closes_all_handles(self):
        class Device(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint32)]
        class Guid(ctypes.Structure):
            _fields_ = [('value', ctypes.c_uint32)]
        api = NS(GUID=Guid, DWORD=ctypes.c_uint32, SP_DEVINFO_DATA=Device,
                 DIGCF_PRESENT=2, SPDRP_HARDWAREID=1, DICS_FLAG_GLOBAL=1,
                 DIREG_DEV=1, KEY_READ=0x20019)
        def guids(name, values, size, count):
            self.assertEqual(size, 8)
            count._obj.value = 1
            return True
        def property_value(handle, device, kind, unused, buffer, size, needed):
            text = 'ROOT\\GENERIC\0USB\\VID_1A86&PID_7523\0\0'
            for i, char in enumerate(text):
                buffer._obj[i] = char
            return True
        def query(key, name, unused, kind, buffer, length):
            buffer._obj.value = 'COM4'
            return 0
        api.SetupDiClassGuidsFromName = guids
        api.SetupDiGetClassDevs = Mock(return_value=123)
        api.SetupDiEnumDeviceInfo = Mock(side_effect=[True, False])
        api.SetupDiGetDeviceRegistryProperty = property_value
        api.SetupDiOpenDevRegKey = Mock(return_value=456)
        api.RegQueryValueEx = query
        api.RegCloseKey, api.SetupDiDestroyDeviceInfoList = Mock(), Mock()
        with patch.dict(sys.modules, {'serial.tools.list_ports_windows': api}), \
             patch('serial.tools.list_ports_windows', api, create=True), \
             patch('serial.Serial', side_effect=AssertionError('No transmission')):
            found = relay_ports._windows_ports()
        self.assertTrue(relay_ports.is_relay_port(found[0]))
        self.assertEqual(api.SetupDiGetClassDevs.call_args.args[-1], 2)
        api.RegCloseKey.assert_called_once_with(456)
        api.SetupDiDestroyDeviceInfoList.assert_called_once_with(123)

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows SetupAPI only')
    def test_actual_native_api_and_pointer_sizes_without_opening_usb(self):
        from serial.tools import list_ports_windows as api
        self.assertEqual(ctypes.sizeof(api.SP_DEVINFO_DATA), 28 if struct.calcsize('P') == 4 else 32)
        with patch('serial.Serial', side_effect=AssertionError('No transmission')):
            self.assertTrue(all(relay_ports.is_relay_port(p) for p in relay_ports._windows_ports()))


if __name__ == '__main__':
    unittest.main()
