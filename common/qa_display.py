"""Launch UI validation and its X server in the same isolated execution session."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

def main():
    bundle=Path('/workspace/scratch/e5e938934c13/ui-deps')
    compiler=Path('/usr/bin/xkbcomp')
    if not compiler.exists(): compiler.symlink_to(bundle/'usr/bin/xkbcomp')
    display=int(os.environ.get('GYMSOFT_QA_DISPLAY_NUMBER','96'))
    env=dict(os.environ,DISPLAY=f'127.0.0.1:{display}',
        LD_LIBRARY_PATH=str(bundle/'usr/lib/x86_64-linux-gnu'),
        XKB_CONFIG_ROOT=str(bundle/'usr/share/X11/xkb'))
    with open('qa_display.log','w') as log:
        server=subprocess.Popen([str(bundle/'usr/bin/Xvfb'),f':{display}','-screen','0','1600x1000x24',
            '-nolisten','unix','-nolisten','local','-listen','tcp','-ac'],env=env,stdout=log,stderr=log)
        try:
            connected=False
            for _ in range(40):
                with socket.socket() as s:
                    if s.connect_ex(('127.0.0.1',6000+display))==0:
                        connected=True
                        break
                if server.poll() is not None:raise RuntimeError('Xvfb failed; see qa_display.log')
                time.sleep(.1)
            if not connected: raise RuntimeError('Xvfb did not open its display; see qa_display.log')
            return subprocess.call(sys.argv[1:],env=env)
        finally:server.terminate();server.wait(timeout=5)

if __name__=='__main__':sys.exit(main())
