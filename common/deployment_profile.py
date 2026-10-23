"""Compatibility with installed data/providers; one Commercial application."""
from dataclasses import dataclass
import json
from product_config import resource_root

@dataclass(frozen=True)
class DeploymentProfile:
    legacy_provider: bool = False

    @property
    def installation_profile(self): return 'ztattuz' if self.legacy_provider else 'commercial'
    @property
    def data_folder(self): return 'GymControl' if self.legacy_provider else 'GymSoft'
    @property
    def scoped_data(self): return not self.legacy_provider
    @property
    def template_prefix(self): return 'ztattuz' if self.legacy_provider else 'gymsoft'
    @property
    def backup_format(self): return 'ZTATTUZ-CLOUD-1' if self.legacy_provider else 'GymSoft-CLOUD-1'
    @property
    def import_format(self): return 'ZTATTUZ-EXCEL-REPLACE-2' if self.legacy_provider else 'GymSoft-EXCEL-REPLACE-2'
    @property
    def context_rpc(self): return 'reception_account_context' if self.legacy_provider else 'commercial_context'
    @property
    def system_rpc(self): return 'ztattuz_system_info' if self.legacy_provider else 'commercial_system_info'
    @property
    def server_product(self): return 'gymsoft-ztattuz' if self.legacy_provider else 'gymsoft-commercial'
    @property
    def server_schema(self): return '3.4.5' if self.legacy_provider else '3.0.0'
    @property
    def license_rpc(self): return None if self.legacy_provider else 'commercial_check_license'


def load_profile():
    path = resource_root() / 'gymsoft_config.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    provider = config.get('backend_kind', 'commercial')
    if provider not in {'commercial', 'ztattuz_legacy'}:
        raise ValueError('Proveedor de datos no compatible.')
    return DeploymentProfile(provider == 'ztattuz_legacy')

PROFILE = load_profile()
