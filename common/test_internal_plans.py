import unittest
import tempfile
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from datetime import date
from plan_forms import validate_plan_options, plan_end_date, plan_label, membership_request
from membership_features import expiry_label
from payment_revision import posted_income, validate_import_payment

class InternalPlans(unittest.TestCase):
    def test_arbitrary_names_and_actual_nulls(self):
        for name in ('STAFF', 'Propietario', 'Invitado', 'Entrenador especial'):
            row=validate_plan_options(name,None,0,None,None,'INTERNAL',True,False,False)
            self.assertEqual(row,(name,None,0,None,None,'INTERNAL',True,False,False))
        plan=dict(name='STAFF',plan_type='INTERNAL',has_expiration=False,unlimited_access=True)
        self.assertIsNone(plan_end_date(plan,date(2026,10,20)))
        self.assertIn('Sin pago',plan_label(plan,str))
        self.assertEqual(expiry_label(plan,str),'Sin vencimiento')

    def test_internal_has_no_sale_or_fake_income(self):
        row=dict(membership_type='INTERNAL',payment_status='non_commercial',amount=0,include_in_financial_stats=False)
        validate_import_payment(row)
        self.assertEqual(posted_income([row,dict(amount=70000,payment_status='posted')]),70000)
        with self.assertRaises(ValueError):validate_import_payment(dict(row,amount=5000))
        with self.assertRaises(ValueError):validate_import_payment(dict(row,membership_type='COMMERCIAL'))
        with self.assertRaises(ValueError):validate_plan_options('STAFF',None,100,None,None,'INTERNAL',True,False,False)

    def test_assignment_has_stable_reference_and_no_payment(self):
        key=str(uuid4())
        name,args=membership_request('gym',1,2,'2026-10-20',0,'','','STAFF',internal=True,request_id=key)
        self.assertEqual(name,'assign_internal_membership');self.assertEqual(args['p_request_id'],key)
        self.assertNotIn('p_amount',args)
        with self.assertRaises(ValueError):membership_request('gym',1,2,None,100,'',internal=True,request_id=key)
        with self.assertRaises(ValueError):membership_request('gym',1,2,None,0,'',internal=True,request_id=None)

    def test_commercial_and_ticket_contracts_remain(self):
        self.assertEqual(validate_plan_options('Mensual',30,70000),('Mensual',30,70000,None,None,'COMMERCIAL',True,True,True))
        self.assertEqual(validate_plan_options('Tiquetera',60,90000,15,2),('Tiquetera',60,90000,15,2,'COMMERCIAL',False,True,True))
        self.assertEqual(membership_request('g',1,2,None,70000,'Efectivo')[0],'add_membership_accumulating')

    def test_real_excel_roundtrip_preserves_internal_flags_nulls_and_history(self):
        from cloud_database import CloudDatabase
        flags=dict(unlimited_access=True,has_expiration=False,include_in_financial_stats=False)
        event=dict(id=str(uuid4()),starts_at='2026-10-20T14:00:00Z',resumed_at='2026-10-22T14:00:00Z',freeze_used_days=2,completion_kind='MANUAL')
        tables={'clients':[dict(id=1,document='STAFF-1',first_name='Personal',last_name='Prueba',active=True)],
                'plans':[dict(id=2,name='STAFF',plan_type='INTERNAL',price=0,duration_days=None,entry_limit=None,**flags)],
                'memberships':[dict(id=3,client_id=1,plan_id=2,membership_type='INTERNAL',membership_active=True,start_date='2026-10-20',end_date=None,paid_at=None,amount=0,amount_paid=0,payment_status='non_commercial',**flags),
                               dict(id=4,client_id=1,plan_id=5,membership_type='COMMERCIAL',start_date='2026-09-01',end_date='2026-09-30',amount=70000,payment_status='posted',freeze_archive=[event]) ]}
        # Keep the commercial history linked to its own normal plan.
        tables['plans'].append(dict(id=5,name='Mensual anterior',duration_days=30,price=70000,entry_limit=None,plan_type='COMMERCIAL',has_expiration=True,unlimited_access=True,include_in_financial_stats=True))
        db=CloudDatabase.__new__(CloudDatabase);db.gym_id='local-test'
        db._cloud_table_rows=lambda name:deepcopy(tables.get(name,[]))
        db._now=lambda:datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            target=db.export_excel(Path(folder)/'staff.xlsx')
            restored=db.prepare_excel_replacement(target)['tables']
            plan=next(p for p in restored['plans'] if p['name']=='STAFF')
            member=next(m for m in restored['memberships'] if m['membership_type']=='INTERNAL')
            self.assertFalse(plan['has_expiration']);self.assertFalse(member['include_in_financial_stats'])
            self.assertTrue(member['unlimited_access']);self.assertIsNone(member.get('end_date'))
            self.assertIsNone(member.get('paid_at'));self.assertIsNone(plan.get('duration_days'))
            commercial=next(m for m in restored['memberships'] if m['membership_type']=='COMMERCIAL')
            self.assertEqual(commercial['freeze_archive'],[event])

if __name__=='__main__':unittest.main()
