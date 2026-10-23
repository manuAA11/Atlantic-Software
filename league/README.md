# Atlantic League

Aplicación personal iPhone/Android y módulo deportivo de la única aplicación Atlantic Gym. Desarrollo en **pruebas**; **main** conserva la versión oficial validada. Los adaptadores históricos identifican proveedores existentes, no aplicaciones distintas.

Esta fase contiene código ejecutable y pruebas. No se ha desplegado ninguna migración de League en los proyectos operativos. No acredita un piloto con clientes reales ni una instalación en iPhone.

## Ejecutar

Requisitos: Node 24, npm y una instalación de Expo compatible con SDK 58.

    cd league
    npm ci
    npm run typecheck
    npm test
    npm run mobile

La pantalla de acceso permite explorar una **demostración identificada con datos simulados** sin conexión con gimnasios. El modo real requiere copiar mobile/.env.example a mobile/.env y usar exclusivamente un hub, Core y proveedor de gimnasio aislados. Nunca colocar claves secretas en variables EXPO_PUBLIC_*.

## Contenido

| Ruta | Responsabilidad |
|---|---|
| mobile | React Native / Expo / TypeScript, acceso, planes, entrenamientos, clases, clasificaciones e historias |
| backend | Pasarela que valida cada JWT en el proveedor correspondiente y consulta la habilitación en Core |
| hub/supabase/migrations | Identidad deportiva independiente, vínculos autorizados, historial, XP y marcas |
| source/supabase/migrations | Adaptador aditivo sobre clientes, rutinas, ejercicios, clases y reservas existentes de Gym |
| core/supabase/migrations | Autorización opcional del módulo, independiente de pagos y licencias de Gym |
| tests | Integración SQL, HTTP, permisos, almacenamiento local, concurrencia PostgreSQL y recorrido de interfaz |
| ../common/league_ui.py | Administración integrada al UI Kit de Atlantic Gym |

Ver [arquitectura](docs/ARQUITECTURA.md), [instalación iPhone](docs/IPHONE.md), [despliegue y reversión](docs/DESPLIEGUE.md) y [estado y piloto](docs/ESTADO.md).

Las dependencias están fijadas y el lockfile se incluye. La licencia del punto de partida de Expo se conserva en mobile/LICENSE.
