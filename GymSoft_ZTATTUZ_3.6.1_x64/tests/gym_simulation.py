"""Jornada de gimnasio con las clases Python y el SQL de ZTATTUZ reales.

Cada ejecución crea PostgreSQL en memoria, usuarios ficticios y dos gimnasios.
No recibe URL ni credenciales; no modifica una base remota ni envía mensajes.
"""
from datetime import date, timedelta
import functools
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cloud_database import CloudDatabase
from reception_database import ReceptionDatabase
from local_service import Engine, Client, LocalDatabaseError


class Simulation:
    def __init__(self, output):
        self.output=output
        self.checks=[]
        self.methods=set()
        self.section='Preparación'
        self.engine=Engine()

    def track(self, db):
        for name in dir(type(db)):
            if name.startswith('_') or not callable(getattr(db,name)):continue
            original=getattr(db,name)
            @functools.wraps(original)
            def call(*args,_fn=original,_name=name,**kwargs):
                self.methods.add(type(db).__name__+'.'+_name)
                return _fn(*args,**kwargs)
            setattr(db,name,call)
        return db

    def stage(self,name):
        self.section=name
        print('SIMULACIÓN: '+name,flush=True)

    def check(self,value,label):
        assert value, self.section+' / '+label
        self.checks.append(dict(section=self.section,case=label,status='PASS'))

    def rejected(self,fn,label,contains=()):
        try:fn()
        except (LocalDatabaseError,ValueError,sqlite3.IntegrityError,RuntimeError,PermissionError) as error:
            if contains:
                assert any(part.casefold() in str(error).casefold() for part in contains), str(error)
            self.check(True,label)
        else:raise AssertionError('La operación inválida fue aceptada: '+label)

    def rpc(self,user,name,**params):
        return Client(self.engine,user).rpc(name,params).execute().data

    def run(self):
        self.stage('Cuentas y acceso original de ZTATTUZ')
        admin_id,reception_id,other_id=[str(uuid4()) for _ in range(3)]
        for uid,email in [(admin_id,'admin@example.test'),(reception_id,'reception@example.test'),(other_id,'other@example.test')]:
            self.engine.sql('INSERT INTO auth.users(id,email) VALUES($1,$2)',[uid,email])
        gid=self.rpc(admin_id,'create_gym',p_name='Gimnasio Simulación')
        other_gid=self.rpc(other_id,'create_gym',p_name='Gimnasio Independiente')
        invite=self.rpc(admin_id,'create_reception_invite')
        self.rpc(reception_id,'redeem_reception_invite',p_code=invite)
        self.check(self.rpc(reception_id,'reception_account_context')['role']=='receptionist','Invitación conserva el rol de Recepción')
        self.check(self.rpc(admin_id,'ztattuz_system_info')['schema_version']=='3.4.5','Servidor reconoce la actualización')
        def db(cls,uid,gym_id):
            return self.track(cls(SimpleNamespace(client=Client(self.engine,uid),user_id=uid,
                gym_id=gym_id,timezone='America/Bogota',gym_name='Gimnasio de simulación')))
        admin=db(CloudDatabase,admin_id,gid)
        reception=db(ReceptionDatabase,reception_id,gid)
        independent=db(CloudDatabase,other_id,other_gid)
        today=admin._today();day=today.isoformat()
        self.check(reception.today()==today,'Administración y Recepción usan la fecha del gimnasio')
        admin.invalidate_today_cache();reception.invalidate_today_cache()
        self.check(admin.is_empty() and independent.is_empty(),'Gimnasios comienzan sin clientes')

        self.stage('Clientes, cumpleaños, huella opcional y búsquedas')
        serial=0
        def person(name,biometric='',target=admin):
            nonlocal serial
            serial+=1
            data=dict(document=f'SIM-{serial:03}',first_name=name,last_name='Prueba',
                phone='3001234567',email=f'cliente{serial}@example.test',
                birthdate=f'2000-{today:%m-%d}',biometric_identifier=biometric,active=True)
            return target.save_client(data),data
        ana,ana_data=person('Ana')
        bruno,bruno_data=person('Bruno','001234',reception)
        carla,carla_data=person('Carla')
        isolated,isolated_data=person('Cliente externo',target=independent)
        self.check(len(admin.list_clients())==3 and len(reception.list_clients())==3,'Ambos roles ven las altas del mismo gimnasio')
        self.check(admin.get_client(ana)['birthdate']==ana_data['birthdate'],'Cumpleaños guardado correctamente')
        self.check(admin.get_client_by_document(ana_data['document'])['id']==ana,'Buscar documento')
        self.check(admin.get_client_by_biometric_identifier('001234')['id']==bruno,'Buscar huella en Administración')
        self.check(reception.find_client_by_biometric_identifier('001234')['id']==bruno,'Buscar huella en Recepción')
        self.check(len(admin.list_clients('Ana'))==1 and len(reception.list_clients('Bruno'))==1,'Buscar nombre sin mezclar personas')
        self.check(not admin.get_client_by_document('NO-EXISTE'),'Búsqueda sin coincidencias')
        self.check(not reception.find_client_by_biometric_identifier('999999'),'Huella desconocida no identifica un cliente')
        self.rejected(lambda:reception.save_client(ana_data),'Documento duplicado rechazado',('existe','duplic','unique'))
        self.rejected(lambda:person('Huella repetida','001234'),'Huella duplicada rechazada',('pertenece','duplic','unique'))
        ana_data['phone']='3007654321';admin.save_client(ana_data,ana)
        bruno_data['last_name']='Actualizado';reception.save_client(bruno_data,bruno)
        self.check(admin.get_client(ana)['phone']=='3007654321','Editar contacto desde Administración')
        self.check(admin.get_client(bruno)['last_name']=='Actualizado','Editar cliente desde Recepción')
        disposable,_=person('Registro temporal');admin.delete_client(disposable)
        self.check(admin.get_client(disposable) is None,'Eliminar un registro temporal sin relaciones')
        self.check(admin.get_client(isolated) is None,'Aislamiento de lectura entre gimnasios')

        self.stage('Planes mensuales, tiqueteras y pagos')
        monthly=admin.add_plan('Mensual simulación',30,60000)
        ticket15=admin.add_plan('Tiquetera 15',30,75000,15,2)
        ticket20=admin.add_plan('Tiquetera 20',30,95000,20,3)
        session=admin.add_plan('Sesión de prueba',1,10000,1)
        inactive=admin.add_plan('Plan temporal',7,20000)
        admin.update_plan(inactive,'Plan semanal',7,22000)
        admin.set_plan_active(inactive,False)
        self.check(inactive not in {p['id'] for p in reception.list_plans()},'Plan desactivado oculto en nuevas ventas')
        self.check(any(p['id']==inactive for p in admin.list_plans(False)),'Administración conserva los planes inactivos')
        admin.set_plan_active(inactive,True)
        self.rejected(lambda:admin.add_plan('Inválido',0,60000),'Plan de duración cero rechazado')
        payment=admin.add_membership(ana,monthly,day,60000,'Efectivo','SIM-PAGO-001')
        self.check(payment>0 and admin.membership_snapshot(ana)['allowed'],'Pago mensual habilita acceso')
        ticket_sale=reception.add_membership(bruno,ticket15,day,75000,'TRANSFERENCIA','SIM-PAGO-002')
        self.check(ticket_sale['membership_id']>0,'Recepción registra tiquetera con transferencia')
        self.check(reception.membership_snapshot(bruno)['entries_remaining']==15,'Tiquetera inicia con 15 entradas')
        first=admin.list_memberships(ana)[0]
        renewal=admin.add_membership(ana,monthly,day,60000,'Transferencia','SIM-PAGO-003')
        renewed=next(p for p in admin.list_memberships(ana) if p['id']==renewal)
        self.check(renewed['start_date']>first['end_date'],'Renovación anticipada acumula vigencia')
        self.check(len(reception.list_memberships(ana))==2,'Recepción consulta ambas mensualidades')
        self.rejected(lambda:admin.update_plan(monthly,'Cambio de tipo',30,60000,15,1),'No cambia a tiquetera un plan con mensualidades vendidas')
        admin.update_plan(ticket15,'Tiquetera 18',30,90000,18,3)
        self.check(reception.membership_snapshot(bruno)['entry_limit']==15,'Editar plan conserva el cupo ya vendido')
        migrated,migrated_data=person('Tiquetera anterior')
        key=str(uuid4())
        carry=admin.add_membership(migrated,ticket20,(today-timedelta(days=10)).isoformat(),0,'Efectivo',
            notes='Tiquetera existente',carryover=True,initial_entries_used=12,request_id=key)
        retry=admin.add_membership(migrated,ticket20,(today-timedelta(days=10)).isoformat(),0,'Efectivo',
            notes='Tiquetera existente',carryover=True,initial_entries_used=12,request_id=key)
        self.check(carry==retry and reception.membership_snapshot(migrated)['entries_remaining']==8,'Traslado de tiquetera conserva el saldo y no se duplica al reintentar')
        self.check(admin.list_memberships(migrated)[0]['amount']==0,'Traslado no genera un pago ficticio')

        self.stage('Registro de entrada, cupos y control de acceso')
        self.check(admin.register_checkin(ana,'MANUAL')['result']=='PERMITIDA','Entrada mensual manual')
        self.check(reception.register_checkin(bruno,'HUELLA')['entries_remaining']==14,'Entrada con huella descuenta una unidad')
        self.check(reception.register_checkin(carla,'MANUAL')['result']=='DENEGADA','Sin plan se deniega entrada')
        self.check(admin.register_checkin(carla,'MANUAL',override=True)['result']=='PERMITIDA','Administración puede autorizar una excepción')
        ana_data['active']=False;admin.save_client(ana_data,ana)
        self.check(reception.register_checkin(ana,'MANUAL')['result']=='DENEGADA','Cliente inactivo no entra aunque tenga pago')
        ana_data['active']=True;admin.save_client(ana_data,ana)
        single,single_data=person('Sesión diaria',target=reception)
        reception.add_membership(single,session,day,10000,'TARJETA','SIM-SESION')
        self.check(reception.register_checkin(single,'MANUAL')['result']=='PERMITIDA','Sesión permite una entrada')
        self.check(reception.register_checkin(single,'MANUAL')['already_consumed_today'],'Sesión permite reentrada el mismo día sin descontar')
        self.check(any(r['client_id']==single for r in admin.list_checkins()),'Historial administrativo muestra entradas')
        self.check(len(reception.list_checkins())>=6,'Historial de Recepción incluye resultados permitidos y denegados')

        self.stage('Corrección y anulación de pagos con auditoría')
        changed=self.rpc(admin_id,'ztattuz_change_payment',p_gym_id=gid,p_membership_id=payment,
            p_expected_revision=0,p_action='correct',p_reason='Corrección de comprobante',
            p_amount=55000,p_payment_method='Transferencia',p_payment_reference='SIM-CORREGIDO')
        self.check(int(changed['amount'])==55000 and changed['payment_revision']==1,'Corrección conserva el registro y aumenta revisión')
        self.rejected(lambda:self.rpc(admin_id,'ztattuz_change_payment',p_gym_id=gid,p_membership_id=payment,
            p_expected_revision=0,p_action='void',p_reason='Pantalla anterior'),
            'Conflicto de edición desde una pantalla desactualizada',('actualiz','cambi','versi'))
        history=self.rpc(admin_id,'ztattuz_payment_history',p_gym_id=gid,p_membership_id=payment)
        self.check(bool(history),'Historial de corrección disponible')
        voided=self.rpc(admin_id,'ztattuz_change_payment',p_gym_id=gid,p_membership_id=renewal,
            p_expected_revision=0,p_action='void',p_reason='Renovación duplicada de prueba')
        self.check(voided['payment_status']=='void','Anulación conserva la evidencia')
        self.check(len(reception.list_memberships(ana))==1,'Pago anulado deja de ampliar la vigencia')
        payment_list=self.rpc(admin_id,'ztattuz_client_payments',p_gym_id=gid,p_client_id=ana,p_include_void=True)
        self.check(len(payment_list['rows'])==2,'Editor sigue mostrando el pago anulado')

        self.stage('Tienda, inventario y ventas desde Recepción')
        product_data=dict(name='Agua 600 ml',sku='77000001',sale_price=3000,stock_quantity=10,
                          low_stock_threshold=3,active=True)
        product=admin.save_store_product(product_data)
        self.check(reception.list_store_products('77000001')[0]['id']==product,'Buscar producto por código de barras')
        sale=reception.register_store_sale(product,2,'EFECTIVO','SIM-VENTA','Ana Prueba')
        self.check(bool(sale),'Venta guardada desde Recepción')
        self.check(admin.list_store_products('Agua')[0]['stock_quantity']==8,'Venta descuenta inventario')
        self.rejected(lambda:reception.register_store_sale(product,9,'EFECTIVO'),'Se impide vender más que el stock',('stock','existencia','disponib'))
        self.rejected(lambda:reception.register_store_sale(product,0,'EFECTIVO'),'Cantidad de venta cero rechazada')
        self.check(admin.list_store_products('Agua')[0]['stock_quantity']==8,'Ventas rechazadas no cambian inventario')
        product_data.update(stock_quantity=8,active=False);admin.save_store_product(product_data,product)
        self.check(not reception.list_store_products('77000001'),'Producto inactivo no se ofrece en Recepción')
        product_data['active']=True;admin.save_store_product(product_data,product)
        self.check(len(admin.list_store_sales())==1,'Historial de ventas sin duplicados')
        store=admin.store_finance(day,day)
        self.check(bool(store),'Finanzas de tienda consulta el período')

        self.stage('Gastos, caja y conciliación del día')
        expense=dict(expense_date=day,category='Servicios',description='Aseo del gimnasio',vendor='Proveedor de prueba',
                     amount=12000,payment_method='Efectivo',payment_reference='SIM-GASTO',notes='Jornada de prueba')
        eid=admin.save_expense(expense)
        rid=reception.create_expense(dict(expense,description='Compra de recepción',amount=5000))
        expense['amount']=10000;admin.save_expense(expense,eid)
        temporary=admin.save_expense(dict(expense,description='Gasto temporal',amount=1000))
        admin.delete_expense(temporary)
        rows=self.engine.sql('SELECT id,amount FROM public.accounting_expenses WHERE gym_id=$1',[gid])
        self.check({r['id'] for r in rows}=={eid,rid} and sum(int(r['amount']) for r in rows)==15000,
            'Alta, edición y eliminación de gastos conservan el total correcto')
        self.check(bool(admin.accounting_expenses(day,day)),'Informe de gastos consulta ambos roles')
        finance=self.rpc(admin_id,'get_finance_dashboard',p_gym_id=gid,p_date_from=day,p_date_to=day)
        self.check(int(finance['total_income'])==140000,'Caja suma pagos corregidos y excluye anulados y traslados')

        self.stage('Personal, turnos y rutinas')
        trainer_data=dict(name='Entrenadora Simulación',phone='3001234567',email='trainer@example.test',
            specialty='Fuerza',hourly_rate=12000,hire_date=day,active=True)
        trainer=admin.save_trainer(trainer_data)
        trainer_data['specialty']='Fuerza y movilidad';admin.save_trainer(trainer_data,trainer)
        self.check(admin.list_trainers(True)[0]['specialty']=='Fuerza y movilidad','Crear y editar personal')
        admin.staff_clock(trainer,'IN')
        self.rejected(lambda:admin.staff_clock(trainer,'IN'),'No se abren dos turnos a la vez')
        admin.staff_clock(trainer,'OUT')
        self.rejected(lambda:admin.staff_clock(trainer,'OUT'),'No se cierra un turno inexistente')
        self.check(bool(admin.staff_dashboard(day,day)),'Turno cerrado visible en informe de personal')
        routine=admin.create_routine(ana,trainer,'Adaptación','Fuerza',day,'Tres días por semana')
        admin.add_exercise(routine,'Lunes','Sentadilla','3','12','20 kg','Técnica controlada')
        admin.add_exercise(routine,'Lunes','Remo','3','10','15 kg','Descanso 60 segundos')
        self.check(admin.list_routines()[0]['exercise_count']==2,'Rutina vinculada al cliente y entrenador')
        self.check([r['position'] for r in admin.list_exercises(routine)]==[1,2],'Ejercicios mantienen el orden')
        trainer_data['active']=False;admin.save_trainer(trainer_data,trainer)
        self.check(not admin.list_trainers(True),'Personal inactivo se oculta del listado activo')
        trainer_data['active']=True;admin.save_trainer(trainer_data,trainer)

        self.stage('Clases y reservas')
        class_id=admin.create_class('Movilidad',trainer,day+'T18:00:00-05:00',1,'Una plaza de prueba')
        reservation=admin.reserve_class(class_id,ana)
        self.rejected(lambda:admin.reserve_class(class_id,bruno),'Clase llena no acepta otra reserva',('cupo',))
        admin.cancel_reservation(reservation)
        self.check(admin.reserve_class(class_id,ana)==reservation,'Reserva cancelada puede reactivarse sin duplicarse')
        self.check(len(admin.list_reservations(class_id))==1,'Listado de reservas mantiene un registro')
        self.check(admin.list_classes()[0]['name']=='Movilidad','Clase y entrenador disponibles en la agenda')

        self.stage('Dashboard, estadísticas y seguimiento comercial')
        metrics=admin.dashboard_metrics()
        self.check(metrics['active_clients']==5,'Dashboard cuenta clientes del gimnasio')
        allowed=self.engine.sql("SELECT count(*) AS n FROM public.checkins WHERE gym_id=$1 AND result='PERMITIDA'",[gid])[0]['n']
        self.check(metrics['checkins_today']==allowed,'Dashboard cuenta entradas permitidas')
        self.check(bool(admin.attendance_statistics(30)),'Estadísticas consultan la asistencia del período')
        self.check(any(r['client_id']==migrated for r in admin.ticket_followup()),'Dashboard incluye tiqueteras con pocas entradas')
        self.check(any(r['client_id']==bruno for r in reception.ticket_followup()),'Recepción consulta saldos de tiqueteras')
        for days in (7,14,30):
            self.check(any(r['client_id']==single for r in admin.session_followup(days)),f'Seguimiento de sesiones a {days} días')
        self.check(isinstance(admin.membership_expiration_groups(),dict),'Bloques de vencimientos consultables')
        self.check(isinstance(admin.upcoming_expirations(),list),'Listado de próximos vencimientos')

        self.stage('Marketing, contactos y autorización')
        settings=admin.marketing_settings()
        admin.save_marketing_settings(dict(settings,whatsapp_enabled=False,warning_days=7))
        self.check(admin.marketing_settings()['warning_days']==7,'Guardar y recuperar configuración de marketing')
        admin.set_marketing_opt_in(ana,True)
        self.check(admin.marketing_contacts('Ana')[0]['whatsapp_opt_in'],'Consentimiento de contacto activado')
        admin.set_marketing_opt_in(ana,False)
        self.check(not admin.marketing_contacts('Ana')[0]['whatsapp_opt_in'],'Consentimiento revocado')
        self.check(admin.marketing_activity()==[],'La simulación no envía mensajes externos')

        self.stage('Excel, respaldos y restauración en un gimnasio aislado')
        with tempfile.TemporaryDirectory(prefix='gymsoft-simulacion-') as folder:
            folder=Path(folder)
            self.check(reception.register_checkin(bruno,'MANUAL')['already_consumed_today'],
                'Segunda visita no consume otra entrada antes de exportar')
            self.engine.sql('DELETE FROM public.checkins WHERE gym_id=$1 AND client_id=$2',[gid,bruno])
            self.check(admin.membership_snapshot(bruno)['entries_remaining']==14,
                'Borrar visitas conserva el saldo consumido')
            backup=admin.backup(folder/'respaldo.json')
            payload=json.loads(backup.read_text(encoding='utf-8'))
            self.check(payload['format']=='ZTATTUZ-CLOUD-1' and len(payload['tables']['clients'])==5,'Respaldo incluye los clientes de la jornada')
            excel=admin.export_excel(folder/'gimnasio.xlsx')
            prepared_excel=admin.prepare_excel_replacement(excel)
            self.check(prepared_excel['counts']['clients']==5,'Excel exportado se puede leer para importar')
            prepared=independent.prepare_technical_backup_replacement(backup)
            result=independent.replace_from_excel(prepared)
            self.check(bool(result) and len(independent.list_clients())==5,'Restaurar reconstruye clientes en el gimnasio destino')
            self.check(len(admin.list_clients())==5,'Restauración no cambia el gimnasio de origen')
            self.check(not ({c['id'] for c in admin.list_clients()} & {c['id'] for c in independent.list_clients()}),
                'Restauración genera identificadores nuevos para evitar mezclar gimnasios')
            self.check(len(independent.list_routines())==1 and len(independent.list_classes())==1,
                'Restauración reconstruye relaciones de rutinas y clases')
            broken=json.loads(json.dumps(prepared));broken['tables']['memberships'][0]['client_id']='NO-EXISTE'
            before=independent.list_clients()
            self.rejected(lambda:independent.replace_from_excel(broken),'Relación rota revierte toda la importación')
            self.check(independent.list_clients()==before,'Importación fallida conserva los registros anteriores')
            independent.replace_from_excel(prepared_excel)
            self.check(len(independent.list_clients())==5 and len(independent.list_store_sales())==1,
                'El Excel exportado restaura clientes y ventas mediante la operación real de importación')
            restored_bruno=next(c for c in independent.list_clients() if c['document']==bruno_data['document'])
            self.check(independent.membership_snapshot(restored_bruno['id'])['entries_remaining']==14,
                'Excel restaura el saldo aunque se haya borrado el historial de visitas')
            self.check(independent.register_checkin(restored_bruno['id'],'MANUAL')['already_consumed_today'],
                'Reentrada tras restaurar no vuelve a consumir el día ya pagado')
            imported_ticket=next(c for c in independent.list_clients() if c['document']==migrated_data['document'])
            self.check(independent.membership_snapshot(imported_ticket['id'])['entries_remaining']==8,
                'Exportar e importar Excel conserva las entradas iniciales consumidas')
            bad=folder/'invalido.json';bad.write_text('{',encoding='utf-8')
            self.rejected(lambda:admin.prepare_technical_backup_replacement(bad),'JSON corrupto rechazado antes de importar')

        self.stage('Permisos y cierre de jornada')
        self.rejected(lambda:self.rpc(reception_id,'session_followup',p_gym_id=gid,p_days=7),'Recepción no accede a estadísticas administrativas')
        self.rejected(lambda:self.rpc(reception_id,'create_reception_invite'),'Recepción no invita a otras cuentas')
        self.rejected(lambda:self.rpc(admin_id,'ticket_followup',p_gym_id=other_gid),'RPC rechaza consultar otro gimnasio')
        self.engine.sql('DELETE FROM public.gym_users WHERE user_id=$1',[reception_id])
        self.rejected(lambda:reception.list_clients(),'Cuenta desvinculada no puede operar')
        self.engine.sql("INSERT INTO public.gym_users(gym_id,user_id,role) VALUES($1,$2,'receptionist')",[gid,reception_id])
        self.check(len(reception.list_clients())==5,'Vinculación conserva los datos y recupera acceso')
        self.check(bool(self.engine.sql('SELECT id FROM public.audit_logs WHERE gym_id=$1',[gid])),'Jornada queda auditada')

    def report(self,error=None):
        self.output.parent.mkdir(parents=True,exist_ok=True)
        payload=dict(status='FAIL' if error else 'PASS',checks=self.checks,checks_passed=len(self.checks),
                     methods_exercised=sorted(self.methods),requests=len(self.engine.calls),
                     scope='Clases Python reales + PostgreSQL local con SQL y RLS de ZTATTUZ. Transporte PostgREST adaptado.',
                     external_pending=['Windows nativo y ejecutables instalados','Autenticación y correo reales',
                        'HTTP/PostgREST y Realtime en red','Lector físico','Envío externo de WhatsApp'])
        if error:payload.update(failed_section=self.section,error=str(error))
        self.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    simulation=Simulation(ROOT/'salida/validacion/simulacion_gimnasio.json')
    try:
        simulation.run()
    except Exception as error:
        simulation.report(error)
        raise
    else:
        simulation.report()
        print(f'PASS: {len(simulation.checks)} comprobaciones de una jornada con las clases Python y el SQL de ZTATTUZ reales.',flush=True)
    finally:simulation.engine.close()


if __name__=='__main__':main()
