# Servidor MCP para Deepseek con Autenticación Autodesk

Este proyecto implementa un servidor FastMCP que expone herramientas para interactuar con la API de Deepseek, con un flujo de autenticación OAuth 2.0 para Autodesk Platform Services.

## Características

*   Servidor FastMCP básico.
*   Herramienta para llamar a la API de chat de Deepseek.
*   Flujo de autenticación OAuth 2.0 (Authorization Code Grant) con Autodesk Platform Services.
    *   Endpoint para iniciar el login con Autodesk.
    *   Endpoint de callback para recibir el código de autorización e intercambiarlo por un token de acceso.
*   Herramienta para verificar el estado de autenticación de Autodesk.
*   Herramienta para llamar a Deepseek API proveyendo contexto de la autenticación de Autodesk (con advertencias de seguridad sobre el manejo de tokens).

## Requisitos Previos

*   Python 3.8+
*   Una cuenta de desarrollador de Autodesk Platform Services y una aplicación configurada con:
    *   `Client ID`
    *   `Client Secret`
    *   `Callback URL` (URI de redirección) apuntando a `http://127.0.0.1:8000/autodesk/callback` (o la URL donde se ejecute el servidor + `/autodesk/callback`).
*   Una clave API de Deepseek.

## Configuración

1.  **Clonar el repositorio (si aplica):**
    ```bash
    # git clone <url-del-repositorio>
    # cd <directorio-del-repositorio>
    ```

2.  **Instalar dependencias:**
    Se recomienda crear un entorno virtual.
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configurar variables de entorno:**
    Cree un archivo `.env` en la raíz del proyecto y añada sus credenciales. El contenido debe ser:

    ```env
    # Variables de entorno para mcp_server.py

    # Clave API para Deepseek
    DEEPSEEK_API_KEY="SU_DEEPSEEK_API_KEY_AQUI"

    # Credenciales de la aplicación Autodesk Platform Services
    AUTODESK_CLIENT_ID="SU_AUTODESK_CLIENT_ID_AQUI"
    AUTODESK_CLIENT_SECRET="SU_AUTODESK_CLIENT_SECRET_AQUI"

    # URI de redirección configurado en tu aplicación Autodesk
    # Debe coincidir exactamente con lo configurado en Autodesk y la ejecución del servidor.
    AUTODESK_REDIRECT_URI="http://127.0.0.1:8000/autodesk/callback"

    # Alcances (scopes) que tu aplicación necesita de Autodesk, separados por espacio.
    # Ejemplo: AUTODESK_SCOPES="data:read viewables:read bucket:read"
    AUTODESK_SCOPES="data:read data:write bucket:create bucket:read"
    ```
    **Nota:** Asegúrese de que `AUTODESK_REDIRECT_URI` en su archivo `.env` coincida exactamente con el URI de redirección configurado en su aplicación de Autodesk Platform Services.

## Ejecución del Servidor

Para iniciar el servidor FastMCP:

```bash
python mcp_server.py
```

El servidor se ejecutará por defecto en `http://127.0.0.1:8000`. Verá mensajes en la consola indicando el estado de carga de las variables de entorno.

## Uso de las Herramientas (Endpoints MCP)

Puede interactuar con el servidor utilizando un cliente MCP compatible (por ejemplo, la CLI de FastMCP u otro cliente programático).

### 1. `get_status()`
Devuelve el estado general del servidor, incluyendo si las claves API y la configuración de Autodesk están cargadas y si se ha obtenido un token de Autodesk.

*   **Ejemplo de llamada (conceptual):**
    `fastmcp call http://127.0.0.1:8000 get_status`

### 2. `get_autodesk_auth_status()`
Verifica si el servidor tiene un token de acceso de Autodesk. Si no, proporciona la URL para iniciar el proceso de autenticación.

*   **Ejemplo de llamada (conceptual):**
    `fastmcp call http://127.0.0.1:8000 get_autodesk_auth_status`
*   **Respuesta si no está autenticado:**
    ```json
    {
        "status": "No autenticado con Autodesk.",
        "token_present": false,
        "login_url": "http://127.0.0.1:8000/autodesk/login"
    }
    ```

