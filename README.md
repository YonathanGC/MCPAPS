# Servidor MCP Avanzado con FastMCP

Este proyecto implementa un servidor MCP (Model Context Protocol) utilizando la biblioteca FastMCP 2.0. El servidor incluye funcionalidades de autenticación OAuth 2.0, gestión de datos completa y automatización de diseño CAD.

## Características Principales

*   **OAuth 2.0 con Caché Automático:**
    *   Flujo de autorización estándar (Authorization Code Grant).
    *   Renovación automática de tokens de acceso.
    *   Almacenamiento seguro en caché local de tokens (cifrado con Fernet).
    *   Manejo de expiración de tokens con margen de seguridad.
    *   Endpoint de callback HTTP para el flujo OAuth.
*   **Data Management Completo:**
    *   Descarga de archivos desde el servidor MCP (soporte para versiones).
    *   Subida de nuevas versiones de archivos.
    *   Listado de archivos con paginación automática (límite de 100 registros por defecto).
    *   Manejo robusto de errores de API y de red.
*   **Design Automation:**
    *   Arquitectura para modificación de archivos CAD mediante motores personalizables.
    *   Soporte para diferentes tipos de motores CAD (ejemplo con un motor basado en script externo).
    *   Ejecución de workflows de diseño personalizables definidos en JSON, con múltiples pasos.
*   **Configuración Profesional:**
    *   Carga de configuración desde variables de entorno y archivos `.env`.
    *   Logging detallado y configurable (nivel, formato, salida a archivo o consola).
    *   Modo de testing para configuraciones específicas de prueba.
    *   Estructura para tests automatizados (ejemplo con tests unitarios para el cliente OAuth).

## Estructura del Proyecto

```
.
├── .env                        # Archivo de ejemplo para variables de entorno (debe ser creado y configurado)
├── cache.key                   # Clave de cifrado para el caché de tokens (generada automáticamente)
├── token_cache.enc             # Caché de tokens cifrados (generado automáticamente)
├── main_server.py              # Punto de entrada principal, define y ejecuta el servidor FastMCP.
├── oauth_client.py             # Lógica para el cliente OAuth 2.0.
├── data_manager.py             # Lógica para la gestión de datos (subida, descarga, listado).
├── design_automation_engine.py # Lógica para la automatización de diseño (motores, workflows).
├── server_config.py            # Carga y gestión de la configuración del servidor.
├── mock_cad_script.py          # Script de ejemplo usado por el motor CAD de demostración.
├── tests/                      # Directorio para tests automatizados.
│   ├── __init__.py
│   └── test_oauth_client.py    # Tests unitarios para oauth_client.py.
├── README.md                   # Este archivo.
└── LICENSE                     # Licencia del proyecto (si aplica).
```

## Requisitos Previos

*   Python 3.8 o superior.
*   Un proveedor OAuth 2.0 configurado (ej. Google, Auth0, Keycloak, etc.) con credenciales de cliente (Client ID, Client Secret) y un Redirect URI registrado.
*   (Opcional) Un servidor MCP real o simulado que exponga una API de datos para las funcionalidades de `DataManager`.
*   (Opcional) Software CAD o scripts necesarios para los motores de `DesignAutomationService` que se implementen.

## Instalación de Dependencias

1.  **Clona el repositorio (si aplica):**
    ```bash
    git clone <url-del-repositorio>
    cd <directorio-del-proyecto>
    ```

2.  **Crea y activa un entorno virtual (recomendado):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Linux/macOS
    # .venv\Scripts\activate    # En Windows
    ```

3.  **Instala las dependencias de Python:**
    El proyecto usa `pip` para gestionar las dependencias. Las dependencias principales son `fastmcp`, `uvicorn`, `requests`, `cryptography`, `python-dotenv`, y `starlette` (opcional para el callback OAuth HTTP). Estas se instalan al seguir los pasos de ejecución o al configurar el entorno. Si hubiera un `requirements.txt`, se usaría:
    ```bash
    # pip install -r requirements.txt
    # Por ahora, las dependencias se listan implícitamente y se instalan según necesidad
    # o se pueden instalar manualmente:
    pip install "fastmcp>=2.0" uvicorn requests cryptography python-dotenv starlette
    ```

## Configuración

1.  **Crea el archivo `.env`:**
    Copia o renombra `.env.example` a `.env` (si existiera un `.env.example`, de lo contrario créalo). Si no existe un `.env.example`, puedes crear un archivo `.env` vacío y llenarlo según el siguiente ejemplo.
    Este archivo contendrá las variables de entorno necesarias.

    Un ejemplo de contenido para `.env`:
    ```dotenv
    # --- Configuración General ---
    APP_ENV=development # development, production, o testing
    LOG_LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR, CRITICAL
    # LOG_FILE=server.log # Descomentar para loguear a un archivo

    # --- Servidor FastMCP ---
    SERVER_HOST=127.0.0.1
    SERVER_PORT=8080

    # --- OAuth 2.0 Client ---
    OAUTH_CLIENT_ID="TU_CLIENT_ID_DE_OAUTH"
    OAUTH_CLIENT_SECRET="TU_CLIENT_SECRET_DE_OAUTH"
    OAUTH_AUTH_URL="URL_DE_AUTORIZACION_DE_TU_PROVEEDOR_OAUTH" # Ej: https://accounts.google.com/o/oauth2/v2/auth
    OAUTH_TOKEN_URL="URL_DE_TOKEN_DE_TU_PROVEEDOR_OAUTH"     # Ej: https://oauth2.googleapis.com/token
    # Asegúrate que este Redirect URI esté registrado en tu proveedor OAuth y coincida con el servidor.
    OAUTH_REDIRECT_URI="http://localhost:8080/oauth/callback"
    # TOKEN_CACHE_KEY_FILE="cache.key" # Opcional, default es cache.key

    # --- Data Management API ---
    # URL base de la API de datos de tu servidor MCP.
    MCP_DATA_API_BASE_URL="URL_BASE_DE_TU_API_DE_DATOS_MCP" # Ej: http://mi-servidor-mcp.com/api/v1/data

    # --- Design Automation (Ejemplo para MockEngine) ---
    # Ruta al script que usará el ExampleScriptEngine (MyPythonCADTool)
    # Puede ser una ruta absoluta o relativa al directorio donde se ejecuta main_server.py
    MOCK_ENGINE_SCRIPT_PATH="./mock_cad_script.py"
    MOCK_ENGINE_INTERPRETER="python" # O la ruta completa al intérprete de Python
    MOCK_ENGINE_FORMATS="step,iges,stl,any"
    MOCK_ENGINE_TIMEOUT="300" # Segundos
    ```

2.  **Completa las variables de entorno:**
    Edita el archivo `.env` y rellena los valores correspondientes, especialmente las credenciales de OAuth y la URL de la API de datos MCP.

## Ejecución del Servidor

Con el entorno virtual activado y las dependencias instaladas:

```bash
python main_server.py
```

El servidor se iniciará en la dirección y puerto especificados en la configuración (por defecto `http://127.0.0.1:8080`).
Podrás acceder a la UI de FastMCP (Swagger/OpenAPI) en `http://127.0.0.1:8080/docs` para ver y probar las herramientas expuestas.

