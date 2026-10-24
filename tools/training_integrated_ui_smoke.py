"""Native Tk -> existing RPC adapter -> isolated PostgreSQL, plus League source reads.

The subprocess has only synthetic identities; it never opens a network listener.
"""
from pathlib import Path
from types import SimpleNamespace
from datetime import date,timedelta
from unittest.mock import patch
import json,sys,os,subprocess,threading,time
import tkinter as tk
from tkinter import ttk
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/os.environ.get('ATLANTIC_TEST_EDITION','GymSoft_ZTATTUZ_3.6.1_x86')));sys.path.insert(0,str(ROOT))
from common.training_service import TrainingDatabaseMixin
from common.training_ui import RoutinesWorkspace,RoutineEditor,ClassEditor,ClassesWorkspace,ReservationEditor
from common import atlantic_ui as kit
from desktop_ui import configure_dark_styles
from ui_tasks import UiDatabase

class SQLFixture:
    def __init__(self):
        self.lock=threading.Lock()
        self.process=subprocess.Popen(['node',str(ROOT/'league/tests/training-ui-server.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        assert json.loads(self.process.stdout.readline())['ready']
    def call(self,kind,action='',data=None,**kwargs):
        with self.lock:
            self.process.stdin.write(json.dumps(dict(kind=kind,action=action,data=data or {},**kwargs))+'\n');self.process.stdin.flush()
            response=json.loads(self.process.stdout.readline())
            if not response['ok']:raise ValueError(response['error'])
            return response['value']
    def close(self):
        self.process.stdin.write('{"kind":"stop"}\n');self.process.stdin.flush();self.process.stdin.close();self.process.wait(timeout=15)
        assert self.process.returncode==0

class Database(TrainingDatabaseMixin):
    def __init__(self,fixture):
        self.fixture=fixture;self.gym_id='d0000000-0000-4000-8000-000000000004';self.cloud=SimpleNamespace(timezone='America/Bogota');self.client=self
    def rpc(self,name,args):
        assert name=='gym_training'
        return SimpleNamespace(execute=lambda:SimpleNamespace(data=self.fixture.call('training',args['p_action'],args['p_data'])))
    def _execute(self,query):return query.execute()

def pump(root,predicate=lambda:True):
    end=time.monotonic()+8
    while time.monotonic()<end:
        root.update();time.sleep(.005)
        if predicate():return
    raise AssertionError('SQL-backed UI did not finish loading')

def raise_ui_error(title,message,**kwargs):raise AssertionError(title+': '+message)
error_patch=patch('common.training_ui.messagebox.showerror',side_effect=raise_ui_error);error_patch.start()
fixture=SQLFixture();root=None
try:
    kit.select_theme('league_light');root=tk.Tk();root.geometry('1280x900');configure_dark_styles(root);errors=[]
    root.report_callback_exception=lambda *e:errors.append(str(e[1]))
    db=UiDatabase(Database(fixture),root);host=ttk.Frame(root);host.pack(fill='both',expand=True)
    plans=RoutinesWorkspace(host,db);plans.pack(fill='both',expand=True);pump(root,lambda:len(plans.catalog)==44)
    editor=RoutineEditor(plans);editor.tabs.select(1);pump(root)
    press=next(r for r in editor.catalog if r['standard_key']=='bench-press');editor.picker.toggle(press['id']);pump(root)
    editor.params['sets'].set('4');editor.tabs.select(2);pump(root,lambda:bool(editor.clients.list.tree.get_children()))
    editor.clients.list.toggle('1');editor.clients.list.toggle('2');editor.name.set('Plan desde escritorio QA')
    with patch('common.training_ui.messagebox.askyesno',return_value=True):editor.save()
    rows=fixture.call('training','routines');assert len(rows)==2
    first=next(r for r in rows if r['client_id']==1);detail=fixture.call('training','routine.detail',{'id':first['id']})
    assert detail['exercises'][0]['sets']=='4' and detail['exercises'][0]['league_catalog_id']==press['id']
    league=fixture.call('league','routines');assert any(r['id']==first['id'] or str(r['id'])==str(first['id']) for r in league)
    # Editing creates a revision, while League's source returns the current plan.
    editor=RoutineEditor(plans,detail,edit=True);editor.tabs.select(1);pump(root);editor.params['reps'].set('12')
    with patch('common.training_ui.messagebox.askyesno',return_value=True):editor.save()
    old=fixture.call('training','routine.detail',{'id':first['id']});assert not old['active'] and old['exercises'][0]['reps']=='10'
    plans.destroy();classes=ClassesWorkspace(host,db);classes.pack(fill='both',expand=True);pump(root,lambda:bool(classes.rows))
    editor=ClassEditor(classes);editor.fields['name'].set('Clase desde escritorio QA')
    future=date.fromisoformat(fixture.call('training','context')['today'])+timedelta(days=2)
    editor.fields['starts_at'].set(str(future)+' 18:00');editor.fields['capacity'].set('2');editor.membership.set(False);editor.save();pump(root)
    actual=fixture.call('training','classes',{'query':'Clase desde escritorio QA'})[0]
    editor=ReservationEditor(classes,actual);pump(root,lambda:bool(editor.picker.list.tree.get_children()));editor.picker.list.toggle('1');editor.save();pump(root)
    assert len(fixture.call('training','reservations',{'class_id':actual['id']}))==1
    calendar=fixture.call('league','calendar');assert any(str(c['id'])==str(actual['id']) for c in calendar)
    # Mobile enrollment appears in the desktop list, reading the same records.
    fixture.call('league','reserve',{'class_id':actual['id']},client=2)
    assert len(fixture.call('training','reservations',{'class_id':actual['id']}))==2
    classes.destroy();pump(root)
    from app import ClassesPage
    page=ClassesPage(host,SimpleNamespace(db=db));page.pack(fill='both',expand=True);page.refresh()
    pump(root,lambda:len(page.workspace.reservation_rows)==2)
    fixture.call('league','cancel',{'class_id':actual['id']},client=2)
    page.refresh()  # Same identity/context; operational rows must still refresh.
    pump(root,lambda:any(r['client_id']==2 and r['status']=='CANCELADA' for r in page.workspace.reservation_rows))
    assert not errors,errors
    print('PASS: native editor -> authenticated training RPC -> PostgreSQL; grouped assignment, immutable revision, class creation, reservation, desktop/League visibility both directions. Synthetic isolated fixtures only.')
finally:
    if root:root.destroy()
    fixture.close();error_patch.stop()
