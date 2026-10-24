"""Real Tk exercise catalog, both themes; fake transport and no customer data."""
from pathlib import Path
import sys
import os
from types import SimpleNamespace
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/os.environ.get('ATLANTIC_TEST_EDITION','GymSoft_ZTATTUZ_3.6.1_x86')))
sys.path.insert(0, str(ROOT))
from common import atlantic_ui as kit
from desktop_ui import configure_dark_styles
from common.league_ui import CatalogPanel

class API:
    def __init__(self):
        self.rows = [{'id':'one','name':'Sentadilla','muscle':'Piernas','equipment':'Barra'},
                     {'id':'two','name':'Remo','muscle':'Espalda','equipment':'Mancuerna'}]
        self.writes = []
    def call(self, action, data=None):
        if action == 'catalog': return self.rows
        self.writes.append((action, data))
        if action == 'catalog_create': self.rows.append({'id':'three',**data})
        return {}

checks = 0
for theme in ('dark', 'minimal'):
    kit.select_theme(theme)
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda *e: errors.append(str(e))
    configure_dark_styles(root)
    api = API()
    with patch('common.league_ui.LeagueClient', return_value=api):
        panel = CatalogPanel(root, SimpleNamespace(db=SimpleNamespace(cloud=None)))
        panel.call = api.call
        panel.pack(fill='both',expand=True)
        for width, height in ((1120,760),(800,600)):
            root.geometry(f'{width}x{height}')
            panel.refresh(); root.update()
            assert len(panel.tree.get_children()) == 2
            panel._toggle('one'); panel.search.set('espalda'); root.update()
            assert panel.tree.get_children() == ('two',)
            assert panel.checked == {'one'}
            panel.search.set(''); panel.checked.clear(); checks += 3
        def save_dialog():
            dialogs = [w for w in panel.winfo_children() if isinstance(w, tk.Toplevel)]
            assert dialogs
            dialog = dialogs[0]
            dialog.fields['name'].set('Curl de bíceps')
            dialog.fields['muscle'].set('Bíceps')
            dialog.save()
        root.after(150, save_dialog)
        panel.create(); root.update()
        assert api.writes[0][0] == 'catalog_create'
        assert api.writes[0][1]['name'] == 'Curl de bíceps'
        assert len(panel.tree.get_children()) == 3
        assert not errors, errors
        checks += 4
    root.destroy()
print(f'PASS {checks} real Tk catalog checks; simulated API, no production writes.')
