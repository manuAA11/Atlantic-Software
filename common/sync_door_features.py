"""Copy the shared optional door implementation and its tests to each product."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def synchronize():
    for edition in ROOT.glob('GymSoft_*'):
        # door_access.py is a compatibility alias to the shared module.
        for name in ('door_ui.py',):
            shutil.copyfile(ROOT / 'common' / name, edition / name)
        for name in ('test_door_access.py', 'test_door_ordering.py', 'test_door_request_lock.py', 'test_door_cleanup.py', 'test_door_cleanup_extra.py',
                     'door_ui_smoke.py', 'door_server_bridge.py', 'door_access_flow.mjs'):
            source = ROOT / 'common' / name
            if source.exists(): shutil.copyfile(source, edition / 'tests' / name)

if __name__ == '__main__': synchronize()
