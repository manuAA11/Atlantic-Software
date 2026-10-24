"""Real Tk controls at 100/125%; synthetic RPC, no network or customer records."""
from pathlib import Path
import sys,os,json,time,copy
from datetime import date
from types import SimpleNamespace
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/os.environ.get('ATLANTIC_TEST_EDITION','GymSoft_ZTATTUZ_3.6.1_x86')))
sys.path.insert(0,str(ROOT))
from common import atlantic_ui as kit
from common.training_ui import RoutinesWorkspace, ClassesWorkspace, RoutineEditor, ClassEditor, ExerciseEditor, ReservationEditor
from common.appearance import install
from desktop_ui import configure_dark_styles
from ui_performance import background_reads, modal_blocks_read
from reception_app import ReceptionSettingsPage
from PIL import ImageGrab
DATA=json.loads((ROOT/'training/seeds/examples.json').read_text())

class DB:
    timezone='America/Bogota'
    def __init__(self):self.calls=[];self.slow=False;self.in_read=False
    def _today(self):return date(2030,6,15)
    def list_trainers(self,active_only=False):return [{'id':1,'name':'Entrenador QA'}]
    def training(self,action,data=None):
        if self.slow and action=='routines':
            self.in_read=True;time.sleep(.25);self.in_read=False
        time.sleep(.015);data=data or {};self.calls.append((action,copy.deepcopy(data)))
        if action=='context':return {'role':'admin','today':'2030-06-15'}
        if action=='trainers':return self.list_trainers()
        if action=='catalog':return [dict(e,active=True,gym_id=None) for e in DATA['exercises']]
        if action=='templates':return [dict(t,gym_id=None) for t in DATA['templates']]
        if action=='clients':
            rows=[{'id':i,'name':f'Cliente QA {i}','document':str(i),'has_routine':i%2==0} for i in range(1,121)]
            rows=[r for r in rows if data.get('query','') in r['name'] and (not data.get('unassigned') or not r['has_routine'])]
            return rows[data.get('offset',0):data.get('offset',0)+data.get('limit',50)]
        if action=='routines':return []
        if action=='classes':return [{'id':1,'name':'Clase QA','starts_at':'2030-06-18T23:00:00Z','duration_minutes':60,'trainer_id':1,'trainer_name':'Entrenador QA','reserved':0,'capacity':15,'version':1,'status':'PROGRAMADA','notes':'','conditions':'','requires_membership':False}]
        if action=='reservations':return []
        if action=='class.calendar':return [{'day':'2030-06-18','classes':1}]
        if action in ('template.save','routine.assign','class.save','catalog.save','reservation.reserve'):return {'saved':True}
        return []

def pump(root,predicate=lambda:True,seconds=8):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        root.update();time.sleep(.005)
        if predicate():return
    manager=background_reads(root)
    print('UI TIMEOUT', 'foreground',getattr(root,'_foreground_io',None),'closed',manager.closed,'job',manager.job,'blocks',[(str(o),modal_blocks_read(root,o)) for o in manager.owners if o.winfo_exists()],repr(root.tk.call('grab','current',root._w)), [(str(o),getattr(o,'_read_inside_modal',False)) for o in manager.owners], [(str(o),k,o.winfo_exists(),o.winfo_viewable() if o.winfo_exists() else False, bool(v.get('ready')),v.get('running')) for (o,k),v in manager.slots.items()],errors)
    raise AssertionError('Timed out waiting for UI result')

