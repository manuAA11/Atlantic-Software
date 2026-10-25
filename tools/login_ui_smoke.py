"""Real Tk access forms: branding, validation, focus, roles and 100/125% layout.

No account, server or hardware is used. Optional screenshots contain synthetic data.
"""
import argparse
from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'GymSoft_Comercial_3.6.0'))
from desktop_ui import configure_dark_styles, decorate_window
from runtime_cloud import LoginDialog
from common import runtime_cloud as access
from common.session_ui import SessionStatus


def settle(root):
    until = time.monotonic() + .12
    while time.monotonic() < until:
        root.update()
        time.sleep(.01)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args()
    checks=0
    for factor in (1, 1.25):
        root=tk.Tk();root.tk.call('tk','scaling',96/72*factor)
        root.geometry('1100x900+20+20');configure_dark_styles(root)
        errors=[];root.report_callback_exception=lambda *error:errors.append(error)
        for role in ('admin','reception','owner'):
            root._atlantic_icon_name='icono_recepcion.ico' if role=='reception' else 'icono.ico'
            decorate_window(root)
            login=LoginDialog(root,owner=role=='owner');settle(root)
            assert login.winfo_viewable() and login.title()=='Atlantic Gym · Iniciar sesión';checks+=1
            assert login._atlantic_icon_name==root._atlantic_icon_name;checks+=1
            assert login.password_entry.cget('show')=='*';checks+=1
            login.email.set('invalid');login.accept()
            assert login.winfo_exists() and login.result is None and login.feedback.get();checks+=1
            login.email.set('demo@example.invalid');login.accept()
            assert login.winfo_exists() and login.feedback.get()=='Escribe tu contraseña.';checks+=1
            if role!='owner':
                login.switch_mode();settle(root)
                assert login.creating_account and login.submit.cget('text')=='Crear cuenta';checks+=1
                login.password.set('short');login.accept()
                assert login.winfo_exists() and '12 caracteres' in login.feedback.get();checks+=1
                login.switch_mode()
                assert login.email.get()=='demo@example.invalid' and not login.password.get();checks+=1
            else:
                login.switch_mode()
                assert not login.creating_account and not login.mode_button.winfo_manager();checks+=1
            login.feedback.set('');settle(root)
            # The primary action stays within the visible area at the default size.
            assert login.submit.winfo_rooty()+login.submit.winfo_height()<=login.winfo_rooty()+login.winfo_height(),('hidden submit',factor,role,login.submit.winfo_rooty(),login.winfo_height());checks+=1
            for entry in (login.email_entry,login.password_entry,login.submit):
                assert entry.winfo_width()>=260 and entry.winfo_rootx()>=login.winfo_rootx();checks+=1
            if args.screenshots and role=='admin':
                from PIL import ImageGrab
                args.screenshots.mkdir(parents=True,exist_ok=True)
                x,y=login.winfo_rootx(),login.winfo_rooty()
                ImageGrab.grab(bbox=(x,y,x+login.winfo_width(),y+login.winfo_height())).save(args.screenshots/f'login-{int(factor*100)}.png')
            login.password.set('SyntheticPass123')
            login.accept();assert login.result==('demo@example.invalid','SyntheticPass123');checks+=1
        # Reauthentication cannot create a different account.
        recovery=LoginDialog(root,allow_signup=False);settle(root)
        assert not recovery.mode_button.winfo_manager();checks+=1;recovery.destroy()
        # Actual Tk form after a saved-token failure, then a rejected password.
        # Neither failure displays an error dialog whose Cancel closes startup.
        cloud=Mock(email='demo@example.invalid',role='admin')
        cloud.restore_session.side_effect=ValueError('JWT issued at future')
        cloud.load_gym.return_value=True
        cloud.sign_in.side_effect=[ValueError('Invalid login credentials'),None]
        forms=[]
        def recovered_form(*args,**kwargs):
            login=LoginDialog(*args,**kwargs);settle(root)
            assert login.winfo_viewable() and root.winfo_exists()
            assert login.email.get()=='demo@example.invalid' and login.password.get()==''
            assert login.feedback.get() and 'JWT' not in login.feedback.get()
            assert login.submit.winfo_rooty()+login.submit.winfo_height()<=login.winfo_rooty()+login.winfo_height()
            assert login.password_entry.cget('show')=='*'
            if args and args[0].state()!='withdrawn':
                assert login.focus_get() is login.password_entry
            forms.append(login)
            root.after(60,lambda:(login.password.set('SyntheticPass123'),login.accept()))
            return login
        with patch.object(access,'CloudService',return_value=cloud), \
             patch.object(access,'LoginDialog',side_effect=recovered_form), \
             patch.object(access,'_record_login_error'), \
             patch.object(access,'messagebox') as messages, \
             patch('ui_tasks.run_io',side_effect=lambda parent,fn,**kw:fn()), \
             patch('licensing.check_license',return_value={'allowed':True}):
            assert access.connect_cloud(root) is cloud;checks+=1
            assert len(forms)==2;checks+=1
            cloud.restore_session.assert_called_once();checks+=1
            assert cloud.sign_in.call_count==2;checks+=1
            messages.askretrycancel.assert_not_called();checks+=1
            messages.showerror.assert_not_called();checks+=1
            cloud.sessions.logout.assert_not_called();checks+=1
            assert root.winfo_exists();checks+=1
        # Revocation inside the open workspace: retry credentials inline and
        # cancel the form without destroying the root or replaying an operation.
        cloud.sessions.state='AUTH_REQUIRED'
        status=SessionStatus(root,cloud)
        forms=[]
        def reauthentication_form(*args,**kwargs):
            login=LoginDialog(*args,**kwargs);settle(root)
            assert login.winfo_viewable() and root.winfo_viewable()
            assert login.email.get()=='demo@example.invalid' and not login.password.get()
            assert not login.mode_button.winfo_manager()
            assert login.focus_get() is login.password_entry
            if forms:
                assert login.feedback.get()=='Correo o contraseña incorrectos.'
            forms.append(login)
            root.after(60,lambda:(login.password.set('SyntheticPass123'),login.accept()))
            return login
        with patch('runtime_cloud.LoginDialog',side_effect=reauthentication_form), \
             patch('common.session_ui.recover_identity',side_effect=[ValueError('Invalid login credentials'),None]) as recover, \
             patch('common.session_ui.run_io',side_effect=lambda parent,fn,**kw:fn()), \
             patch('common.session_ui.messagebox') as messages:
            status.recover()
            assert len(forms)==2 and recover.call_count==2;checks+=1
            messages.showerror.assert_not_called();checks+=1
            assert root.winfo_exists() and root.winfo_viewable();checks+=1
        def cancelled_form(*args,**kwargs):
            login=LoginDialog(*args,**kwargs)
            root.after(60,login.destroy)
            return login
        with patch('runtime_cloud.LoginDialog',side_effect=cancelled_form), \
             patch('common.session_ui.recover_identity') as recover:
            status.recover()
            recover.assert_not_called();checks+=1
            assert root.winfo_exists() and cloud.sessions.state=='AUTH_REQUIRED';checks+=1
        root.withdraw();hidden=LoginDialog(root);settle(root)
        assert hidden.winfo_viewable();checks+=1;hidden.destroy()
        assert not errors,errors;checks+=1
        root.destroy()
    print(f'LOGIN UI {checks} CHECKS PASS: actual Tk, Atlantic Gym, role icons, account modes, validation, visible actions and hidden parent at 100/125%.')

if __name__=='__main__':main()
