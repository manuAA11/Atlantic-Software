"""Fake USB reader -> real worker/store -> application RPCs -> local PostgreSQL.
Never uses a physical reader or a remote account. Tests both desktop roles.
"""
import os
os.environ['GYMSOFT_OFFLINE_QA']='1'
from datetime import timedelta
from pathlib import Path
import queue,sys,time
from types import SimpleNamespace as NS
from uuid import uuid4
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cloud_database import CloudDatabase
from reception_database import ReceptionDatabase
from fingerprint_service import FingerprintService
from fingerprint_store import CloudTemplateStore
from local_service import Engine,Client

class Reader:
    def __init__(self):self.samples=queue.Queue();self.added=0
    def read(self):
        try:return self.samples.get(timeout=.03)
        except queue.Empty:return None
    def match(self,sample,templates):return [i for i,t in enumerate(templates) if t==sample]
    def finger_present(self):return False
    def enroll_start(self):self.added=0
    def enroll_add(self,sample):self.added+=1;return sample if self.added==3 else None
    def enroll_finish(self):pass
    def close(self):pass

def until(fn):
    end=time.monotonic()+8
    while not fn():
        assert time.monotonic()<end,'No terminó la prueba local de entrada biométrica.'
        time.sleep(.01)

checks=0
def check(value,label):
    global checks
    assert value,label;checks+=1;print('  OK:',label,flush=True)

