# Gym soft Comercial 3.3.0

Incluye Administración, Recepción y el panel privado del propietario, con las funciones anteriores, iconos GS, créditos y datos de contacto.

## Instalar o actualizar en Windows

1. Cierra las aplicaciones y extrae el ZIP completo en una carpeta nueva.
2. Ejecuta **CREAR_INSTALADORES.bat**. Requiere Python 3.13 de 64 bits e Inno Setup 6.
3. Instala `salida/GymSoft_Instalar_o_Actualizar_3.3.0.exe` para Administración y Recepción.
4. En tu computador de propietario, instala también `salida/GymSoft_Propietario_PRIVADO_3.3.0.exe`.

Entrega a los gimnasios únicamente el instalador de Administración y Recepción. El del propietario es privado. El ZIP contiene las fuentes y el generador; **no contiene ejecutables ya compilados**.

Supabase confirmó la aplicación de `ACTUALIZAR_TIQUETERAS_3.3.0.sql` al proyecto comercial `bawrakwhzkxmhmgkczqu`. No reinstales la base ni ejecutes `INSTALAR_BASE_NUEVA.sql`. La consulta final fue bloqueada por el límite de uso de la revisión automática. Se incluye `VERIFICAR_TIQUETERAS_3.3.0.sql`, de solo lectura, para comprobar manualmente los componentes instalados.

## Planes y tiqueteras

En **Administración → Configuración → Planes**, pulsa **Nuevo plan** o **Editar plan**.

- **Mensualidad / por días:** conserva el funcionamiento por días, sin límite de entradas.
- **Tiquetera / por entradas:** define el cupo, por ejemplo 15, 20 o 25 entradas. Elige **Meses calendario** y su cantidad, o conserva una vigencia por días.

Las ediciones se aplican a compras posteriores. Las tiqueteras vendidas conservan cupo y vencimiento. Los planes antiguos conservan sus días hasta que cambies su unidad.

La fecha final es inclusiva. Un mes desde el 1 de septiembre termina el 30 de septiembre. Se calcula la fecha equivalente del mes siguiente y se resta un día; si ese mes no tiene el mismo número de día, se usa su último día antes de restar uno. El formulario muestra el vencimiento previsto.

## Trasladar una tiquetera ya iniciada

En Administración o Recepción:

1. En **Clientes y pagos**, selecciona al cliente y pulsa **Registrar pago**.
2. Elige la tiquetera y escribe la fecha real de inicio.
3. Marca **Tiquetera ya iniciada (sin nuevo cobro)**.
4. Indica las **Entradas ya utilizadas**. Si tenía 20 y usó 7, escribe 7: quedan 13 y el próximo ingreso es el número 8.
5. Revisa el vencimiento y guarda.

El traslado no crea visitas ficticias ni suma otro pago: el valor queda en cero. No admite fechas futuras ni una membresía superpuesta. El propietario puede corregir después **Entradas utilizadas antes del traslado** en **Pagos y membresías**, indicando un motivo.

## Dashboard y seguimiento

Administración y Recepción muestran bloques de tiqueteras: **Sin entradas**, **1–5**, **6–10**, **11–15**, **16–20** y **Más de 20**. Cada cliente aparece una sola vez, según su tiquetera actual. Se incluyen clientes activos y tiqueteras vigentes por fecha; se excluyen sesiones individuales y tiqueteras futuras o vencidas. Al abrir un bloque puedes buscar, copiar el contacto, abrir la ficha o exportar el listado a CSV para Excel.

En **Administración → Estadísticas → Seguimiento de sesiones**, selecciona **Últimos 7, 14 o 30 días**. Son períodos acumulativos que incluyen hoy según la zona horaria del gimnasio. Se cuentan entradas permitidas reales y se incluyen quienes solo asistieron por sesión dentro del período: planes de una entrada o planes de un día sin cupo. Si también asistieron con una mensualidad o tiquetera, no aparecen en ese período.

Se muestra el teléfono, correo, número de sesiones, última sesión, plan actual y estado actual. Así puedes revisar si compraron otra membresía después. Copiar o exportar los datos sirve para tu seguimiento manual; la pantalla no envía mensajes.

## Recorrido para probar

1. Crea un cliente de prueba sin huella y escribe su nacimiento como DDMMYYYY. Las barras deben aparecer y el cursor debe avanzar sin usar las flechas.
2. Crea una tiquetera de 20 entradas y 2 meses.
3. Trasládala con su fecha de inicio y 7 entradas utilizadas: deben quedar 13.
4. Registra una entrada: deben quedar 12.
5. Abre el bloque **11–15 entradas** y prueba buscar y copiar el contacto.
6. Revisa el seguimiento de sesiones; estará vacío si no hay visitas que cumplan el filtro.
7. Reduce la ventana y comprueba los formularios con escala de Windows al 100 % y 125 %.

Se mantiene la huella opcional, lectura automática con lectores que escriben como teclado mientras Gym soft está activo, navegación reorganizada, modo oscuro y diseño adaptable con desplazamiento cuando el contenido excede el alto. La lectura se pausa en formularios; no controla directamente un torniquete ni captura entradas sobre otras aplicaciones.

Las pruebas locales pasaron. La instalación, los iconos de los ejecutables y el lector físico necesitan una prueba en Windows antes de distribuir el instalador a clientes.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
