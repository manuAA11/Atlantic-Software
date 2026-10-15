"""Feed genuine local SQL access responses through the optional door boundary."""
from pathlib import Path
import json
import sys
import tempfile
import time
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from door_access import ConfigStore, DoorConfig, DoorController, DoorDatabase, RELAY_ON, RELAY_OFF
from test_door_access import FakeUSB, until

cases=json.load(sys.stdin)
checks=0
for case in cases:
    # This scenario checks immediate duplicate scans in logical time. Windows
    # USB cleanup/disk latency must not advance the 0.75 s scan debounce or
    # the 2 s authorization age. Event/Timer/monotonic deadlines remain real.
    with tempfile.TemporaryDirectory() as folder, patch('door_access.time.time', return_value=10_000.):
        store=ConfigStore(folder,'local-sql-contract')
        usb=FakeUSB()
        door=DoorController(store,transport=lambda _:usb,clock=lambda:10.,ports_provider=lambda:[])
        usb.on=door._cancel.set
        store.save(DoorConfig(True,'COM7',3,0x1A86,0x7523))
        backend=Mock(); backend.register_checkin.return_value=case['result']
        proxy=DoorDatabase(backend,door)
        try:
            actual=proxy.register_fingerprint_checkin(case['client'],case['method'])
            assert actual is case['result']
            until(lambda:not door._pending)
            assert bool(usb.frames.count(RELAY_ON))==case['allowed'],case['name']
            if case['allowed']: assert usb.frames[-1]==RELAY_OFF
            duplicate=proxy.register_fingerprint_checkin(case['client'],case['method'])
            assert duplicate['duplicate_read']
            assert backend.register_checkin.call_count==1
            assert usb.frames.count(RELAY_ON)==int(case['allowed'])
            checks+=5
        finally:door.close()
print(f'DOOR SQL/DRIVER BRIDGE {checks} CHECKS PASS: server responses preserved; denied never unlock; repeated reads never repeat RPC/pulse.')
