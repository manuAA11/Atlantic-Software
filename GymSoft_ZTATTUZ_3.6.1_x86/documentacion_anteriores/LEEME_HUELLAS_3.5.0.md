# Gym soft y ZTATTUZ 3.5.0 · Huellas DigitalPersona

Entrega del 25 de septiembre de 2026. Lector: DigitalPersona U.are.U 4500. Plataforma de destino: Windows 10/11 de 64 bits.

## Qué incluye

- Integración directa con el lector USB; no requiere que el sensor escriba un código como teclado.
- Registro, reemplazo y eliminación de una huella por cliente desde Administración o Recepción.
- Plantillas biométricas en la base del gimnasio, compartidas entre sus equipos autorizados. No se guardan fotografías de los dedos ni archivos locales de plantillas.
- Identificación y solicitud de entrada automáticas sin enfocar el buscador. El servidor conserva la validación del plan, vencimiento, entradas y permisos.
- Control de lecturas repetidas y pausa durante formularios y operaciones con respuesta incierta.
- Componentes de ejecución y controlador DigitalPersona 3.4.0 x64 del paquete que proporcionaste, con su licencia original.
- Funciones anteriores, pruebas locales e informes de ambas ediciones.

Los ZIP contienen el código completo y el generador de instaladores. No contienen los ejecutables de Gym soft ya compilados. El instalador del fabricante incluido corresponde al componente DigitalPersona.

## 1. Generar los instaladores en tu computador

1. Extrae cada ZIP en una carpeta nueva. No mezcles las dos ediciones.
2. Usa Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6 en el computador donde compilas. Los equipos del gimnasio no necesitan estas herramientas.
3. Ejecuta `CREAR_INSTALADORES.bat` dentro de la carpeta elegida.
4. Mantén visibles las ventanas que abra la prueba gráfica y el escritorio desbloqueado hasta terminar. Las pruebas usan datos locales ficticios; no requieren lector USB ni controlador instalado.
5. Entrega el instalador correspondiente de la carpeta `salida`:

| Edición | Instalador que entregas al gimnasio |
| --- | --- |
| Gym soft Comercial | `GymSoft_Instalar_o_Actualizar_3.5.0.exe` |
| ZTATTUZ | `ZTATTUZ_Instalar_o_Actualizar_3.5.0.exe` |

`GymSoft_Propietario_PRIVADO_3.5.0.exe` es exclusivamente para tu computador. Conserva para ti el código fuente, los archivos SQL y las herramientas del propietario.

## 2. Estado de las bases de datos

**ZTATTUZ:** ya se aplicó y verificó la actualización de huellas en su proyecto. La tabla está vacía y tiene acceso restringido; no se registraron huellas de prueba ni se cambiaron clientes, pagos o asistencias reales. No necesitas volver a instalar la base.

**Gym soft Comercial:** el proyecto `bawrakwhzkxmhmgkczqu` estaba pausado al preparar esta entrega. Reactívalo en Supabase y ejecuta únicamente `ACTUALIZAR_HUELLAS_3.5.0.sql` en su SQL Editor. Mientras el proyecto esté pausado no podrá iniciar sesión ni sincronizar datos. El instalador sí puede generarse sin conectarse a ese servidor, una vez descargadas sus dependencias.

No ejecutes `INSTALAR_BASE_NUEVA.sql` en una base existente. Ese archivo, que ahora incluye las huellas, es solo para proyectos nuevos. Cada edición conserva su conexión propia: una huella de ZTATTUZ no se comparte con Gym soft Comercial ni con otro gimnasio.

## 3. Instalar en el gimnasio

1. Cierra Administración y Recepción antes de actualizar.
2. Ejecuta el instalador de la edición correspondiente.
3. Deja seleccionada la opción **Instalar el controlador y reconocimiento DigitalPersona** y completa el asistente del fabricante. Windows puede pedir permiso de administrador o reinicio. No hace falta conectar el lector para completar este paso.
4. Conecta el U.are.U 4500 por USB y abre Administración o Recepción con una cuenta del gimnasio.

