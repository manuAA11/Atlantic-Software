"""Commercial application compatibility entry point; no edition-specific logic."""
from pathlib import Path
import sys
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import reception_app as _implementation
sys.modules[__name__] = _implementation

if __name__ == "__main__":
    _implementation.main()
