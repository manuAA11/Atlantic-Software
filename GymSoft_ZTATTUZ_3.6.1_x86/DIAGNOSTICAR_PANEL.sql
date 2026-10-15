-- Diagnóstico de solo lectura para el SQL Editor del proyecto existente.
-- No consulta datos personales ni ejecuta RPCs, migraciones o escrituras.
-- La presencia de funciones no acredita permisos, rendimiento ni servicios externos.
with required_functions(component, signature, upgrade_file) as (
 values
 ('Listado de clientes', 'public.reception_list_clients(uuid,text)', 'Revisar la actualización base de la edición'),
 ('Reloj del gimnasio', 'public.gym_local_clock(uuid)', 'ACTUALIZAR_CONSUMO_DIARIO.sql'),
 ('Tiqueteras', 'public.ticket_followup(uuid)', 'Revisar la actualización base de tiqueteras de la edición'),
 ('Panel de membresías y STAFF', 'public.membership_population(uuid)', 'ACTUALIZAR_PLANES_INTERNOS.sql'),
 ('Editor de planes', 'public.save_membership_plan(uuid,jsonb,bigint,text)', 'ACTUALIZAR_PLANES_INTERNOS.sql'),
 ('Congelación', 'public.membership_freeze_info(uuid,bigint)', 'ACTUALIZAR_CONGELACION_Y_HORAS.sql'),
 ('Reanudación anticipada', 'public.membership_resume_preview(uuid,uuid)', 'ACTUALIZAR_REANUDACION_MEMBRESIAS.sql')
), required_columns(component, table_name, column_name, upgrade_file) as (
 values
 ('Consumo por día local', 'public.checkins', 'local_date', 'ACTUALIZAR_CONSUMO_DIARIO.sql'),
 ('Tipo de membresía', 'public.memberships', 'membership_type', 'ACTUALIZAR_PLANES_INTERNOS.sql'),
 ('Duración efectiva de congelación', 'public.membership_freezes', 'calculation_version', 'ACTUALIZAR_REANUDACION_MEMBRESIAS.sql')
), checks as (
 select component, to_regprocedure(signature) is not null as installed, upgrade_file
 from required_functions
 union all
 select component, exists (
  select 1 from pg_catalog.pg_attribute
  where attrelid=to_regclass(table_name) and attname=column_name and not attisdropped
 ), upgrade_file
 from required_columns
)
select component as componente,
 case when installed then 'PRESENTE' else 'FALTA' end as estado,
 case when installed then '' else upgrade_file end as revisar
from checks order by installed, component;
