import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from owner_editor_forms import confirmation,email_params,profile_params,record_patch,read_backup,write_backup

class OwnerEditorFormsTest(unittest.TestCase):
    def setUp(self):self.gym={'id':'10000000-0000-4000-8000-000000000001','name':'Gym Manuel'}

    def test_destination_name_must_match(self):
        with self.assertRaises(ValueError):confirmation(self.gym,{'name':'Otro gym','reason':'Prueba'})
        self.assertEqual(confirmation(self.gym,{'name':'Gym Manuel','reason':'Prueba'})['p_name'],'Gym Manuel')

    def test_email_roles_and_timezone(self):
        for label,role in [('Recepción','receptionist'),('Administración','admin')]:
            self.assertEqual(email_params(self.gym,{'email':'User@Example.com','role':label,'reason':'Prueba'})['p_role'],role)
        with self.assertRaises(ValueError):email_params(self.gym,{'email':'invalid','role':'admin','reason':'Prueba'})
        raw={'name':'Nuevo','email':'user@example.com','timezone':'America/Bogota','plan':'Pro','reason':'Prueba'}
        self.assertEqual(profile_params(self.gym,raw)['p_name'],'Nuevo')
        with self.assertRaises(ValueError):profile_params(self.gym,{**raw,'timezone':'Invalid/Zone'})

    def test_typed_patch_preserves_unedited_protected_fields(self):
        cols=[{'name':'id','type':'bigint','editable':False,'nullable':False},
              {'name':'amount','type':'bigint','editable':True,'nullable':False},
              {'name':'active','type':'boolean','editable':True,'nullable':False},
              {'name':'birth_date','type':'date','editable':True,'nullable':True}]
        old={'id':1,'amount':500,'active':True,'birth_date':'2000-01-01'}
        result=record_patch(cols,old,{'id':'999','amount':'400','active':'No','birth_date':''})
        self.assertEqual(result,{'amount':400,'active':False,'birth_date':None})
        with self.assertRaises(ValueError):record_patch(cols,old,{'amount':'1.2','active':'Sí','birth_date':''})

    def test_dates_require_timezone(self):
        col={'name':'paid_at','type':'timestamp with time zone','editable':True,'nullable':False}
        with self.assertRaises(ValueError):record_patch([col],{}, {'paid_at':'2026-09-07T12:00:00'})
        self.assertTrue(record_patch([col],{}, {'paid_at':'2026-09-07T12:00:00Z'})['paid_at'].endswith('+00:00'))

    def test_backup_atomicity_and_format(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'backup.json';data={'format':'GymSoft-CLOUD-2','tables':{},'gym_id':self.gym['id']}
            write_backup(p,data);self.assertEqual(read_backup(p),data)
            with patch('owner_editor_forms.os.replace',side_effect=OSError('Disco lleno')):
                with self.assertRaises(OSError):write_backup(p,{**data,'changed':True})
            self.assertEqual(read_backup(p),data)
            self.assertEqual(list(Path(d).iterdir()),[p])
            p.write_text(json.dumps({'format':'SQL','tables':{}}))
            with self.assertRaises(ValueError):read_backup(p)

if __name__=='__main__':unittest.main()
