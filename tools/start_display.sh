#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/recovery-notes
multigym_display=${1:-:99}
multigym_python=/workspace/.venvs/multigym313/bin/python
multigym_probe='import tkinter as tk; r=tk.Tk(); r.update(); print("Tk display ready",r.winfo_screenwidth(),r.winfo_screenheight()); r.destroy()'
if DISPLAY="$multigym_display" "$multigym_python" -c "$multigym_probe" 2>/dev/null; then exit 0; fi
nohup /workspace/.local/xvfb/usr/bin/Xvfb "$multigym_display" -screen 0 1600x1000x24 -nolisten tcp -noreset > "/workspace/recovery-notes/xvfb-${multigym_display#:}.log" 2>&1 < /dev/null &
multigym_pid=$!
printf '%s\n' "$multigym_pid" > "/workspace/recovery-notes/xvfb-${multigym_display#:}.pid"
for multigym_attempt in {1..20}; do
  if DISPLAY="$multigym_display" "$multigym_python" -c "$multigym_probe" 2>/dev/null; then exit 0; fi
  if ! kill -0 "$multigym_pid" 2>/dev/null; then cat "/workspace/recovery-notes/xvfb-${multigym_display#:}.log"; exit 1; fi
  sleep 0.2
done
exit 1
