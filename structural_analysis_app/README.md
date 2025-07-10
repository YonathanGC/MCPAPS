# Aplicación de Análisis Estructural con OpenSeesPy e IA

Esta aplicación permite realizar análisis estructurales básicos de vigas, incluyendo análisis estáticos (lineales y no lineales geométricos) y análisis modales, utilizando OpenSeesPy como motor de cálculo. También integra una API de IA (Gemini) para generar resúmenes descriptivos de los análisis estáticos.

## Características Principales

*   **Biblioteca de Materiales y Perfiles Mexicanos:** Incluye datos de ejemplo para concretos (NTC) y aceros (ASTM), así como perfiles estructurales comunes (IPR, CE). (Localizados en `data/`)
*   **Análisis Estático:**
    *   Lineal.
    *   No Lineal Geométrico (efectos P-Delta).
*   **Análisis Modal:** Cálculo de periodos y frecuencias naturales.
*   **Interfaz Gráfica de Usuario (GUI):** Desarrollada con Tkinter para una fácil entrada de parámetros y visualización de resultados.
*   **Visualización 3D:**
    *   Representación de la estructura original y deformada (para análisis estático) usando PyVista.
*   **Generación de Reportes:**
    *   Creación de reportes en PDF (con ReportLab) resumiendo los parámetros de entrada, resultados principales, y una imagen de la visualización 3D (para análisis estático).
*   **Integración con IA (Gemini):**
    *   Generación de resúmenes descriptivos de los resultados del análisis estático.
*   **Exportación de Modelo:**
    *   Exportación de la geometría del modelo (nodos y elementos) a formato DXF para interoperabilidad con software CAD/CAE como Robot Structural Analysis.

## Estructura del Proyecto

structural_analysis_app/
|-- data/                     # Archivos JSON para materiales y perfiles
|   |-- materials_mx.json
|   `-- profiles_ansi_mx.json
|-- exports/                  # Directorio para archivos DXF exportados (se crea automáticamente)
|-- reports/                  # Directorio para reportes PDF (se crea automáticamente)
|-- src/                      # Código fuente de la aplicación
|   |-- core_analysis.py      # Lógica principal de análisis con OpenSeesPy
|   |-- export_dxf.py         # Funcionalidad de exportación a DXF
|   |-- gemini_integration.py # Integración con la API de Gemini
|   |-- gui_app.py            # Interfaz gráfica de usuario (Tkinter)
|   |-- material_library.py   # Carga y gestión de la biblioteca de materiales/perfiles
|   |-- report_generator.py   # Generación de reportes PDF
|   `-- visualization.py      # Visualización 3D con PyVista
|-- tests/                    # Pruebas unitarias
|   `-- test_material_library.py
|-- AGENTS.md                 # Notas para agentes IA trabajando en este código
|-- README.md                 # Este archivo
`-- requirements.txt          # Dependencias de Python

## Configuración y Ejecución

### Prerrequisitos

*   Python 3.7 o superior.
*   PIP (manejador de paquetes de Python).
*   (Opcional pero recomendado) Un entorno virtual de Python (`venv` o `conda`).

### Instalación de Dependencias

1.  Clona este repositorio (o asegúrate de tener todos los archivos).
2.  Navega al directorio raíz `structural_analysis_app/`.
3.  (Opcional) Crea y activa un entorno virtual:
    ```bash
    python -m venv env
    source env/bin/activate  # En Linux/macOS
    # env\Scripts\activate   # En Windows
    ```
4.  Instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```

### Configuración de la API de Gemini (Opcional)

Para usar la funcionalidad de "Resumen con IA", necesitas una API Key de Google Gemini:

1.  Obtén una API Key desde [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Configura la variable de entorno `GOOGLE_API_KEY` con tu clave.
    *   Linux/macOS: `export GOOGLE_API_KEY="TU_API_KEY"`
    *   Windows (cmd): `set GOOGLE_API_KEY=TU_API_KEY`
    *   Windows (PowerShell): `$env:GOOGLE_API_KEY="TU_API_KEY"`

    Si no configuras la API Key, la aplicación funcionará pero el botón "Resumen con IA" estará deshabilitado o mostrará un error si se intenta usar.

### Ejecución de la Aplicación

Desde el directorio raíz `structural_analysis_app/`, ejecuta la aplicación GUI con:

```bash
python -m src.gui_app
```

## Uso

1.  **Parámetros de Entrada:**
    *   **Longitud de la Viga (mm):** Longitud total de la viga.
    *   **Perfil:** Selecciona un perfil estructural de la lista (cargada desde `profiles_ansi_mx.json`).
    *   **Material:** Selecciona un material de la lista (cargada desde `materials_mx.json`).
    *   **Carga Puntual Central (N):** Magnitud de la carga (negativa para carga hacia abajo).
    *   **Escala Deformación (Visualización):** Factor para escalar la deformada en la visualización 3D.
    *   **No Linealidad Geométrica (P-Delta):** Marcar para incluir efectos P-Delta en el análisis estático.
    *   **Número de Modos (Análisis Modal):** Especifica cuántos modos calcular en el análisis modal.
2.  **Tipos de Análisis:**
    *   **Análisis Estático:** Calcula desplazamientos y reacciones para la carga dada. Puede ser lineal o P-Delta.
    *   **Análisis Modal:** Calcula periodos y frecuencias naturales de la viga. (Asegúrate que el material seleccionado tenga `unit_weight_kn_m3` definido).
3.  **Post-Proceso (después de un análisis estático exitoso):**
    *   **Visualizar 3D (Estático):** Muestra el modelo original y deformado.
    *   **Reporte PDF (Estático):** Genera un PDF con los detalles del análisis. Se guarda en la carpeta `reports/`.
    *   **Resumen IA (Estático):** Genera un resumen descriptivo usando Gemini (requiere API Key).
    *   **Exportar DXF (Estático):** Exporta la geometría del modelo a un archivo DXF. Se guarda en la carpeta `exports/`.

## Contribuir (Notas para Desarrolladores)

*   El código está estructurado en módulos dentro de `src/`.
*   Las pruebas unitarias se encuentran en `tests/`. Ejecutar con `python -m unittest discover tests`.
*   Consulta `AGENTS.md` para directrices específicas si eres un agente IA.

## Limitaciones y Futuro Trabajo

*   Actualmente modela solo una viga simple con carga puntual central.
*   La biblioteca de materiales/perfiles es de ejemplo y debería expandirse.
*   La exportación a IFC para Revit no está implementada.
*   El análisis dinámico (respuesta sísmica, historia en el tiempo) es una futura línea de trabajo.
*   No se incluyen elementos finitos complejos (losas, muros).
*   La visualización de formas modales no está implementada.

---
Hecho con la ayuda de un asistente IA.