checks=0
for factor in (1,1.25):
    for theme in ('league_light','league_dark'):
        print('Checking',factor,theme,flush=True)
        kit.select_theme(theme);root=tk.Tk();root.geometry('1280x940+0+0');root.tk.call('tk','scaling',96/72*factor)
        errors=[];root.report_callback_exception=lambda *args:errors.append(str(args[1]));configure_dark_styles(root);install(root)
        db=DB();host=ttk.Frame(root);host.pack(fill='both',expand=True)
        workspace=RoutinesWorkspace(host,db);workspace.pack(fill='both',expand=True)
        pump(root,lambda:len(workspace.catalog)==44)
        workspace.tabs.select(1);pump(root,lambda:len(workspace.catalog_tree.get_children())==44)
        ticks=[];timer=[None]
        def heartbeat():
            if db.in_read:ticks.append(time.monotonic())
            timer[0]=root.after(20,heartbeat)
        heartbeat();db.slow=True;workspace.query.set('Búsqueda QA')
        pump(root,lambda:any(a=='routines' and d.get('query')=='Búsqueda QA' for a,d in db.calls))
        db.slow=False;root.after_cancel(timer[0]);assert len(ticks)>=3,'Tk blocked during the simulated network read';checks+=1
        workspace.catalog_query.set('cuadriceps');pump(root,lambda:len(workspace.catalog_tree.get_children())==1)
        editor=RoutineEditor(workspace);editor.tabs.select(1);pump(root)
        chosen=DATA['exercises'][0];editor.picker.toggle(chosen['id']);pump(root)
        editor.query.set('remo');pump(root,lambda:editor.picker.tree.get_children() and chosen['id'] not in editor.picker.tree.get_children())
        assert editor.selection.catalog_ids=={chosen['id']};checks+=1
        editor.query.set('');pump(root,lambda:chosen['id'] in editor.picker.tree.get_children())
        assert chosen['id'] in editor.picker.checked;checks+=1
        if os.environ.get('ATLANTIC_THEME_IMAGES'):
            ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((0,0,1280,940)).save(Path(os.environ['ATLANTIC_THEME_IMAGES'])/f'RoutineEditor_{theme}_{int(factor*100)}.png')
        editor.tabs.select(2);pump(root,lambda:len(editor.clients.list.tree.get_children())==50)
        editor.clients.list.toggle('1');editor.clients.page(1);pump(root,lambda:'51' in editor.clients.list.tree.get_children())
        editor.clients.list.toggle('51');assert editor.clients.list.checked=={'1','51'};checks+=1
        # A modal may load its own picker; unrelated page updates must stay deferred.
        editor.clients.query.set('Cliente QA 12');pump(root,lambda:editor.clients.list.tree.get_children()==('12','120'))
        assert editor.clients.list.checked=={'1','51'};checks+=1
        with patch('common.training_ui.messagebox.askyesno',return_value=True):editor.save()
        pump(root);saved=[d for a,d in db.calls if a=='routine.assign'][-1]
        assert saved['clients']==[1,51] and saved['exercises'][0]['catalog_id']==chosen['id'];checks+=2
        editor=RoutineEditor(workspace);editor.template.set(next(k for k,v in editor.template_choices.items() if v and v['name'].startswith('Push')))
        editor.use_template();pump(root);assert len(editor.selection.items)==4;checks+=1
        editor.params['sets'].set('5')
        with patch('common.training_ui.messagebox.showinfo'):editor.save_template()
        assert any(a=='template.save' and d['exercises'][0]['sets']==5 for a,d in db.calls);checks+=1
        if factor==1 and theme=='league_light':
            legacy=dict(name='Plan anterior',exercises=[dict(name='Ejercicio manual anterior',catalog_id=None,day='Lunes',sets=4,reps=8,weight_kg=25,rest_seconds=60)])
            editor=RoutineEditor(workspace,legacy);editor.tabs.select(1);pump(root)
            editor.picker.tree.selection_set(DATA['exercises'][0]['id']);editor.resolve_exercise();pump(root)
            assert editor.selection.payload()[0]['weight_kg']==25;checks+=1
            editor.destroy();pump(root)
        workspace.destroy();pump(root)
        classes=ClassesWorkspace(host,db);classes.pack(fill='both',expand=True);pump(root,lambda:bool(classes.rows))
        classes.tree.selection_set('1');classes.select_class();classes.toggle_calendar();pump(root)
        assert classes.calendar_visible and classes.calendar_days.winfo_children();checks+=1
        editor=ClassEditor(classes);editor.fields['name'].set('Recurrente QA');editor.fields['repeat_count'].set('4');editor.save();pump(root)
        saved=[d for a,d in db.calls if a=='class.save'][-1];assert saved['repeat_count']==4 and saved['starts_at'].endswith('-05:00');checks+=2
        editor=ReservationEditor(classes,classes.rows[0]);pump(root,lambda:bool(editor.picker.list.tree.get_children()))
        editor.picker.list.toggle('1');editor.save();pump(root);assert any(a=='reservation.reserve' and d['client_id']==1 for a,d in db.calls);checks+=1
        if os.environ.get('ATLANTIC_THEME_IMAGES'):
            ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((0,0,1280,940)).save(Path(os.environ['ATLANTIC_THEME_IMAGES'])/f'Training_{theme}_{int(factor*100)}.png')
        classes.destroy();pump(root)
        settings=ReceptionSettingsPage(host,SimpleNamespace(db=db));settings.pack(fill='both',expand=True);pump(root)
        notebook=next(w for w in settings.winfo_children() if isinstance(w,ttk.Notebook))
        assert [notebook.tab(t,'text') for t in notebook.tabs()]==['Apariencia'];checks+=1
        appearance=notebook.nametowidget(notebook.tabs()[0])
        with tempfile.TemporaryDirectory() as folder,patch('common.theme_settings.preference_path',return_value=Path(folder)/'appearance.json'):
            appearance.theme_variable.set(theme)
            next(w for w in appearance.winfo_children() if isinstance(w,ttk.Button)).invoke();pump(root)
            from common.theme_settings import load_theme
            assert load_theme()==theme;checks+=1
        assert not errors,errors
        root.destroy()
kit.select_theme('dark')
print(f'PASS {checks} real Tk workflow checks; 100/125%, light/dark, synthetic transport only.')
