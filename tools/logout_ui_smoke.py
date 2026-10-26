"""Real Admin/Reception logout buttons and fresh credential form at 100/125%."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'GymSoft_Comercial_3.6.0'))
sys.path.insert(0, str(ROOT / 'GymSoft_Comercial_3.6.0' / 'tests'))
os.environ['GYMSOFT_OFFLINE_QA'] = '1'
import app
import reception_app
from common.atlantic_ui import COLORS
from common.session_manager import MemorySessionStore, SessionManager
from common.session_ui import SessionStatus
from runtime_cloud import LoginDialog
from responsive_ui_smoke import shell, assert_buttons_fit
from ui_assertions import pump, destroy_root


def main():
    checks = 0
    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, LOCALAPPDATA=folder):
        for factor in (1, 1.25):
            for cls in (app.GymSoftApp, reception_app.ReceptionApp):
                root = shell(cls, factor)
                failures = []
                root.report_callback_exception = lambda *error: failures.append(error)
                root.ready = True
                root.realtime_listener = Mock()
                client = Mock(supabase_key='synthetic-public-key')
                client.options.headers = {}
                store = MemorySessionStore()
                sessions = SessionManager(client, store)
                client.auth.get_session = lambda: sessions.session
                sessions.session = NS(access_token='synthetic', refresh_token='synthetic-refresh')
                store.save({'synthetic': True})
                root.cloud.sessions = sessions
                root.session_status = SessionStatus(root, root.cloud)
                pump(root, .15)
                button = root.logout_button
                settings = root.nav_buttons['settings']
                assert button.cget('text') == 'Cerrar sesión'
                assert button.cget('style') == 'Danger.TButton'
                assert ttk.Style(root).lookup('Danger.TButton', 'foreground') == COLORS['danger']
                assert button.master is settings.master and button.winfo_y() < settings.winfo_y()
                assert_buttons_fit(root)
                checks += 5
                root.pages['shop'] = NS(pos=NS(cart=NS(rows={1: 'synthetic'})))
                with patch('common.session_ui.messagebox') as messages:
                    button.invoke()
                    messages.showinfo.assert_called_once()
                assert store.load() is not None and root.ready
                checks += 2
                root.pages.clear()
                # Reception also covers a server outage during explicit logout.
                if cls is reception_app.ReceptionApp:
                    client.auth.sign_out.side_effect = ConnectionError('synthetic network outage')
                listener = root.realtime_listener
                button.invoke()
                assert root._return_to_login and not root.ready
                assert store.load() is None and sessions.ensure() is None
                client.auth.sign_out.assert_called_once_with({'scope': 'local'})
                listener.stop.assert_called_once()
                assert not root.tk.call('after', 'info')
                assert not failures, failures
                checks += 6
                # The next workspace starts at a new, empty credential form.
                fresh = tk.Tk()
                fresh.geometry('900x650')
                fresh.tk.call('tk', 'scaling', 96 / 72 * factor)
                fresh.report_callback_exception = lambda *error: failures.append(error)
                dialog = LoginDialog(fresh, allow_signup=False)
                pump(fresh, .15)
                assert dialog.winfo_viewable()
                assert not dialog.password.get() and not dialog.email.get()
                assert not failures, failures
                checks += 3
                dialog.destroy()
                destroy_root(fresh)
    print(f'LOGOUT UI {checks} CHECKS PASS: actual Admin/Reception red buttons above Settings, busy cart guard, online/offline credential removal and fresh login at 100/125%; synthetic auth only.')


if __name__ == '__main__':
    main()