Solo una aplicación puede controlar el mismo lector a la vez. Si Administración lo tiene reservado, ciérrala para usarlo desde Recepción. Puedes dejar otros equipos del gimnasio trabajando con sus propios lectores.

Windows 10 Mini debe ser de 64 bits y conservar los componentes necesarios para instalar y ejecutar el controlador. No se ha comprobado esta edición modificada de Windows con tu dispositivo; la validación física se hará en ese equipo después de instalar.

## 4. Registrar la primera huella

1. Crea o selecciona al cliente. El identificador de huella del formulario continúa siendo opcional y no sustituye el registro del dedo.
2. Abre **Registro de entrada → Huellas / lector**.
3. Selecciona el cliente en la lista y pulsa **Registrar / reemplazar**.
4. Confirma la persona y su autorización para registrar la huella.
5. Coloca el mismo dedo varias veces, levantándolo entre lecturas, hasta que aparezca **Huella registrada correctamente**.
6. Cierra la ventana de Huellas y deja activada la lectura automática.

Se conserva la huella anterior hasta confirmar el nuevo registro. Si cancelas o hay una lectura de mala calidad, puedes repetirlo. La huella de otra persona ya registrada se rechaza.

## 5. Uso automático y otros computadores

Con la aplicación abierta, la sesión iniciada, la lectura activada y conexión al servidor, colocar el dedo identificado solicita la entrada y muestra el resultado. No hace falta hacer clic en el buscador. Puede funcionar con otra aplicación al frente; los formularios modales y el registro de huellas pausan los accesos automáticos para evitar interferencias.

Para usar otro computador, instala la misma edición y DigitalPersona, conecta su lector e inicia sesión en el mismo gimnasio. No tienes que registrar de nuevo a los clientes. La lista se sincroniza periódicamente y se consulta nuevamente antes de identificar cada lectura. Eliminar una huella la retira del registro del gimnasio y de futuras comprobaciones en sus equipos.

Las plantillas no están incluidas en los Excel ni en los respaldos JSON operativos. Permanecen en la base del gimnasio. La aplicación no ofrece reconocimiento sin conexión ni mezcla plantillas de distintos gimnasios.

## 6. Si aparece un aviso

| Aviso | Qué hacer |
| --- | --- |
| Falta DigitalPersona Runtime x64 | En Huellas, pulsa **Instalar controlador DigitalPersona**. Completa el asistente y vuelve a abrir la aplicación. |
| Conecta el U.are.U 4500 | Revisa el cable USB y que el controlador esté instalado. La aplicación vuelve a intentar detectarlo. |
| El lector está activo en otra aplicación | Cierra la aplicación que está usando ese mismo lector. |
| Huella no reconocida | Levanta el dedo y vuelve a colocarlo; si aún no está registrada, regístrala para ese cliente. |
| Falta instalar ACTUALIZAR_HUELLAS_3.5.0.sql | El proveedor debe aplicar la actualización en el proyecto de esa edición. |
| No se pudo confirmar la sincronización | Revisa la conexión y el estado del proyecto. No se conceden entradas automáticas sin comprobar los datos. |
| No se pudo confirmar la entrada | Consulta el historial antes de reactivar la lectura; la petición pudo llegar al servidor. No se repite automáticamente. |

## Verificación de esta entrega

Pasaron las pruebas locales de ambas ediciones, incluidas la simulación de un gimnasio, los permisos SQL y la interfaz con lector simulado. Los resultados están en `salida/validacion` y `VERIFICACION_HUELLAS_3.5.0.md`.

Quedan pendientes la compilación e instalación nativas en Windows y la lectura, registro y comparación con tu U.are.U 4500 real. Las pruebas automáticas no sustituyen esa comprobación y no garantizan ausencia de todo error. No se exigirá conectar el lector para generar el instalador.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
Correo: manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
