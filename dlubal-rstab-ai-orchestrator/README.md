# Dlubal RSTAB AI Orchestrator

Este proyecto tiene como objetivo conectar la API de Dlubal RSTAB (via WebService o COM API) con un modelo de lenguaje grande (LLM) a través de la API de DeepSeek. La finalidad es interpretar instrucciones en lenguaje natural para realizar modificaciones en modelos estructurales, aplicar normativas de diseño mexicanas y generar reportes.

## Estructura del Proyecto

```
/dlubal-rstab-ai-orchestrator
├── .env                # Variables de entorno (DeepSeek API Key, config RSTAB) - NO SUBIR A GIT
├── .env.example        # Ejemplo de archivo .env
├── main.py             # Lógica principal de conexión e interacción
├── rstab_client.py     # Módulo para conectarse e interactuar con RSTAB
├── deepseek_ai.py      # Módulo para enviar prompts a DeepSeek y obtener respuestas
├── mexico_codes.py     # Módulo para reglas y datos de diseño estructural mexicano (NTC, CFE, AISC-LRFD, ACI 318)
├── templates/          # Plantillas para reportes (ej. PDF, DOCX)
├── outputs/            # Archivos generados automáticamente (reportes, logs, exportaciones)
├── requirements.txt    # Dependencias de Python
└── README.md           # Este archivo
```

## Configuración

### 1. Variables de Entorno (`.env`)
Crea un archivo `.env` en la raíz del proyecto (puedes copiar de `.env.example`) y completa las siguientes variables:

```ini
# DeepSeek API Configuration
DEEPSEEK_API_KEY="TU_DEEPSEEK_API_KEY_AQUI"

# Dlubal RSTAB Configuration
# Ajusta según tu método de conexión (WebService o COM) y tu entorno RSTAB.
# Ejemplo para WebService:
RSTAB_API_ENDPOINT="http://localhost:8081" # O la URL del servidor RSTAB
RSTAB_USERNAME="TU_USUARIO_RSTAB"         # Si es necesario para WebService
RSTAB_PASSWORD="TU_CONTRASENA_RSTAB"     # Si es necesario para WebService

# Ejemplo para identificar un archivo local (si se usa COM o para abrir archivos específicos con WebService):
# RSTAB_MODEL_FILE_PATH="C:/ruta/a/tu/modelo.rs9" # O .rs8, .glb, .igs, etc.

# Configuración regional o de normativas (opcional, para guiar a la IA)
DEFAULT_REGION_CODE="MX" # Ejemplo para México
```

