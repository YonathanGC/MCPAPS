import os
from fastmcp import FastMCP
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Crear instancia del servidor FastMCP
mcp = FastMCP(name="DeepseekAutodeskServer")

# Variables de configuración (inicialmente vacías o con valores predeterminados)
# Estas se llenarán/usarán en pasos posteriores
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions" # Ejemplo, ajustar si es necesario

AUTODESK_CLIENT_ID = os.getenv("AUTODESK_CLIENT_ID")
AUTODESK_CLIENT_SECRET = os.getenv("AUTODESK_CLIENT_SECRET")
AUTODESK_REDIRECT_URI = os.getenv("AUTODESK_REDIRECT_URI")
AUTODESK_AUTH_URL = "https://developer.api.autodesk.com/authentication/v1/authorize" # Ejemplo, ajustar
AUTODESK_TOKEN_URL = "https://developer.api.autodesk.com/authentication/v1/gettoken" # Ejemplo, ajustar
AUTODESK_SCOPES = "data:read data:write" # Ejemplo, ajustar según necesidad

# Almacenamiento simple para el token de Autodesk (en producción, usar algo más robusto)
autodesk_access_token = None

# Importar requests para llamadas HTTP
import requests
import json
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode

@mcp.tool
def get_status() -> str:
    """Devuelve el estado actual del servidor."""
    status = "Servidor FastMCP en funcionamiento.\n"
    if DEEPSEEK_API_KEY:
        status += "Clave API de Deepseek cargada.\n"
    else:
        status += "Clave API de Deepseek NO cargada.\n"
    if AUTODESK_CLIENT_ID and AUTODESK_CLIENT_SECRET and AUTODESK_REDIRECT_URI:
        status += "Configuración de cliente Autodesk cargada.\n"
    else:
        status += "Configuración de cliente Autodesk INCOMPLETA.\n"
    if autodesk_access_token:
        status += "Token de acceso de Autodesk OBTENIDO.\n"
    else:
        status += "Token de acceso de Autodesk NO OBTENIDO.\n"
    return status

@mcp.tool
def call_deepseek(prompt: str, model: str = "deepseek-chat", max_tokens: int = 2048) -> str:
    """
    Realiza una llamada a la API de Deepseek para obtener una compleción de chat.

    Args:
        prompt: El mensaje del usuario para enviar a Deepseek.
        model: El modelo a utilizar (por defecto 'deepseek-chat').
        max_tokens: El número máximo de tokens a generar.

    Returns:
        La respuesta de la API de Deepseek como una cadena de texto JSON,
        o un mensaje de error si la llamada falla.
    """
    if not DEEPSEEK_API_KEY:
        return json.dumps({"error": "La clave API de Deepseek (DEEPSEEK_API_KEY) no está configurada."})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7, # Ejemplo, se puede ajustar
        # "stream": False, # FastMCP maneja streaming de forma diferente si es necesario
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Error en la llamada a la API de Deepseek: {str(e)}"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Error al decodificar la respuesta JSON de Deepseek.", "response_text": response.text})

# --- Lógica de Autenticación OAuth de Autodesk ---

@mcp.asgi_app.route("/autodesk/login", methods=["GET"])
async def autodesk_login(request: Request):
    """
    Redirige al usuario a la página de autorización de Autodesk.
    """
    if not all([AUTODESK_CLIENT_ID, AUTODESK_REDIRECT_URI, AUTODESK_SCOPES]):
        return HTMLResponse(
            "Error: Faltan variables de configuración de Autodesk (CLIENT_ID, REDIRECT_URI, SCOPES).",
            status_code=500
        )

    params = {
        "response_type": "code",
        "client_id": AUTODESK_CLIENT_ID,
        "redirect_uri": AUTODESK_REDIRECT_URI,
        "scope": AUTODESK_SCOPES,
        # "state": "un_valor_aleatorio_y_seguro" # IMPORTANTE para producción
    }
    auth_url = f"{AUTODESK_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)