### 3. Autenticación con Autodesk
Si `get_autodesk_auth_status` indica que no está autenticado:
    a.  Abra la `login_url` (ej. `http://127.0.0.1:8000/autodesk/login`) en un navegador web.
    b.  Será redirigido a la página de inicio de sesión de Autodesk. Ingrese sus credenciales.
    c.  Autorice a la aplicación los permisos solicitados (definidos en `AUTODESK_SCOPES`).
    d.  Tras la autorización, Autodesk lo redirigirá de vuelta a `AUTODESK_REDIRECT_URI` (ej. `http://127.0.0.1:8000/autodesk/callback`). El servidor intercambiará el código de autorización por un token de acceso.
    e.  Verá un mensaje de éxito o error en el navegador. Si es exitoso, el token de Autodesk está ahora almacenado (temporalmente en memoria) en el servidor.
    f.  Puede volver a llamar a `get_autodesk_auth_status` para confirmar.
*   **Respuesta si está autenticado:**
    ```json
    {
        "status": "Autenticado con Autodesk.",
        "token_present": true
    }
    ```

### 4. `call_deepseek(prompt: str, model: str = "deepseek-chat", max_tokens: int = 2048)`
Llama directamente a la API de Deepseek con el prompt proporcionado. Requiere que `DEEPSEEK_API_KEY` esté configurada.

*   **Ejemplo de llamada (conceptual):**
    `fastmcp call http://127.0.0.1:8000 call_deepseek prompt="¿Cuál es la capital de Francia?"`
*   **Respuesta (ejemplo si es exitoso):**
    ```json
    {
        "id": "chatcmpl-...",
        "object": "chat.completion",
        "created": ...,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "La capital de Francia es París."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": { ... }
    }
    ```

### 5. `call_deepseek_with_autodesk_context(prompt: str, model: str = "deepseek-chat", max_tokens: int = 2048)`
Llama a la API de Deepseek, pero primero verifica si hay un token de Autodesk. Si existe, añade información contextual (derivada del token o estado de autenticación) al prompt enviado a Deepseek.

*   **Importante (Seguridad):** Como está implementado actualmente, esta función añade una porción truncada del token de acceso al prompt. **Esto es solo para fines demostrativos y NO es una práctica segura para producción.** En un entorno real, nunca envíe tokens de acceso directamente a un LLM. En su lugar, use el token para obtener información específica del usuario o de los recursos de Autodesk y pase esa información relevante y segura al LLM.
*   **Ejemplo de llamada (conceptual, asumiendo que ya se autenticó con Autodesk):**
    `fastmcp call http://127.0.0.1:8000 call_deepseek_with_autodesk_context prompt="Basado en mi contexto de Autodesk, ¿qué podrías decirme?"`
*   **Respuesta:** Similar a `call_deepseek`, pero el LLM habrá recibido el prompt modificado. Si no está autenticado con Autodesk, devolverá un error.

## Consideraciones de Seguridad y Mejoras

*   **Manejo de Tokens:** El token de Autodesk se almacena en memoria y se pierde si el servidor se reinicia. Para producción, implemente un almacenamiento persistente y seguro para los tokens (ej. base de datos, caché cifrada).
*   **Refresco de Tokens:** Los tokens de acceso de Autodesk expiran. Implemente la lógica para usar el `refresh_token` (obtenido durante el intercambio de código) para obtener nuevos tokens de acceso automáticamente.
*   **Parámetro `state` en OAuth:** Para prevenir ataques CSRF, el parámetro `state` debe generarse, almacenarse y validarse correctamente durante el flujo de OAuth.
*   **Contexto para Deepseek:** Revise cuidadosamente qué información del contexto de Autodesk es útil y seguro pasar a la API de Deepseek. Evite enviar tokens completos o datos sensibles innecesarios.
*   **Manejo de Errores:** Aunque hay manejo básico de errores, se puede mejorar para proporcionar mensajes más claros o códigos de error específicos.
*   **Configuración de URL del Servidor:** La URL base del servidor (ej. `http://127.0.0.1:8000`) está implícita en algunas partes (como `AUTODESK_REDIRECT_URI` y la `login_url` devuelta). Considere hacer esto más configurable si el servidor necesita ejecutarse en diferentes hosts o puertos.

Este README proporciona una guía básica para configurar y utilizar el servidor.