def main():
    engine=Engine();services=[]
    def rpc(uid,name,**params):return Client(engine,uid).rpc(name,params).execute().data
    try:
        owner,aid,rid=[str(uuid4()) for _ in range(3)]
        for uid in (owner,aid,rid):engine.sql('insert into auth.users(id,email) values($1,$2)',[uid,uid+'@example.test'])
        if (ROOT/'sql/030_commercial.sql').exists():
            engine.sql('insert into private.software_owners(user_id) values($1)',[owner])
            info=rpc(owner,'owner_create_gym',p_name='Huella local',p_email=aid+'@example.test',p_monthly_price=1000)
            gid=info['gym_id'];rpc(aid,'commercial_accept_invite',p_code=info['activation_code'])
            rpc(aid,'commercial_check_license',p_device_hash='c'*64,p_device_name='Simulado')
            detail=rpc(owner,'owner_gym_detail',p_gym_id=gid)
            rpc(owner,'owner_set_device',p_device_id=detail['devices'][0]['id'],p_blocked=False,p_reason='Prueba local')
            rpc(aid,'commercial_check_license',p_device_hash='c'*64,p_device_name='Simulado')
            invite=rpc(owner,'owner_invite_user',p_gym_id=gid,p_email=rid+'@example.test',p_role='receptionist')
            rpc(rid,'commercial_accept_invite',p_code=invite)
            rpc(rid,'commercial_check_license',p_device_hash='c'*64,p_device_name='Simulado')
        else:
            gid=rpc(aid,'create_gym',p_name='Huella local')
            invite=rpc(aid,'create_reception_invite');rpc(rid,'redeem_reception_invite',p_code=invite)
        def db(cls,uid):return cls(NS(client=Client(engine,uid),gym_id=gid,user_id=uid,timezone='America/Bogota',gym_name='Prueba'))
        admin,recep=db(CloudDatabase,aid),db(ReceptionDatabase,rid)
        today=admin._today();monthly=admin.add_plan('Mensual biométrica',30,60000);ticket=admin.add_plan('Una entrada',30,10000,1)
        for index,database in enumerate((admin,recep)):
            reader=Reader();store=CloudTemplateStore(database)
            service=FingerprintService(store,database.register_checkin,lambda:reader);service.pause(True)
            services.append(service);service.start();until(lambda:service.reader is not None)
            clients={};templates={}
            def person(kind):
                payload=dict(document=f'BIO-{index}-{kind}',first_name='Prueba',last_name=kind,phone='',email='',birthdate='',biometric_identifier='',active=kind!='inactivo')
                cid=admin.save_client(payload);clients[kind]=cid;templates[kind]=b'FMR\0'+bytes([10+index])*40+kind.encode();return cid
            for kind in ('mensual','tiquetera','sinplan','inactivo','vencido'):person(kind)
            for kind in ('mensual','inactivo','vencido'):
                day=today-timedelta(days=90) if kind=='vencido' else today
                admin.add_membership(clients[kind],monthly,day.isoformat(),60000,'Efectivo')
            admin.add_membership(clients['tiquetera'],ticket,today.isoformat(),10000,'Efectivo')
            def event(kind):
                end=time.monotonic()+8
                while time.monotonic()<end:
                    try:
                        k,v=service.events.get(timeout=.1)
                        if k==kind:return v
                    except queue.Empty:pass
                raise AssertionError('Falta evento: '+kind+' / '+str(service._status))
            service.send('enroll',clients['mensual']);until(lambda:service.phase=='capture')
            for n in range(3):reader.samples.put(templates['mensual']);until(lambda:reader.added==n+1)
            until(lambda:service.phase=='verify_new')
            check(clients['mensual'] not in CloudTemplateStore(admin).load(),'Antes de verificar no se guarda plantilla')
            reader.samples.put(templates['mensual'])
            check(event('enrollment_end')['result']=='saved','Registro confirma guardado real en PostgreSQL')
            check(CloudTemplateStore(recep if index==0 else admin).load()[clients['mensual']]==templates['mensual'],'Otro rol/equipo recibe la misma huella')
            def count():return engine.sql('select count(*) n from public.checkins where gym_id=$1',[gid])[0]['n']
            before=count();service.send('verify',clients['mensual']);until(lambda:service.phase=='verify_only');reader.samples.put(templates['mensual'])
            check(event('enrollment_end')['result']=='verified' and count()==before,'Comprobar huella no registra asistencia')
            external=CloudTemplateStore(admin);saved=external.load()
            for kind in ('tiquetera','sinplan','inactivo','vencido'):
                saved[clients[kind]]=templates[kind];external.save(saved)
            service.pause(False)
            for kind in ('mensual','tiquetera','sinplan','inactivo','vencido'):
                reader.samples.put(templates[kind]);result=event('access')
                allowed=kind in ('mensual','tiquetera')
                check(result['result']==('PERMITIDA' if allowed else 'DENEGADA'),'Entrada biométrica '+kind)
            check(admin.membership_snapshot(clients['tiquetera'])['entries_remaining']==0,'Tiquetera descuenta exactamente una entrada')
            before=count();reader.samples.put(templates['tiquetera']);time.sleep(.2)
            check(count()==before,'Lectura repetida no duplica ingreso ni descuenta otra entrada')
            service.last[clients['tiquetera']]-=11;reader.samples.put(templates['tiquetera'])
            result=event('access')
            check(result['result']=='PERMITIDA' and result['already_consumed_today'] and result['entries_remaining']==0,'Tiquetera agotada permite reentrada el mismo día')
            engine.sql("create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select now()+interval '1 day'$$")
            service.last[clients['tiquetera']]-=11;reader.samples.put(templates['tiquetera'])
            check(event('access')['result']=='DENEGADA','Sin saldo se deniega el día siguiente')
            engine.sql("create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select now()$$")
            before=count();reader.samples.put(b'FMR\0'+b'unknown'*10);until(lambda:'no reconocida' in service._status)
            check(count()==before,'Huella desconocida no escribe entrada')
            service.pause(True);service.send('delete',clients['mensual']);event('template_deleted');service.last.clear();service.pause(False)
            before=count();reader.samples.put(templates['mensual']);until(lambda:'no reconocida' in service._status)
            check(count()==before and clients['mensual'] not in CloudTemplateStore(admin).load(),'Huella eliminada deja de permitir identificación')
            service.close();service.thread.join(5)
        print(f'PASS: {checks} comprobaciones completas de huella, nube y entrada en ambos roles; lector simulado y PostgreSQL local.',flush=True)
    finally:
        for service in services:service.close();service.thread.join(5)
        engine.close()

if __name__=='__main__':
    with patch('fingerprint_service.ReaderLease',return_value=NS(acquire=lambda:True,close=lambda:None)):main()