### 2. Obtener API Key de DeepSeek
- Visita el sitio web oficial de [DeepSeek AI](https://www.deepseek.com/) (o su plataforma de desarrolladores).
- Regístrate o inicia sesión.
- Navega a la sección de API Keys en tu panel de control.
- Genera una nueva API Key.
- Copia esta clave y pégala en la variable `DEEPSEEK_API_KEY` de tu archivo `.env`.

### 3. Instalación del SDK/API de Dlubal RSTAB

La forma de interactuar con RSTAB dependerá de si utilizas su **WebService API** o su **COM API**.

**Opción A: WebService API**
- **Requisitos Previos**:
    - Asegúrate de que RSTAB esté configurado para exponer su WebService. Esto puede requerir una licencia específica o una configuración particular en RSTAB.
    - El WebService debe estar accesible desde la máquina donde se ejecuta este script (puede ser `localhost` o una URL de red).
- **Instalación**:
    - Generalmente no se requiere un SDK instalable aparte para Python, ya que la interacción se realiza mediante solicitudes HTTP (usando bibliotecas como `requests`).
    - Consulta la **documentación oficial de Dlubal** para conocer los endpoints específicos del WebService, los métodos de autenticación y los formatos de datos esperados.
    - Configura `RSTAB_API_ENDPOINT` en tu archivo `.env`.

**Opción B: COM API**
- **Requisitos Previos**:
    - Dlubal RSTAB debe estar instalado en la misma máquina Windows donde se ejecutará este script.
    - La API COM debe estar habilitada y registrada por la instalación de RSTAB.
- **Instalación (Python en Windows)**:
    - Necesitarás la biblioteca `pywin32`. Si no está en `requirements.txt`, puedes instalarla con:
      ```bash
      pip install pywin32
      ```
    - No se requiere una configuración de endpoint de red, pero `rstab_client.py` deberá ser adaptado para usar `win32com.client`.
    - Consulta la **documentación oficial de Dlubal** para ejemplos de scripting COM y los objetos/métodos disponibles.

### 4. Dependencias de Python
Instala las dependencias listadas en `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Uso

1.  **Configura tu archivo `.env`** como se describió anteriormente.
2.  **Asegúrate de que RSTAB esté disponible** (ya sea el WebService corriendo o RSTAB instalado localmente para COM).
3.  **Ejecuta el script principal**:
    ```bash
    python main.py
    ```
4.  **Interactúa con el sistema**:
    - El script `main.py` (una vez implementado) te permitirá ingresar instrucciones en lenguaje natural.

## Flujo de Trabajo Conceptual

1.  El usuario ingresa una instrucción en `main.py` (ej: *"Rediseñar vigas de acero con perfil IPR en acero A992 según LRFD 2021."*).
2.  `main.py` envía esta instrucción a `deepseek_ai.py`.
3.  `deepseek_ai.py` se comunica con la API de DeepSeek para:
    *   `interpret_prompt()`: Traducir la instrucción a un formato estructurado (ej. JSON) que defina acciones y parámetros.
    *   Opcionalmente, `suggest_design_change()`: Tomar la tarea interpretada y, usando conocimiento de `mexico_codes.py`, sugerir cambios específicos.
4.  La respuesta estructurada de DeepSeek regresa a `main.py`.
5.  `main.py` utiliza `rstab_client.py` para:
    *   `connect()`: Conectarse a RSTAB y abrir el modelo especificado.
    *   `get_structure_elements()`: Obtener información del modelo si es necesario.
    *   `apply_modification()`: Aplicar los cambios sugeridos por la IA al modelo RSTAB.
    *   `run_analysis()`: Ejecutar el cálculo/análisis en RSTAB.
    *   `export_results()`: Exportar resultados, memorias de cálculo o estados de diseño (ej. a JSON, CSV, PDF) a la carpeta `outputs/`.
6.  `mexico_codes.py` puede ser consultado por `deepseek_ai.py` para informar sus sugerencias o por `main.py` para validaciones adicionales.

## Ejemplos de Entradas y Salidas (Conceptuales)

### Ejemplo 1: Modificación de Perfil y Normativa

*   **Instrucción de Usuario (Entrada a `main.py`)**:
    ```
    "Quiero cambiar todas las vigas de acero existentes con sección 'IPE 240' a un perfil 'IPR 305' y verificar su diseño con acero A992 bajo la normativa LRFD AISC 2016."
    ```

*   **Interpretación de DeepSeek (`deepseek_ai.interpret_prompt()` → Salida JSON conceptual)**:
    ```json
    {
      "actions": [
        {
          "type": "modify_elements",
          "element_category": "member",
          "filter_by_current_section": "IPE 240",
          "new_properties": {
            "section_name": "IPR 305",
            "material_name": "A992"
          }
        },
        {
          "type": "set_design_code",
          "code_name": "AISC 360-16 LRFD",
          "apply_to": "all_steel_members"
        },
        {
          "type": "run_design_check",
          "check_type": "steel_design"
        },
        {
          "type": "export_report",
          "report_type": "steel_design_summary",
          "format": "pdf"
        }
      ]
    }
    ```

*   **Acciones en RSTAB (`rstab_client.py`)**:
    1.  Conectar a RSTAB, abrir modelo.
    2.  Identificar miembros con sección "IPE 240".
    3.  Modificar su sección a "IPR 305" y material a "A992".
    4.  Configurar la normativa de diseño de acero a AISC 360-16 LRFD.
    5.  Ejecutar el módulo de diseño de acero.
    6.  Exportar un resumen del diseño en PDF a `outputs/steel_design_summary_timestamp.pdf`.

*   **Salida (Archivo en `outputs/`)**:
    *   `steel_design_summary_timestamp.pdf` conteniendo el reporte de RSTAB.
    *   Posiblemente un archivo `model_modificado.rs9` (si se guarda el modelo).

### Ejemplo 2: Diseño de Nuevo Elemento

*   **Instrucción de Usuario**:
    ```
    "Añade una losa de concreto de 15 cm de espesor, f'c 250 kg/cm2, apoyada en las vigas V1, V2, V3 y V4. Considera una carga viva de 200 kg/m² según NTC-CDMX Cargas."
    ```

*   **Interpretación de DeepSeek (Salida JSON conceptual)**:
    ```json
    {
      "actions": [
        {
          "type": "create_element",
          "element_category": "surface",
          "properties": {
            "thickness_cm": 15,
            "material_concrete_fc_kgcm2": 250,
            "boundary_supports": ["V1", "V2", "V3", "V4"],
            "geometry_definition": "..." // Podría requerir más info o una etapa de clarificación
          }
        },
        {
          "type": "apply_load",
          "load_case_name": "Carga Viva Losa",
          "load_type": "surface_area_load",
          "magnitude_kgm2": 200,
          "target_elements": ["nueva_losa_id"],
          "code_reference": "NTC-CDMX Cargas y Criterios de Diseño Estructural"
        }
      ]
    }
    ```
    *(Nota: La IA podría necesitar más detalles para la geometría de la losa o solicitar una selección gráfica en RSTAB si la integración lo permite).*

*   **Salida**: Modelo RSTAB modificado, posible reporte de cargas.

## TODO / Próximos Pasos para el Desarrollador

*   **Implementar `rstab_client.py`**:
    *   Elegir el método de conexión (WebService o COM).
    *   Escribir la lógica detallada para `connect`, `get_structure_elements`, `apply_modification`, `run_analysis`, `export_results`.
    *   Manejar la autenticación y los errores de la API de RSTAB.
*   **Refinar `deepseek_ai.py`**:
    *   Mejorar los prompts del sistema para guiar a DeepSeek a generar JSON más precisos y útiles para `rstab_client.py`.
    *   Implementar un manejo robusto de errores y reintentos para las llamadas a la API de DeepSeek.
    *   Considerar el uso de técnicas de "few-shot prompting" o "fine-tuning" (si DeepSeek lo permite y es necesario) para mejorar la calidad de la interpretación.
*   **Poblar `mexico_codes.py`**:
    *   Añadir datos estructurados y funciones para las normativas mexicanas relevantes. Esto es crucial para que la IA pueda hacer sugerencias de diseño informadas y para validaciones.
*   **Desarrollar `main.py`**:
    *   Crear el flujo principal de la aplicación, incluyendo la interfaz de usuario (CLI o GUI simple).
    *   Orquestar las llamadas entre `deepseek_ai.py` y `rstab_client.py`.
    *   Manejar el estado de la aplicación y el feedback al usuario.
*   **Crear plantillas de reporte** en `templates/` si se desea generar reportes personalizados más allá de lo que RSTAB exporta directamente.
*   **Añadir pruebas unitarias e de integración.**

Este proyecto es ambicioso y requerirá un desarrollo iterativo. ¡Buena suerte!
```
