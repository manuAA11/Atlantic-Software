"""Supported devices through the real native adapter; no reader is required."""
import unittest

from digitalpersona_native import NativeReader, NoReader, ReaderError, supported_reader_model
from fake_digitalpersona import FakeSDK

T = b'FMR\0' + b'synthetic-sample' * 4


class ReaderModelTests(unittest.TestCase):
    def test_supported_descriptors(self):
        for model in ('4500', '5160'):
            for name in (model, f'U.are.U {model}', f'DigitalPersona U.are.U® {model} Fingerprint Reader'):
                with self.subTest(name=name):
                    self.assertEqual(supported_reader_model(name), model)
                    self.assertEqual(supported_reader_model(name.encode()), model)

    def test_other_models_are_not_silently_enabled(self):
        for name in ('', 'U.are.U 5100', 'U.are.U 5300', '14500', '51600', b'other\xffreader'):
            with self.subTest(name=name):
                self.assertIsNone(supported_reader_model(name))

    def test_both_models_enumerate_open_capture_enroll_and_identify(self):
        for model in ('4500', '5160'):
            sdk = FakeSDK((f'U.are.U {model} Fingerprint Reader',))
            with self.subTest(model=model), sdk.installed():
                reader = NativeReader()
                try:
                    self.assertEqual(reader.model, model)
                    self.assertEqual(sdk.opened, [b'fake-reader-0'])
                    self.assertEqual(sdk.loaded, ['dpfpdd.dll', 'dpfj.dll'])
                    reader.enroll_start()
                    for index in range(3):
                        sdk.samples.put(T)
                        sample = reader.read()
                        self.assertEqual(sample, T)
                        self.assertEqual(reader.enroll_add(sample), T if index == 2 else None)
                    reader.enroll_finish()
                    self.assertEqual(reader.match(T, [T + b'other', T]), [1])
                    self.assertEqual(reader.match(T, [T, T]), [0, 1])
                    self.assertEqual(reader.match(T, [T + b'other']), [])
                    self.assertIsNone(reader.read())
                finally:
                    reader.close()
                reader.close()  # Idempotent cleanup, including the DLL search path.
                self.assertEqual((sdk.closes, sdk.exits, sdk.directory_closes), (1, 1, 1))

    def test_supported_reader_is_found_after_an_unrelated_reader(self):
        sdk = FakeSDK(('U.are.U 5300', 'U.are.U 5160', 'U.are.U 4500'))
        with sdk.installed():
            reader = NativeReader()
            try:
                self.assertEqual(reader.model, '5160')
                self.assertEqual(sdk.opened, [b'fake-reader-1'])
            finally:
                reader.close()

    def test_no_reader_cleans_up_and_names_supported_models(self):
        sdk = FakeSDK(())
        with sdk.installed(), self.assertRaisesRegex(NoReader, '4500 o 5160'):
            NativeReader()
        self.assertEqual(sdk.opened, [])
        self.assertEqual((sdk.exits, sdk.directory_closes), (1, 1))

    def test_unsupported_reader_is_never_opened(self):
        sdk = FakeSDK(('U.are.U 5100', 'U.are.U 51600'))
        with sdk.installed(), self.assertRaisesRegex(NoReader, '4500 o 5160'):
            NativeReader()
        self.assertEqual(sdk.opened, [])
        self.assertEqual((sdk.exits, sdk.directory_closes), (1, 1))

    def test_open_failure_keeps_native_diagnostic_and_releases_sdk(self):
        sdk = FakeSDK(open_error=0x05BA001E)
        with sdk.installed(), self.assertRaisesRegex(ReaderError, '0x05BA001E'):
            NativeReader()
        self.assertEqual(sdk.closes, 0)
        self.assertEqual((sdk.exits, sdk.directory_closes), (1, 1))


if __name__ == '__main__':
    unittest.main()
