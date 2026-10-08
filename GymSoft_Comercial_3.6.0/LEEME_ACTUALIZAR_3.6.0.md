# Gym soft Comercial 3.6.0

Actualización de presentación y controles. Las casillas usan marcas blancas, con estados de selección y teclado conservados. Los avisos tienen iconos dibujados, texto alineado y acciones consistentes; las pestañas y botones siguen el tema oscuro. El acceso inicial muestra «Iniciar sesión» y «Crear cuenta».

## Instalar o actualizar

1. Cierra Administración y Recepción, y el panel del propietario.
2. Extrae este ZIP completo en una carpeta nueva.
3. En el computador donde generas instaladores, ejecuta `CREAR_INSTALADORES.bat`. Utiliza Python 3.13 de 64 bits, Inno Setup 6 y Node.js LTS para las pruebas locales; los archivos de preparación incluidos comprueban las dependencias.
4. Espera a que las comprobaciones terminen. No necesitas conectar el lector ni el relé. Las pruebas gráficas abren ventanas: mantén el escritorio desbloqueado y las pruebas visibles.
5. En `salida`, ejecuta `GymSoft_Instalar_o_Actualizar_3.6.0.exe`. Sirve para instalar y actualizar Administración y Recepción.

El panel privado se instala con `salida/GymSoft_Propietario_PRIVADO_3.6.0.exe`, solo en el equipo del propietario. **Esta edición no incluye control de relé ni apertura de puerta.**

## Datos y comprobaciones

No necesitas SQL nuevo para actualizar desde 3.5.3. Esta entrega no cambia la base real, los permisos, los pagos, los clientes ni las plantillas biométricas. Se mantienen las correcciones de distribución estable y márgenes en Registro de entrada.

El ZIP contiene código y el generador de instaladores, no ejecutables Windows precompilados. La entrega se verifica en Linux con Tk real y PostgreSQL local; lector y relé simulados. El informe `VERIFICACION_3.6.0.md` detalla lo que se probó y lo pendiente. La compilación en Windows conserva sus controles de errores. La instalación y el hardware físico deben comprobarse en el equipo del gimnasio; las pruebas automáticas no garantizan que cualquier dispositivo o versión modificada de Windows funcione sin incidencias.

© 2026 Manuel Cuéllar. All rights reserved.
