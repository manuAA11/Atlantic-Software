"""Regresiones de huella opcional y configuración de planes (sin red)."""
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from biometric import ScanBuffer
from cloud_database import CloudDatabase
from reception_database import ReceptionDatabase
from plan_forms import validate_plan


class AccessPlans(TestCase):
    def db(self):
        db=CloudDatabase.__new__(CloudDatabase);db.gym_id='gimnasio-prueba'
        db.client=Mock();db._data=Mock(return_value=[{'id':17}]);db._execute=Mock()
        return db

    def test_blank_biometrics_use_null_to_preserve_legacy_unique_index(self):
        for value in ['',None,'   ']:
            for client_id in [None,42]:
                db=self.db();db.save_client({'document':'123','first_name':'Ana','last_name':'Prueba','biometric_identifier':value},client_id)
                table=db.client.table.return_value
                payload=(table.insert if client_id is None else table.update).call_args.args[0]
                self.assertIsNone(payload['biometric_identifier'])
                self.assertEqual(payload['gym_id'],'gimnasio-prueba')

    def test_biometric_code_normalized_when_present(self):
        db=self.db();db.save_client({'biometric_identifier':' ab 012 '})
        self.assertEqual(db.client.table.return_value.insert.call_args.args[0]['biometric_identifier'],'AB012')

    def test_ticket_limits_do_not_depend_on_plan_name(self):
        for limit in [1,15,20,37,None]:
            db=self.db();db.add_plan('Plan personalizado',30,55000,limit)
            value=db.client.table.return_value.insert.call_args.args[0]
            self.assertEqual(value['entry_limit'],limit)
            self.assertEqual(value['duration_days'],30)
        self.assertEqual(validate_plan('Tiquetera',30,100,None)[3],None)

    def test_edit_ticket_limit_preserves_gym_scope(self):
        db=self.db();db._data.return_value=[{'entry_limit':15}]
        db.update_plan(17,'Tiquetera 20',30,60000,20)
        value=db.client.table.return_value.update.call_args.args[0]
        self.assertEqual(value['entry_limit'],20)
        self.assertEqual(db.client.table.return_value.update.return_value.eq.call_args.args,('gym_id','gimnasio-prueba'))

    def test_existing_sales_prevent_days_to_tickets_type_change(self):
        db=self.db();db._data.side_effect=[[{'entry_limit':None}],[{'id':9}]]
        with self.assertRaisesRegex(ValueError,'compras registradas'):
            db.update_plan(17,'Nuevo nombre',30,5000,20)
        db.client.table.return_value.update.assert_not_called()

    def test_invalid_ticket_limits_rejected_before_writing(self):
        for limit in ['',0,-1,'1.5','abc','15.0']:
            db=self.db()
            with self.subTest(limit=limit),self.assertRaises(ValueError): db.add_plan('Tiquetera',30,100,limit)
            db.client.table.assert_not_called()

    def test_fast_scanner_with_or_without_terminator_is_recognized(self):
        for value in ['ABC123','001234']:
            b=ScanBuffer()
            for i,char in enumerate(value):b.feed(char,100+i*.009)
            self.assertEqual(b.value(),value)
            b.reset();self.assertIsNone(b.value())

    def test_manual_typing_incomplete_bursts_and_long_gap_are_not_scans(self):
        for intervals in [[0,.2,.4,.6],[0,.01,.03,.5],[0,.06,.12,.18]]:
            b=ScanBuffer()
            for char,now in zip('A123',intervals):b.feed(char,now)
            self.assertIsNone(b.value())
