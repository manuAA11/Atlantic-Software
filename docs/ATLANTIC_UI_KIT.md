# Atlantic UI Kit · Multi-Gym

La fuente visual aprobada es el diseño existente de Gym Soft. El kit centraliza sus colores en `common/atlantic_ui.py`; conserva sidebar, tarjetas, tablas, formularios, botones, diálogos, controles de fecha/importe, espaciado, tamaños, estados y navegación en sus componentes existentes. Cada edición conserva una copia independiente del módulo compartido para poder distribuirse sin importar desde otra carpeta.

La guía visual que el usuario adjuntó el 8 de octubre de 2026 define el icono G azul para Atlantic Gym Administrador y el G cian para Atlantic Gym Recepción. ZTATTUZ conserva su identificación como gimnasio, funciones específicas y nombres/IDs históricos de instalación; pertenece a la misma familia visual Atlantic.

Se usa `.AppleSystemUIFont` en macOS y Segoe UI en Windows. No se distribuye SF Pro. En Linux se conserva Arial/fallback del sistema para las pruebas de Tk. La firma aparece de forma secundaria en login/configuración; no añade detalles técnicos al flujo del cliente.

Los colores del kit son los valores existentes del producto aprobado. Los nuevos iconos corresponden a la referencia entregada por el usuario. Las imágenes de los iconos no son pruebas de ejecución de Windows; la inserción y los accesos directos requieren validación del instalador en Windows.

Antes de cambiar componentes o crear una pantalla, revisar `AGENTS.md` y reutilizar el kit. El diseño no debe modificar reglas de acceso ni calcular estados sensibles; utiliza las respuestas del servidor.
