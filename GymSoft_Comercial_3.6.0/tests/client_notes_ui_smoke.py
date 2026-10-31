"""Real Tk staff notices, scrolling, failed writes and replacement at check-in."""
import os, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['GYMSOFT_OFFLINE_QA']='1'
from unittest.mock import Mock, patch
import tkinter as tk
import app as admin
import reception_app as reception
from common.client_notes_ui import open_client_notes
from responsive_ui_smoke import shell, descendants
from ui_assertions import pump, destroy_root, resize_test_window
from ui_test_support import settle_geometry


def main():
    checks=0
    for factor in (1,1.25):
        for module,app_class,key in ((admin,admin.GymSoftApp,'checkin'),(reception,reception.ReceptionApp,'access')):
            with patch.object(reception.branding,'show_reception_logo',lambda *_:None):
                root=shell(app_class,factor)
            failures=[];root.report_callback_exception=lambda *args:failures.append(str(args[1]))
            try:
                # General note and current membership remain separate; failed save retains input.
                db=Mock();db.get_client_notes.return_value={'client_notice':'Avisar a recepción','revision':7,'membership_notes':'Traer soporte'}
                saved=Mock()
                win=open_client_notes(root,db,42,'Ana Prueba',module.BaseDialog,saved);pump(root)
                assert 'Avisar a recepción' in win.note_editor.get('1.0','end');checks+=1
                win.note_editor.delete('1.0','end');win.note_editor.insert('1.0','Revisar documento\nAl finalizar la clase')
                db.save_client_note.side_effect=RuntimeError('Sin conexión')
                with patch('common.client_notes_ui.messagebox.showerror') as error:
                    win.save_note();assert error.called and win.winfo_exists();assert not saved.called;checks+=2
                db.save_client_note.side_effect=None;db.save_client_note.return_value={'revision':8}
                win.save_note();assert saved.call_count==1
                db.save_client_note.assert_called_with(42,'Revisar documento\nAl finalizar la clase',7);checks+=2
                with patch.object(root.page_types['clients'],'refresh',lambda *_:None):root.show_page('clients')
                clients_page=root.pages['clients']
                row={'id':42,'document':'TEST','client_name':'Ana Prueba','first_name':'Ana','last_name':'Prueba',
                     'phone':'','birthdate':'','membership_status':'AL DÍA','status':'AL DÍA','client_notice':'Aviso guardado',
                     'membership_notes':'Nota mensual','active':True}
                if key=='checkin':clients_page._render_refresh([row])
                else:
                    from datetime import date
                    clients_page._render_refresh(([row],[],date(2026,10,30)))
                clients_page.tree.selection_set('42');clients_page.show_note_preview();pump(root)
                assert 'Aviso guardado' in clients_page.note_preview.get() and 'Nota mensual' in clients_page.note_preview.get();checks+=1
                with patch.object(root.page_types[key],'refresh',lambda *_:None):root.show_page(key)
                page=root.pages[key]
                note='Aviso de prueba\n'+'Texto largo que debe poder consultarse sin agrandar las columnas. '*120
                result={'id':42,'document':'TEST','client_name':'Ana Prueba','status':'AL DÍA','result':'PERMITIDA',
                        'allowed':True,'membership_end':'2026-10-31','client_notice':note,'membership_notes':'Traer soporte',
                        'access_detail':'Membresía vigente.','expiry_notice':'La membresía vence mañana.'}
                if key=='checkin':page.show_result(result)
                else:
                    page.db=Mock();page.db.register_checkin.return_value=result
                    page.refresh_clients=Mock();page.refresh_history=Mock()
                    page.register_client_entry(42,'PRUEBA',show_confirmation=False)
                for width in (960,1366):
                    resize_test_window(root,f'{width}x900');pump(root)
                    panel=page.result_notes
                    settle_geometry(root,(panel,panel.text),'notas largas sin cambiar ancho')
                    text=panel.text.get('1.0','end-1c')
                    assert note.rstrip() in text and 'Traer soporte' in text, 'The full notice and membership note must remain readable'
                    checks+=1
                    assert panel.winfo_width()>100 and panel.text.winfo_height()>20;checks+=1
                    panel.text.yview_moveto(1);pump(root);assert panel.text.yview()[1]>.95;checks+=1
                if key=='checkin':page.show_result({**result,'id':43,'client_notice':'','membership_notes':'','access_detail':'Sin membresía','result':'DENEGADA'})
                else:
                    page.db.register_checkin.return_value={**result,'id':43,'client_notice':'','membership_notes':'','access_detail':'Sin membresía','result':'DENEGADA'}
                    page.register_client_entry(43,'PRUEBA',show_confirmation=False)
                assert 'Aviso de prueba' not in page.result_notes.text.get('1.0','end');checks+=1
                root.on_biometric_unknown('sin-coincidencia');pump(root)
                assert 'Sin notas ni avisos' in page.result_notes.text.get('1.0','end');checks+=1
                assert not failures,failures
            finally:destroy_root(root)
    print(f'PASS: {checks} client notices UI checks, Admin/Reception, 100/125%, simulated server only.')


if __name__=='__main__':main()
