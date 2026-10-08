import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from owner_forms import (amount, contract_params, email, grace_params, invite_params,
                         new_gym_params, renewal_params, required)

GYM={'id':'a0000000-0000-4000-8000-000000000001','currency':'COP',
     'active_devices':2,'active_users':3}


class OwnerFormsTest(unittest.TestCase):
    def test_amount_formats(self):
        for value in ['200000','200.000','200,000','200000.00','200.000,00','200,000.00']:
            with self.subTest(value=value):self.assertEqual(amount(value),'200000.00')
        self.assertEqual(amount('40,50'),'40.50')
        self.assertEqual(amount('0'),'0.00')

    def test_invalid_amounts(self):
        for value in ['', '-1','NaN','Infinity','$500','2e5','1,234,56','1.2345','10000000000']:
            with self.subTest(value=value), self.assertRaises(ValueError):amount(value)

    def test_reference_required_before_rpc(self):
        for value in ['', '  ', 'a','12']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'Referencia'):
                renewal_params(GYM,{'months':'1','amount':'200000','reference':value})

    def test_month_limits(self):
        for value in ['0','121','-1','1.5','x','']:
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'Meses'):
                renewal_params(GYM,{'months':value,'amount':'100','reference':'Recibo-001'})

    def test_renewal_is_idempotent(self):
        form={'months':'1','amount':'200.000','reference':' Recibo-001 '}
        a=renewal_params(GYM,form);b=renewal_params(GYM,form)
        self.assertEqual(a,b)
        self.assertEqual(a['p_reference'],'Recibo-001')
        other=renewal_params({**GYM,'id':'a0000000-0000-4000-8000-000000000002'},form)
        self.assertNotEqual(a['p_idempotency_key'],other['p_idempotency_key'])

    def test_role_selection(self):
        for label,role in [('Administración','admin'),('Recepción','receptionist')]:
            self.assertEqual(invite_params(GYM,{'email':' Staff@Example.com ','role':label})['p_role'],role)
        with self.assertRaises(ValueError):invite_params(GYM,{'email':'a@example.com','role':'owner'})

    def test_email_validation(self):
        self.assertEqual(email(' A@Example.com '),'a@example.com')
        for v in ['','test','a@b','a b@b.com','a@b.']:
            with self.subTest(value=v),self.assertRaises(ValueError):email(v)

    def test_reason_validation(self):
        for v in ['', '  ', 'si']:
            with self.subTest(value=v),self.assertRaises(ValueError):required(v,'Motivo',3)
        self.assertEqual(required(' Autorizado ','Motivo',3),'Autorizado')

    def test_contract_constraints(self):
        f={'price':'200000','currency':'cop','devices':'2','users':'3','notes':''}
        self.assertEqual(contract_params(GYM,f)['p_currency'],'COP')
        for key,value in [('devices','1'),('users','2'),('devices','101'),('users','1001'),('currency','pesos')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):contract_params(GYM,{**f,key:value})

    def test_grace_validation(self):
        self.assertEqual(grace_params(GYM,{'days':'3','reason':'Pago pendiente'})['p_days'],3)
        for f in [{'days':'31','reason':'plazo'},{'days':'0','reason':'plazo'},{'days':'3','reason':''}]:
            with self.subTest(form=f),self.assertRaises(ValueError):grace_params(GYM,f)

    def test_create_gym_validation(self):
        f={'name':'Gimnasio nuevo','email':'gym@example.com','price':'100.000','currency':'COP',
           'devices':'2','days':'7','timezone':'America/Bogota'}
        self.assertEqual(new_gym_params(f)['p_monthly_price'],'100000.00')
        for key,value in [('name',''),('days','0'),('days','91'),('timezone','No existe'),('email','x'),('price','-1')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):new_gym_params({**f,key:value})


if __name__=='__main__':unittest.main()
