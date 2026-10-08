"""Subprocesos de validación con progreso, límite de tiempo y cierre controlado."""
from dataclasses import dataclass
import os
import queue
import signal
import subprocess
import threading
import time

ERROR_MARKERS = ('invalid command name', 'Exception in Tkinter callback',
                 'Traceback (most recent call last):')


@dataclass
class StageResult:
    returncode: int
    seconds: float
    timed_out: bool = False
    callback_failure: bool = False


def stop_process_tree(process):
    """Solo el grupo creado para esta etapa, nunca otros Python del equipo."""
    if os.name == 'nt':
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=5)


def run_stage(command, *, cwd, env, name, emit, timeout=300, heartbeat=15):
    if timeout <= 0 or heartbeat <= 0:
        raise ValueError('Los límites de tiempo deben ser positivos.')
    started = time.monotonic()
    messages = queue.Queue()
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                               errors='replace', **options)

    def read_output():
        try:
            for line in process.stdout:
                messages.put(line)
        finally:
            messages.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    eof = False
    timed_out = False
    callback_failure = False
    next_heartbeat = started + heartbeat

    def write(line):
        nonlocal callback_failure
        emit(line)
        callback_failure |= any(marker in line for marker in ERROR_MARKERS)

    try:
        while not (eof and process.poll() is not None):
            now = time.monotonic()
            if now-started >= timeout:
                timed_out = True
                emit(f'ERROR: {name} superó el límite de {timeout:g} s. '
                     'Se detiene esta prueba; no se generará un instalador incompleto.\n')
                stop_process_tree(process)
                break
            if now >= next_heartbeat:
                emit(f'EN CURSO: {name} · {now-started:.0f} s · límite {timeout:g} s.\n')
                next_heartbeat = now + heartbeat
            try:
                line = messages.get(timeout=min(.1, max(.001, timeout-(now-started))))
            except queue.Empty:
                continue
            if line is None:
                eof = True
            else:
                write(line)
        code = process.wait(timeout=5)
    except BaseException:
        stop_process_tree(process)
        raise
    finally:
        reader.join(timeout=1)
        if not reader.is_alive():
            process.stdout.close()
        while True:
            try:
                line = messages.get_nowait()
            except queue.Empty:
                break
            if line is not None:
                write(line)
    if timed_out or callback_failure:
        code = code or 1
    return StageResult(code, round(time.monotonic()-started, 2), timed_out, callback_failure)
