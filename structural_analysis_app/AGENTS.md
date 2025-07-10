# Notas para Agentes IA sobre el Proyecto de Análisis Estructural

Este documento proporciona directrices y contexto para agentes IA que trabajen en este codebase.

## Convenciones Generales

*   **Lenguaje:** Python 3.
*   **Estilo de Código:** Seguir PEP 8 قدر الإمكان. Usar formateadores como Black o Autopep8 es bienvenido.
*   **Comentarios:** Añadir comentarios claros para lógica compleja o decisiones de diseño no obvias. Docstrings para módulos, clases y funciones públicas.
*   **Manejo de Errores:** Usar excepciones de Python para errores y proporcionar mensajes descriptivos. En la GUI, usar `messagebox` para informar al usuario.
*   **Unidades:** El sistema de unidades interno para OpenSees es N, mm, s. Las conversiones desde otras unidades (ej. de los JSON o entrada del usuario) deben ser explícitas.
*   **Modularidad:** Mantener los módulos con responsabilidades claras (ej. `core_analysis` para OpenSees, `gui_app` para Tkinter, etc.).

## Estructura del Proyecto

Revisa el `README.md` para la descripción de la estructura de directorios y archivos.

## Trabajar con Módulos Específicos

*   **`core_analysis.py`:**
    *   Contiene la lógica de interacción con `openseespy`.
    *   Cualquier nueva funcionalidad de análisis (estático, dinámico, modal) debe implementarse aquí.
    *   Las funciones deben ser lo más puras posible, tomando datos y devolviendo resultados, minimizando efectos secundarios (excepto llamadas a `ops`).
    *   Siempre llamar a `ops.wipe()` al inicio de una función de análisis principal para evitar interferencias entre modelos.
    *   Asegurar que los tags de nodos, materiales, transformaciones, etc., sean únicos dentro del alcance de una función de análisis. Considerar el uso de offsets o rangos para tags si se combinan múltiples funciones de construcción de modelos.
*   **`gui_app.py`:**
    *   Maneja la interacción con el usuario.
    *   Debe llamar a las funciones de `core_analysis.py` para los cálculos.
    *   Las validaciones de entrada del usuario deben realizarse aquí antes de pasar datos al backend.
    *   Actualizar el área de texto de resultados de forma clara.
    *   Habilitar/deshabilitar botones de post-proceso según el estado del análisis.
*   **`material_library.py`:**
    *   Encapsula la carga de datos de materiales y perfiles desde archivos JSON.
    *   Si se añaden nuevas propiedades a los JSON, actualizar las funciones de acceso si es necesario.
    *   **Importante para empaquetado:** Este módulo (y cualquier otro que cargue archivos de `data/`) necesitará usar una función como `resource_path` (descrita abajo) para localizar correctamente los archivos de datos cuando la aplicación esté empaquetada (ej. con PyInstaller).
*   **`visualization.py`, `report_generator.py`, `export_dxf.py`:**
    *   Estos módulos toman los resultados del análisis (especialmente `visualization_data` o el diccionario completo de resultados) para generar sus respectivas salidas.
    *   Deben ser independientes de la lógica de OpenSees directamente.
*   **`gemini_integration.py`:**
    *   Maneja la comunicación con la API de Google Gemini.
    *   Asegurar que la API Key no se exponga en el código.
    *   Los prompts deben ser claros y proporcionar suficiente contexto para que la IA genere respuestas útiles.

## Pruebas

*   Las pruebas unitarias para `material_library.py` están en `tests/test_material_library.py`.
*   Se deben añadir más pruebas unitarias para otras lógicas de negocio (ej. funciones de conversión de unidades, generación de prompts, etc.).
*   Probar la GUI manualmente es esencial para verificar la interacción y el flujo de trabajo.

## Futuras Mejoras y Consideraciones

