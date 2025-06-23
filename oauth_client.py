import os
import time
import json
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Configuración de OAuth 2.0 (ejemplo para Google, ajustar según el proveedor)
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/callback")
AUTH_URL = os.getenv("OAUTH_AUTH_URL") # Ejemplo: "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = os.getenv("OAUTH_TOKEN_URL") # Ejemplo: "https://oauth2.googleapis.com/token"
TOKEN_CACHE_FILE = "token_cache.enc"
CACHE_KEY_FILE = "cache.key" # Clave para cifrar/descifrar el caché de tokens
TOKEN_EXPIRATION_MARGIN_SECONDS = 300  # 5 minutos de margen para la renovación

class OAuthClient:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.redirect_uri = REDIRECT_URI
        self.auth_url = AUTH_URL
        self.token_url = TOKEN_URL
        self._load_or_generate_cache_key()
        self.cipher_suite = Fernet(self.cache_key)
        self.token_data = self._load_token_from_cache()

    def _load_or_generate_cache_key(self):
        """Carga la clave de cifrado desde el archivo o genera una nueva si no existe."""
        if os.path.exists(CACHE_KEY_FILE):
            with open(CACHE_KEY_FILE, "rb") as f:
                self.cache_key = f.read()
        else:
            self.cache_key = Fernet.generate_key()
            with open(CACHE_KEY_FILE, "wb") as f:
                f.write(self.cache_key)

    def _encrypt_data(self, data: dict) -> bytes:
        """Cifra los datos del token."""
        return self.cipher_suite.encrypt(json.dumps(data).encode())

    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        """Descifra los datos del token."""
        return json.loads(self.cipher_suite.decrypt(encrypted_data).decode())

    def _save_token_to_cache(self, token_data: dict):
        """Guarda el token cifrado en el archivo de caché."""
        if not token_data:
            return
        encrypted_token = self._encrypt_data(token_data)
        with open(TOKEN_CACHE_FILE, "wb") as f:
            f.write(encrypted_token)
        self.token_data = token_data

    def _load_token_from_cache(self) -> dict | None:
        """Carga el token descifrado desde el archivo de caché."""
        if not os.path.exists(TOKEN_CACHE_FILE):
            return None
        try:
            with open(TOKEN_CACHE_FILE, "rb") as f:
                encrypted_token = f.read()
            return self._decrypt_data(encrypted_token)
        except Exception as e:
            print(f"Error al cargar token desde caché: {e}")
            # Si hay error (ej. clave incorrecta, archivo corrupto), eliminar caché.
            if os.path.exists(TOKEN_CACHE_FILE):
                os.remove(TOKEN_CACHE_FILE)
            return None

    def _is_token_expired(self) -> bool:
        """Verifica si el token ha expirado o está cerca de expirar."""
        if not self.token_data or "expires_at" not in self.token_data:
            return True
        # Comprueba si el tiempo actual más el margen es mayor o igual al tiempo de expiración.
        return time.time() + TOKEN_EXPIRATION_MARGIN_SECONDS >= self.token_data["expires_at"]

    def get_authorization_url(self, scope: str | list[str], state: str = None) -> str:
        """Genera la URL de autorización para el usuario."""
        if not self.client_id or not self.auth_url:
            raise ValueError("CLIENT_ID y AUTH_URL deben estar configurados.")

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scope) if isinstance(scope, list) else scope,
        }
        if state:
            params["state"] = state

        # Construir la URL con parámetros
        req = requests.Request('GET', self.auth_url, params=params)
        prepared_req = req.prepare()
        return prepared_req.url

    def exchange_code_for_token(self, authorization_code: str) -> dict:
        """Intercambia el código de autorización por un token de acceso."""
        if not self.client_id or not self.client_secret or not self.token_url:
            raise ValueError("CLIENT_ID, CLIENT_SECRET y TOKEN_URL deben estar configurados.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        try:
            response = requests.post(self.token_url, data=payload)
            response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
            token_data = response.json()

            if "expires_in" in token_data:
                token_data["expires_at"] = time.time() + token_data["expires_in"]

            self._save_token_to_cache(token_data)
            return token_data
        except requests.exceptions.RequestException as e:
            print(f"Error al intercambiar código por token: {e}")
            if e.response is not None:
                print(f"Respuesta del servidor: {e.response.text}")
            # Considerar eliminar el caché si el token es definitivamente inválido
            # if e.response and e.response.status_code in [400, 401]:
            #     if os.path.exists(TOKEN_CACHE_FILE):
            #         os.remove(TOKEN_CACHE_FILE)
            raise

    def refresh_token(self) -> dict:
        """Refresca el token de acceso utilizando el refresh token."""
        if not self.token_data or "refresh_token" not in self.token_data:
            raise ValueError("No hay refresh token disponible para renovar.")
        if not self.client_id or not self.client_secret or not self.token_url:
            raise ValueError("CLIENT_ID, CLIENT_SECRET y TOKEN_URL deben estar configurados para refrescar el token.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.token_data["refresh_token"],
            "grant_type": "refresh_token",
        }
        try:
            response = requests.post(self.token_url, data=payload)
            response.raise_for_status()
            new_token_data = response.json()

            # El nuevo token puede o no incluir un nuevo refresh_token.
            # Si no lo incluye, conservamos el anterior.
            if "refresh_token" not in new_token_data and "refresh_token" in self.token_data:
                new_token_data["refresh_token"] = self.token_data["refresh_token"]

            if "expires_in" in new_token_data:
                new_token_data["expires_at"] = time.time() + new_token_data["expires_in"]

            self._save_token_to_cache(new_token_data)
            return new_token_data
        except requests.exceptions.RequestException as e:
            print(f"Error al refrescar el token: {e}")
            if e.response is not None:
                print(f"Respuesta del servidor: {e.response.text}")
            # Si el refresh token es inválido (ej. revocado), eliminar el caché.
            if e.response and e.response.status_code in [400, 401]:
                 print("El refresh token es inválido. Limpiando caché de token.")
                 if os.path.exists(TOKEN_CACHE_FILE):
                    os.remove(TOKEN_CACHE_FILE)
                 self.token_data = None # Limpiar token en memoria
            raise

    def get_access_token(self) -> str | None:
        """Obtiene el token de acceso, refrescándolo si es necesario."""
        if not self.token_data and not self._load_token_from_cache():
            print("No hay token en caché. Es necesario obtener uno nuevo mediante el flujo de autorización.")
            return None # O lanzar una excepción / iniciar flujo de autorización

        if self._is_token_expired():
            print("Token expirado o cerca de expirar. Intentando refrescar...")
            try:
                self.refresh_token()
            except Exception as e:
                print(f"No se pudo refrescar el token: {e}. Se requiere nueva autorización.")
                # Aquí podrías eliminar el caché si el refresco falla consistentemente
                # y forzar una nueva autenticación completa.
                if os.path.exists(TOKEN_CACHE_FILE):
                    os.remove(TOKEN_CACHE_FILE)
                self.token_data = None
                return None # O lanzar una excepción

        return self.token_data.get("access_token") if self.token_data else None

# Ejemplo de uso (requiere que las variables de entorno estén configuradas):
if __name__ == "__main__":
    # Estas variables deben estar en tu archivo .env o exportadas en el entorno
    # OAUTH_CLIENT_ID="tu_client_id"
    # OAUTH_CLIENT_SECRET="tu_client_secret"
    # OAUTH_AUTH_URL="url_de_autorizacion_del_proveedor"
    # OAUTH_TOKEN_URL="url_de_token_del_proveedor"
    # OAUTH_REDIRECT_URI="http://localhost:8080/callback" (debe estar registrado en el proveedor OAuth)

    if not all([CLIENT_ID, CLIENT_SECRET, AUTH_URL, TOKEN_URL]):
        print("Error: Faltan variables de entorno para OAuth (CLIENT_ID, CLIENT_SECRET, AUTH_URL, TOKEN_URL).")
        print("Asegúrate de crear un archivo .env con estas variables o exportarlas.")
        # Crear un .env de ejemplo si no existe para guiar al usuario
        if not os.path.exists(".env"):
            with open(".env", "w") as f:
                f.write("OAUTH_CLIENT_ID=\"TU_CLIENT_ID_AQUI\"\n")
                f.write("OAUTH_CLIENT_SECRET=\"TU_CLIENT_SECRET_AQUI\"\n")
                f.write("OAUTH_AUTH_URL=\"URL_AUTORIZACION_PROVEEDOR_AQUI\"\n")
                f.write("OAUTH_TOKEN_URL=\"URL_TOKEN_PROVEEDOR_AQUI\"\n")
                f.write("OAUTH_REDIRECT_URI=\"http://localhost:8080/callback\"\n")
            print("Se ha creado un archivo .env de ejemplo. Por favor, edítalo con tus credenciales.")
        exit(1)

    client = OAuthClient()

    access_token = client.get_access_token()

    if not access_token:
        print("No se pudo obtener el token de acceso. Iniciando flujo de autorización.")
        # Ejemplo de cómo obtener la URL de autorización
        # Necesitarás el scope adecuado para tu aplicación.
        # Por ejemplo, para Google API podría ser 'https://www.googleapis.com/auth/drive.metadata.readonly'
        scope_ejemplo = "profile email openid" # Ajustar según el proveedor y necesidades
        auth_url = client.get_authorization_url(scope=scope_ejemplo)
        print(f"Por favor, ve a esta URL y autoriza la aplicación: {auth_url}")

        # Después de que el usuario autoriza, será redirigido a REDIRECT_URI
        # con un parámetro 'code'. Debes capturar ese código.
        auth_code = input("Pega el código de autorización aquí: ")

        try:
            client.exchange_code_for_token(auth_code)
            access_token = client.get_access_token()
            if access_token:
                print("¡Token obtenido y guardado exitosamente!")
                print(f"Token de acceso: {access_token[:20]}...") # Muestra solo una parte
            else:
                print("Falló la obtención del token después del intercambio.")
        except Exception as e:
            print(f"Error durante el intercambio de código: {e}")
    else:
        print("Token de acceso cargado desde caché o refrescado exitosamente.")
        print(f"Token de acceso: {access_token[:20]}...") # Muestra solo una parte

    # Ejemplo de cómo usar el token para una solicitud (simulado)
    if access_token:
        print("\nSimulando una solicitud a una API protegida...")
        headers = {"Authorization": f"Bearer {access_token}"}
        # response = requests.get("https://api.example.com/data", headers=headers)
        # print(f"Respuesta de la API (simulada): {response.status_code}")
        print(f"Cabeceras para la API: {headers}")

    # Para probar la renovación, podrías modificar artificialmente el 'expires_at' en el caché
    # o esperar a que expire naturalmente si el tiempo de expiración es corto.
    # OJO: No modificar directamente el archivo cifrado, sino el `client.token_data` y luego guardarlo
    # si quieres forzar un escenario de prueba.
    # Ejemplo:
    # if client.token_data:
    # client.token_data['expires_at'] = time.time() - 7200 # Simular que expiró hace 2 horas
    # client._save_token_to_cache(client.token_data)
    # print("\nToken modificado para simular expiración. Intentando obtenerlo de nuevo (debería refrescar)...")
    # access_token_refrescado = client.get_access_token()
    # if access_token_refrescado:
    # print(f"Token refrescado: {access_token_refrescado[:20]}...")
    # else:
    # print("Fallo al refrescar el token simulado.")

    print("\nPrueba de OAuthClient completada.")
    print(f"Recuerda configurar tus variables de entorno en un archivo .env o directamente.")
    print(f"El token (si se obtuvo) está guardado cifrado en '{TOKEN_CACHE_FILE}'.")
    print(f"La clave de cifrado está en '{CACHE_KEY_FILE}'. ¡Guarda esta clave de forma segura!")

# Consideraciones adicionales:
# 1. Seguridad de CACHE_KEY_FILE: Esta clave es sensible. En un entorno de producción,
#    considera almacenarla de forma más segura (ej. gestor de secretos, variable de entorno protegida).
# 2. Manejo de errores: El manejo de errores es básico. En producción, querrás un logging más robusto
#    y posiblemente estrategias de reintento más sofisticadas.
# 3. Flujo de autorización: Este script asume un flujo donde el usuario copia y pega el código.
#    En una aplicación web, el redirect_uri manejaría esto automáticamente.
# 4. Scopes: Asegúrate de solicitar solo los scopes necesarios.
# 5. State parameter: El parámetro 'state' en `get_authorization_url` es importante para prevenir CSRF.
#    Deberías generarlo, guardarlo en la sesión del usuario y verificarlo en el callback.
# 6. Multi-usuario: Este cliente está diseñado para un solo "usuario" (una sola caché de token).
#    Para múltiples usuarios, necesitarías gestionar múltiples cachés o tokens.
# 7. Proveedor OAuth específico: Los detalles como las URLs exactas, los scopes y los parámetros
#    pueden variar entre proveedores OAuth (Google, GitHub, Azure AD, etc.).
#    Este código es una plantilla general.
# 8. Eliminación de caché: Considerar cuándo y cómo invalidar/eliminar la caché si el refresh token
#    es revocado o si el usuario desautoriza la aplicación.
# 9. Pruebas: Probar exhaustivamente todos los flujos (obtención inicial, carga desde caché,
#    refresco exitoso, refresco fallido, token inválido).
# 10. Entorno de ejecución: Si esto se ejecuta en un servidor, asegúrate de que los permisos de archivo
#     para TOKEN_CACHE_FILE y CACHE_KEY_FILE sean apropiados.
# 11. Librerías OAuth: Para flujos más complejos o para evitar reinventar la rueda, considera usar
#     librerías como Authlib (que ya instalamos como dependencia de fastmcp) o requests-oauthlib.
#     FastMCP mismo usa Authlib, por lo que integrarse con sus mecanismos puede ser una opción.
#     Este script es más bien una implementación manual para ilustrar los conceptos.
#     Sin embargo, la gestión del caché con Fernet es una adición útil.
# 12. Asincronía: Si tu aplicación es asíncrona (ej. FastAPI), querrás usar `httpx` en lugar de `requests`
#     y adaptar las llamadas para que sean `async/await`.
#     FastMCP es asíncrono, por lo que esto será importante al integrarlo.
