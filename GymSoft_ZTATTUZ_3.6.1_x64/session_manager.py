"""Compatibility entry point for common/session_manager.py."""
from pathlib import Path
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import session_manager as _implementation
sys.modules[__name__] = _implementation