*   **Modelo de Objetos:** Para geometrías más complejas, considerar un modelo de objetos simple para representar la estructura (Nodos, Elementos, Materiales, Secciones, Cargas, etc.) que pueda ser construido por la GUI y luego traducido a comandos de OpenSees.
*   **Gestión de Unidades:** Implementar un sistema de gestión de unidades más formal.
*   **Logging:** Reemplazar `print()` con el módulo `logging`.
*   **Empaquetado:** Ver sección de empaquetado abajo.

## Empaquetado (Notas Adicionales)

*   **PyInstaller:** Es una buena opción para crear ejecutables standalone para Windows, Linux y macOS.
    *   Comando básico: `pyinstaller --name StructuralAnalysisApp --onefile --windowed src/gui_app.py`
    *   **Archivos de Datos (`data/`, `*.json`):** PyInstaller no incluye automáticamente archivos de datos no Python. Se deben especificar usando la opción `--add-data`.
        *   Ejemplo: `pyinstaller --add-data "data/*.json:data"` (si estás ejecutando PyInstaller desde `structural_analysis_app/`)
        *   O más explícito: `pyinstaller --add-data "structural_analysis_app/data/*.json:data"` (si ejecutas desde el padre de `structural_analysis_app`)
    *   **Resolución de Rutas para Datos Empaquetados:** El código que accede a estos archivos (ej. `MaterialLibrary`, `ReportGenerator` para plantillas si las tuviera) usa actualmente rutas relativas como `os.path.join(os.path.dirname(__file__), '..', 'data')`. Cuando se empaqueta con PyInstaller (especialmente con `--onefile`), `__file__` puede no comportarse como se espera. Se necesita una función para resolver la ruta de los datos en tiempo de ejecución, tanto para desarrollo como para el ejecutable empaquetado. Una solución común es:
        ```python
        import sys # Necesario
        import os  # Necesario

        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                # _MEIPASS contiene la ruta a la carpeta temporal donde PyInstaller ha desempaquetado todo.
                base_path = sys._MEIPASS
            except Exception:
                # sys._MEIPASS no está definido, así que estamos en modo desarrollo (no empaquetado)
                # Asumimos que el script que llama a resource_path está en 'src/'
                # y los datos están en 'data/' al mismo nivel que 'src/', dentro de 'structural_analysis_app/'
                # Por lo tanto, subimos un nivel desde 'src' para llegar a 'structural_analysis_app'
                # y luego añadimos la ruta relativa.
                base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

            return os.path.join(base_path, relative_path)

        # Ejemplo de uso en material_library.py:
        # DATA_PATH_BASE = resource_path("data") # Esto apuntaría a structural_analysis_app/data
        # MATERIALS_FILE = os.path.join(DATA_PATH_BASE, 'materials_mx.json')
        # PROFILES_FILE = os.path.join(DATA_PATH_BASE, 'profiles_ansi_mx.json')
        ```
        Esta función `resource_path` debería añadirse a un módulo de utilidades o al inicio de los scripts que cargan archivos de datos (como `material_library.py`) y usarse para definir las rutas a los JSON. La clave es que `relative_path` para `resource_path` debe ser relativa al `base_path` (que es la raíz del proyecto o `_MEIPASS`).
    *   **Icono:** Se puede añadir un icono con `--icon=myicon.ico` (o `.icns` para macOS).
    *   **Dependencias Ocultas:** A veces PyInstaller no detecta todas las dependencias (especialmente de paquetes científicos como `numpy`, `pandas`, o las de `openseespy`). Se pueden añadir con `--hidden-import=nombre_modulo`. `openseespy` puede requerir atención especial; revisa su documentación para problemas comunes de empaquetado. Algunas bibliotecas como `pyvista` pueden traer muchas dependencias gráficas que también necesitan ser manejadas.
    *   **Consola:** Si se usa `--windowed` (para aplicaciones GUI), la salida de `print` no será visible. Para depuración, se puede omitir `--windowed` o usar `--noconsole` (en Windows) versus `--nowindowed` (en macOS/Linux) según se necesite.
*   **cx_Freeze:** Otra alternativa popular a PyInstaller.

---
Mantener este archivo actualizado con cualquier nueva convención o decisión de diseño importante.
```
