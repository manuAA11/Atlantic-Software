"""Small local diagnostic: phases and error codes, never templates or identities."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re


def log_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GymSoft' / 'logs' / 'huellas.log'


def record(phase, error=None):
    if os.environ.get('GYMSOFT_OFFLINE_QA') == '1': return
    try:
        logger = logging.getLogger('GymSoft.huellas')
        if not logger.handlers:
            path = log_path(); path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(path, maxBytes=100000, backupCount=1, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            logger.addHandler(handler); logger.setLevel(logging.INFO); logger.propagate = False
        code = str(getattr(error, 'code', ''))
        codes = re.findall(r'0x[0-9A-Fa-f]{4,8}', str(error)) if error else []
        if not re.fullmatch(r'[A-Z0-9]{4,12}', code): code = ''
        logger.info('%s %s %s %s', phase, type(error).__name__ if error else '', code, ' '.join(codes))
    except Exception:
        pass  # A log failure must not interfere with capture.
