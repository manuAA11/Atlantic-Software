# Gym soft Comercial 3.4.5

Esta entrega mantiene la distribución de la vista maximizada también en la ventana mediana y corrige los espacios interiores que dejaba la reorganización de paneles. Incluye Administración, Recepción y el panel privado del propietario.

## Actualizar

1. Cierra las tres aplicaciones.
2. Extrae `GymSoft_Comercial_3.4.5_COMPLETO.zip` en una carpeta nueva.
3. Ejecuta `CREAR_INSTALADORES.bat`. Se requieren Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6. El script reconoce Python aunque el comando `py` no esté disponible.
4. Durante las pruebas gráficas, deja el escritorio desbloqueado y sus ventanas visibles. La prueba mueve y restaura sus propias ventanas; espera a que termine antes de abrir otras aplicaciones que puedan taparlas.
5. Instala `salida/GymSoft_Instalar_o_Actualizar_3.4.5.exe` para Administración y Recepción.
6. Instala `salida/GymSoft_Propietario_PRIVADO_3.4.5.exe` únicamente en tu computador.

**No ejecutes SQL para actualizar desde 3.4.x.** Esta revisión no cambia los datos, las tablas, las funciones del servidor ni los permisos.

El ZIP contiene las fuentes y el generador de instaladores. Los ejecutables deben compilarse en Windows.

## Distribución y espacio disponible

- El Dashboard conserva cuatro columnas en sus indicadores, acciones rápidas y rangos de vencimiento. Las tiqueteras conservan dos filas de tres bloques; los cumpleaños, una fila de tres.
- Restaurar o maximizar ajusta el ancho disponible sin convertir esas filas en bloques apilados.
- Los paneles conservan sus proporciones y su capacidad de ocupar el alto disponible. En Estadísticas, el gráfico y la tabla crecen hasta los indicadores inferiores, sin el hueco intermedio.
- La corrección compartida se aplica a las páginas y formularios que utilizan el sistema de distribución de Administración, Recepción y Propietario.
- Los encabezados no reservan una fila vacía para el estado de carga. Los avisos aparecen junto al título, y las barras de acciones conservan la alineación de sus etiquetas y botones.
- Los textos se ajustan dentro de su espacio. Si la ventana resulta demasiado estrecha para conservar controles legibles, aparece desplazamiento horizontal; el vertical se muestra cuando falta altura. Las tablas mantienen su propio desplazamiento.
- Mover la ventana o desplazar contenido estable no vuelve a distribuir sus tarjetas. Se conservan los controles existentes y la caché de sus anchos mínimos.

Se mantienen Recepción sin Dashboard, la huella opcional, la lectura automática, las tiqueteras editables y todas las funciones de la entrega 3.4.4. También permanecen las correcciones de pagos, consultas en segundo plano, reintento de acceso e importes.

## Comprobación

La batería incluye una prueba de columnas estables y de ocupación del alto disponible al 100 %, 120 % y 125 %, además del recorrido de páginas, formularios y pestañas. `VALIDACION_3.4.5.md` detalla la ejecución local y sus límites.

`SIMULAR_GIMNASIO.bat` permite volver a ejecutar las pruebas con datos ficticios. Los resultados se guardan en `salida/validacion`. La compilación exige que todas las etapas pasen; si alguna falla, conserva esa carpeta para diagnosticarlo.

La validación local utiliza un escritorio virtual de Linux. La apariencia y la fluidez del EXE deben comprobarse en Windows con la escala y los monitores de uso. La prueba nativa del lector y de la conexión real entre equipos también se realiza allí.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
