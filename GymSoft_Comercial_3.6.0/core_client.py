"""Compatibility entry point for common/core_client.py."""
from pathlib import Path
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import core_client as _implementation
sys.modules[__name__] = _implementation
