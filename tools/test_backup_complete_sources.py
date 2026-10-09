"""Packaging boundary checks; synthetic inputs do not validate vendor/hardware."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location("complete_source_package", Path(__file__).with_name("backup_complete_sources.py"))
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


class PackagingBoundaries(unittest.TestCase):
    def test_other_product_is_excluded_and_tracked_private_paths_fail(self):
        editions = package.PRODUCTS["AtlanticGym"]
        self.assertEqual(package.select_sources(["GymSoft_ZTATTUZ_3.6.1_x64/app.py", "GymSoft_Comercial_3.6.0/app.py"], editions), ["GymSoft_Comercial_3.6.0/app.py"])
        for unsafe in ("GymSoft_Comercial_3.6.0/.env", "docs/../private.txt", "docs/vendor/Samples/sample.c", "common/key.pem"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                package.select_sources([unsafe], editions)

    def test_private_credentials_fail_but_public_config_is_allowed(self):
        secret = b"prv_test_" + b"a" * 24
        with self.assertRaises(ValueError):
            package.check_no_secrets("backend/config.json", secret)
        payload = base64.urlsafe_b64encode(json.dumps({"role": "service_role"}).encode()).rstrip(b"=")
        token = b"eyJhbGciOiJIUzI1NiJ9." + payload + b".abcdefghi"
        with self.assertRaises(ValueError):
            package.check_no_secrets("desktop.json", token)
        package.check_no_secrets("gymsoft_config.json", json.dumps({"supabase_url": "https://example.supabase.co", "supabase_publishable_key": "public-fixture"}).encode())
        with self.assertRaises(ValueError):
            package.check_no_secrets("gymsoft_config.json", json.dumps({"service_role": "fixture"}).encode())

    def fixture_archive(self, path: Path, *, changed_runtime=False, extra_sdk=False, duplicate=False):
        edition = "GymSoft_Comercial_3.6.0"
        runtime = b"synthetic-runtime-x64"
        eula = b"synthetic-test-license"
        def metadata(name, data):
            return {"path": name, "bytes": len(data), "sha256": package.digest(data)}
        sdk = {"runtimes": {"x64": {"files": [metadata("setup.exe", runtime)]}}, "license": metadata("Licenses/EULA SDK.rtf", eula)}
        entries = {f"{edition}/{name}": b"synthetic-source-fixture" for name in package.REQUIRED}
        entries[f"{edition}/gymsoft_config.json"] = json.dumps({"supabase_url": "https://example.supabase.co", "supabase_publishable_key": "public-fixture"}).encode()
        entries[f"{edition}/DigitalPersonaRuntime/setup.exe"] = b"synthetic-runtime-x86" if changed_runtime else runtime
        entries[f"{edition}/DigitalPersonaRuntime/Licenses/EULA SDK.rtf"] = eula
        for name in ("README.md", "CONDICIONES_RUNTIME.txt", "docs/vendor/digitalpersona/sdk-manifest.json"):
            entries[name] = b"synthetic-document-fixture"
        if extra_sdk:
            entries["docs/vendor/Samples/sample.c"] = b"forbidden-vendor-sdk-sample"
        manifest = {"type": "APPLICATION_COMPLETE_DEVELOPMENT", "final_release": False, "product": "AtlanticGym", "editions": package.PRODUCTS["AtlanticGym"], "files": [metadata(name, data) for name, data in entries.items()]}
        # Hashes reflect the tampered entry: vendor authority must still reject it.
        entries["APP_MANIFEST.json"] = json.dumps(manifest).encode()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr("ApplicationFixture/" + name, data)
            if duplicate:
                archive.writestr("ApplicationFixture/README.md", b"duplicate")
        return sdk

    def test_tampered_runtime_is_rejected_even_with_updated_application_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "application.zip"
            sdk = self.fixture_archive(path)
            package.validate_archive(path, sdk)
            self.fixture_archive(path, changed_runtime=True)
            with self.assertRaisesRegex(ValueError, "Runtime incorrecto"):
                package.validate_archive(path, sdk)

    def test_sdk_source_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "application.zip"
            sdk = self.fixture_archive(path, extra_sdk=True)
            with self.assertRaises(ValueError):
                package.validate_archive(path, sdk)

    def test_wrong_external_hash_and_conflicting_resource_do_not_mutate_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "application.zip"
            sdk = self.fixture_archive(path)
            edition = "GymSoft_Comercial_3.6.0"
            (root / edition).mkdir()
            with self.assertRaises(ValueError):
                package.restore_runtime_from_package(path, root, [edition], sdk, "0" * 64)
            self.assertFalse((root / edition / "DigitalPersonaRuntime").exists())
            target = root / edition / "DigitalPersonaRuntime/setup.exe"
            target.parent.mkdir()
            target.write_bytes(b"preserve-existing-resource")
            with self.assertRaises(ValueError):
                package.restore_runtime_from_package(path, root, [edition], sdk, package.digest(path.read_bytes()))
            self.assertEqual(target.read_bytes(), b"preserve-existing-resource")
            self.assertFalse((target.parent / "Licenses").exists())

    def test_package_cannot_restore_another_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "application.zip"
            sdk = self.fixture_archive(path)
            with self.assertRaises(ValueError):
                package.restore_runtime_from_package(path, root, ["GymSoft_ZTATTUZ_3.6.1_x64"], sdk, package.digest(path.read_bytes()))
            self.assertFalse((root / "GymSoft_ZTATTUZ_3.6.1_x64").exists())


if __name__ == "__main__":
    unittest.main()
