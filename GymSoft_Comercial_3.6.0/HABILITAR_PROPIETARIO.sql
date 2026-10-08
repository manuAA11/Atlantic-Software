-- Ejecutar únicamente después de crear TU usuario en Authentication > Users.
-- Sustituye el correo antes de ejecutar. No hay contraseñas predeterminadas.
do $$
declare owner_email text := 'CAMBIA_POR_TU_CORREO'; owner_id uuid;
begin
 if owner_email='CAMBIA_POR_TU_CORREO' then raise exception 'Primero escribe el correo de tu cuenta propietaria.'; end if;
 select id into owner_id from auth.users where lower(email)=lower(trim(owner_email));
 if owner_id is null then raise exception 'Crea primero ese usuario en Authentication > Users.'; end if;
 insert into private.software_owners(user_id) values(owner_id) on conflict do nothing;
end $$;
