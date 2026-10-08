#!/usr/bin/env bash
set -euo pipefail
cd /workspace/Atlantic-Software
command -v uv >/dev/null
command -v node >/dev/null
command -v npm >/dev/null
/usr/bin/python3.13 -c 'import sys, tkinter; assert sys.version_info[:2] == (3,13)'
if [ ! -x /workspace/.venvs/multigym313/bin/python ]; then
  uv venv --cache-dir /workspace/.cache/uv --python /usr/bin/python3.13 /workspace/.venvs/multigym313
fi
uv pip install --cache-dir /workspace/.cache/uv --python /workspace/.venvs/multigym313/bin/python -r tools/requirements-cloud.lock
for edition in GymSoft_Comercial_3.6.0 GymSoft_ZTATTUZ_3.6.1_x86 GymSoft_ZTATTUZ_3.6.1_x64; do
  uv pip install --cache-dir /workspace/.cache/uv --python /workspace/.venvs/multigym313/bin/python -r "$edition/requirements.txt"
  (cd "$edition" && npm ci --cache /workspace/.cache/npm --no-audit --no-fund)
done
bash tools/install_display.sh
uv pip check --cache-dir /workspace/.cache/uv --python /workspace/.venvs/multigym313/bin/python
