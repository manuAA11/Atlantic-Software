"""Compatibility entry point for common/updater.py."""
from pathlib import Path
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import updater as _implementation
sys.modules[__name__] = _implementation
