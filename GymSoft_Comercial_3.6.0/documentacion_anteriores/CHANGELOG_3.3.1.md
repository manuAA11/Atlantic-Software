# Gym soft Comercial 3.3.1

- Corrige el fallo de compilación «No cargaron usuarios e invitaciones» causado por una comprobación anterior al comienzo de la carga inicial.
- El editor inicia su consulta antes de mostrarse y mantiene los controles bloqueados mientras carga.
- La prueba gráfica espera la finalización de la carga, comprueba ambos correos y sus estados y verifica una respuesta retrasada sin conectarse a cuentas reales.
- Los errores de la prueba imprimen su traza original para facilitar el diagnóstico.
- Conserva las tiqueteras, el seguimiento de sesiones, la huella opcional, el diseño adaptable y las funciones anteriores. No requiere cambios SQL.