@mcp.asgi_app.route("/autodesk/callback", methods=["GET"])
async def autodesk_callback(request: Request):
    """
    Callback de Autodesk después de la autorización del usuario.
    Intercambia el código de autorización por un token de acceso.
    """
    global autodesk_access_token
    code = request.query_params.get("code")
    # state_received = request.query_params.get("state") # Validar el state en producción

    if not code:
        return HTMLResponse(
            "Error: No se recibió el código de autorización de Autodesk.",
            status_code=400
        )

    if not all([AUTODESK_CLIENT_ID, AUTODESK_CLIENT_SECRET, AUTODESK_REDIRECT_URI, AUTODESK_TOKEN_URL]):
        return HTMLResponse(
            "Error: Faltan variables de configuración de Autodesk para el intercambio de token.",
            status_code=500
        )

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": AUTODESK_CLIENT_ID,
        "client_secret": AUTODESK_CLIENT_SECRET,
        "redirect_uri": AUTODESK_REDIRECT_URI,
    }

    try:
        response = requests.post(AUTODESK_TOKEN_URL, data=token_data, timeout=10)
        response.raise_for_status()
        token_info = response.json()

        autodesk_access_token = token_info.get("access_token")
        # En producción, también querrás almacenar refresh_token, expires_in, etc.
        # y manejar la expiración y el refresco del token.

        if autodesk_access_token:
            return HTMLResponse(
                "¡Autenticación con Autodesk exitosa! El token ha sido obtenido. Puede cerrar esta ventana."
            )
        else:
            return HTMLResponse(
                f"Error: No se pudo obtener el token de acceso de la respuesta de Autodesk. Respuesta: {token_info}",
                status_code=400
            )
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            f"Error al intercambiar el código por el token: {str(e)} <br/>Respuesta del servidor: {response.text if 'response' in locals() else 'N/A'}",
            status_code=500
        )
    except json.JSONDecodeError:
        return HTMLResponse(
            f"Error al decodificar la respuesta JSON del token de Autodesk. Respuesta: {response.text if 'response' in locals() else 'N/A'}",
            status_code=500
        )

@mcp.tool
def get_autodesk_auth_status() -> dict:
    """
    Devuelve el estado de la autenticación de Autodesk y proporciona la URL de inicio de sesión si no está autenticado.
    """
    if autodesk_access_token:
        return {"status": "Autenticado con Autodesk.", "token_present": True}
    else:
        # Asumiendo que el servidor corre en localhost:8000 (ajustar si es diferente)
        login_url = "http://127.0.0.1:8000/autodesk/login"
        return {
            "status": "No autenticado con Autodesk.",
            "token_present": False,
            "login_url": login_url
        }

@mcp.tool
def call_deepseek_with_autodesk_context(prompt: str, model: str = "deepseek-chat", max_tokens: int = 2048) -> str:
    """
    Realiza una llamada a la API de Deepseek, añadiendo el token de Autodesk al prompt si está disponible.
    ADVERTENCIA: Enviar tokens de acceso directamente en prompts a LLMs puede tener implicaciones de seguridad.
                 Considere cuidadosamente los riesgos y si esto es realmente necesario.
                 Podría ser mejor pasar información derivada del token o del estado de autenticación.

    Args:
        prompt: El mensaje del usuario para enviar a Deepseek.
        model: El modelo a utilizar (por defecto 'deepseek-chat').
        max_tokens: El número máximo de tokens a generar.

    Returns:
        La respuesta de la API de Deepseek como una cadena de texto JSON,
        o un mensaje de error si la llamada falla.
    """
    global autodesk_access_token

    if not autodesk_access_token:
        return json.dumps({
            "error": "No autenticado con Autodesk. Por favor, autentíquese primero.",
            "autodesk_auth_status": get_autodesk_auth_status()
        })

    # Ejemplo: Añadir información sobre el token al prompt.
    # ¡¡¡CUIDADO CON LA SEGURIDAD AL HACER ESTO!!!
    # En un caso real, es probable que NO quieras enviar el token directamente.
    # Enviarías un resumen, un ID de usuario, o algún dato obtenido usando el token.
    contextual_prompt = (
        f"Contexto de Autodesk: Se ha autenticado un usuario con Autodesk. Token (parcial para demo): {autodesk_access_token[:20]}...\n\n"
        f"Pregunta del usuario: {prompt}"
    )

    # Reutilizamos la función existente call_deepseek
    return call_deepseek(prompt=contextual_prompt, model=model, max_tokens=max_tokens)

# Aquí se añadirán más herramientas

if __name__ == "__main__":
    print("Iniciando servidor FastMCP...")
    print(f"DEEPSEEK_API_KEY: {'Cargada' if DEEPSEEK_API_KEY else 'NO Cargada'}")
    print(f"AUTODESK_CLIENT_ID: {'Cargado' if AUTODESK_CLIENT_ID else 'NO Cargado'}")
    print(f"AUTODESK_CLIENT_SECRET: {'Cargado' if AUTODESK_CLIENT_SECRET else 'NO Cargado'}")
    print(f"AUTODESK_REDIRECT_URI: {'Cargado' if AUTODESK_REDIRECT_URI else 'NO Cargado'}")

    # Ejecutar el servidor FastMCP.
    # Para desarrollo, podríamos usar http, pero stdio es el default y más simple para iniciar.
    # Para la autenticación OAuth, necesitaremos un endpoint HTTP para el redirect URI.
    # Por ahora, lo dejaremos con el default, y lo ajustaremos cuando implementemos OAuth.
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
