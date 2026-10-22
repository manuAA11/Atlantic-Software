"""Compatibility entry point for common/realtime_listener.py."""
from pathlib import Path
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import realtime_listener as _implementation
sys.modules[__name__] = _implementation