## Flujo de Autenticación OAuth (Ejemplo)

1.  **Obtener la URL de Autorización:**
    El cliente (o el usuario a través de una UI) necesitará iniciar el flujo. Si el servidor FastMCP expusiera una herramienta para esto, o si tuvieras un cliente que la genere, llamarías a `oauth_client_instance.get_authorization_url(scope="tu_scope")`.
    Por ahora, el `main_server.py` no expone directamente una herramienta para *iniciar* el flujo OAuth, pero el `oauth_client.py` tiene un bloque `if __name__ == "__main__"` que puede usarse manualmente para obtener la URL si se configura con las variables de entorno.

2.  **Autorización del Usuario:**
    El usuario visita la URL de autorización en su navegador, se autentica con el proveedor OAuth y autoriza a la aplicación.

3.  **Callback al Servidor:**
    El proveedor OAuth redirige al usuario al `OAUTH_REDIRECT_URI` configurado (ej. `http://localhost:8080/oauth/callback`). El servidor FastMCP (si `starlette` está instalado y el endpoint está activo) manejará este callback.

4.  **Intercambio de Código por Token:**
    El manejador del callback en `main_server.py` recibe el código de autorización y lo intercambia por un token de acceso (y un token de refresco) usando `oauth_client_instance.exchange_code_for_token()`.

5.  **Almacenamiento del Token:**
    El `OAuthClient` guarda el token de forma segura en el archivo `token_cache.enc`.

A partir de este punto, las herramientas del servidor que requieren autenticación (como las de `DataManager`) podrán obtener el token de acceso a través de `oauth_client_instance.get_access_token()`.

## Ejecución de Tests

Para ejecutar los tests unitarios (actualmente implementados para `oauth_client.py`):

```bash
python -m unittest tests.test_oauth_client -v
```

O para descubrir y ejecutar todos los tests en el directorio `tests/`:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Consideraciones y Mejoras Futuras

*   **Asincronía Completa:** Los módulos `oauth_client`, `data_manager`, y `design_automation_engine` son actualmente síncronos. Para un rendimiento óptimo en producción con FastMCP (que es asíncrono), deberían ser refactorizados para usar `async/await` con bibliotecas como `httpx` (para peticiones HTTP) y `aiofiles` (para operaciones de E/S de archivos). Las tareas de larga duración (como los workflows CAD) deberían delegarse a un sistema de colas de tareas (ej. Celery, RQ).
*   **Seguridad de Endpoints de Archivos:** Las herramientas `download_mcp_file` y `upload_mcp_file` actualmente toman rutas de archivo como parámetros (`destination_path`, `file_path`). Esto es inseguro para un servidor expuesto y debería ser rediseñado (ej. subidas a un área de staging controlada, descargas desde ubicaciones seguras o streaming directo del contenido).
*   **Gestión de Estado OAuth:** La validación del parámetro `state` en el callback OAuth es crucial para prevenir ataques CSRF y requeriría una gestión de sesión si el servidor es accedido por múltiples usuarios a través de una UI.
*   **Configuración Avanzada de Motores CAD:** La carga de configuración para los motores de Design Automation es básica. Un sistema más dinámico (ej. plugins, archivos de configuración YAML/JSON dedicados) sería más flexible.
*   **Pruebas de Integración:** Implementar tests de integración que verifiquen la interacción entre todos los componentes y con servicios externos (aunque sean mockeados).
*   **Empaquetado y Despliegue:** Considerar el uso de Docker para empaquetar la aplicación y sus dependencias para un despliegue más sencillo y consistente.

## Contribuir

(Sección estándar de contribución: cómo reportar bugs, proponer features, pull requests, etc. - si aplica)

## Licencia

(Especificar la licencia del proyecto aquí - si aplica)
