import os
import requests
import json
from typing import List, Dict, Any, Optional

# Suponiendo que el cliente OAuth está en el mismo directorio
from oauth_client import OAuthClient

# Configuración (estos deberían venir de una configuración más general o variables de entorno)
# Asumimos que la URL base del API de datos del servidor MCP se define en algún lugar.
# Por ahora, la dejaremos como placeholder.
MCP_DATA_API_BASE_URL = os.getenv("MCP_DATA_API_BASE_URL", "https://api.examplemcp.com/data/v1") # Ejemplo
DOWNLOAD_CHUNK_SIZE = 8192  # 8KB

class DataManagerError(Exception):
    """Clase base para errores del DataManager."""
    pass

class DownloadError(DataManagerError):
    """Error durante la descarga de un archivo."""
    pass

class UploadError(DataManagerError):
    """Error durante la subida de un archivo."""
    pass

class ApiError(DataManagerError):
    """Error genérico de la API de datos."""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self):
        return f"{super().__str__()} (Status: {self.status_code}, Response: {self.response_text})"


class DataManager:
    def __init__(self, oauth_client: OAuthClient, base_api_url: Optional[str] = None):
        self.oauth_client = oauth_client
        self.base_api_url = base_api_url or MCP_DATA_API_BASE_URL
        if not self.base_api_url:
            raise ValueError("MCP_DATA_API_BASE_URL no está configurado.")

    def _get_headers(self) -> Dict[str, str]:
        """Obtiene las cabeceras necesarias, incluyendo el token de acceso."""
        access_token = self.oauth_client.get_access_token()
        if not access_token:
            raise ApiError("No se pudo obtener el token de acceso para la solicitud de datos.")
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json", # Por defecto, puede ser sobreescrito
        }

    def _handle_api_response(self, response: requests.Response):
        """Maneja la respuesta de la API y lanza ApiError si no es exitosa."""
        if not response.ok:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", response.text)
            except json.JSONDecodeError:
                message = response.text
            raise ApiError(
                f"Error en la API: {response.status_code}",
                status_code=response.status_code,
                response_text=message
            )
        # Si es una respuesta vacía pero exitosa (ej. 204 No Content)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            # Si no es JSON pero la respuesta fue OK (ej. descarga de archivo)
            # Devolvemos el contenido crudo en ese caso, o None si está vacío
            return response.content if response.content else None


    def list_files(self, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """
        Lista los archivos del servidor MCP, con paginación.
        El límite de registros por página es 100.
        """
        if per_page > 100:
            print("Advertencia: El límite de registros por página es 100. Se usará 100.")
            per_page = 100

        endpoint = f"{self.base_api_url}/files"
        params = {"page": page, "per_page": per_page}
        headers = self._get_headers()

        try:
            response = requests.get(endpoint, headers=headers, params=params)
            return self._handle_api_response(response)
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Error de red listando archivos: {e}")

    def download_file(self, file_id: str, destination_path: str, version: Optional[str] = "latest") -> None:
        """
        Descarga un archivo desde el servidor MCP a la ruta de destino especificada.
        Permite especificar una versión del archivo; por defecto, la última.
        """
        endpoint = f"{self.base_api_url}/files/{file_id}/download"
        params = {"version": version}
        headers = self._get_headers()
        # Para descargas de archivos, no esperamos JSON, sino un stream
        headers.pop("Content-Type", None)

        print(f"Iniciando descarga del archivo ID: {file_id} (versión: {version}) a {destination_path}")
        try:
            with requests.get(endpoint, headers=headers, params=params, stream=True) as r:
                r.raise_for_status() # Lanza HTTPError para malas respuestas (4xx o 5xx)

                # Intentar obtener el nombre del archivo de Content-Disposition si está disponible
                content_disposition = r.headers.get('content-disposition')
                filename_from_header = None
                if content_disposition:
                    parts = content_disposition.split('filename=')
                    if len(parts) > 1:
                        filename_from_header = parts[1].strip('"')

                # Si destination_path es un directorio, usar el nombre del header o file_id
                if os.path.isdir(destination_path):
                    final_filename = filename_from_header or file_id
                    destination_filepath = os.path.join(destination_path, final_filename)
                else:
                    destination_filepath = destination_path
                    # Crear directorios padres si no existen
                    os.makedirs(os.path.dirname(destination_filepath) or '.', exist_ok=True)


                with open(destination_filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        f.write(chunk)
                print(f"Archivo '{os.path.basename(destination_filepath)}' descargado exitosamente a '{destination_filepath}'.")

        except requests.exceptions.HTTPError as e:
            # Intentar obtener más detalles del error si la respuesta es JSON
            error_message = str(e)
            try:
                error_details = e.response.json()
                error_message = error_details.get("error", {}).get("message", str(e))
            except json.JSONDecodeError:
                pass # Mantener el mensaje de HTTPError
            raise DownloadError(f"Error HTTP descargando archivo {file_id}: {error_message} (Status: {e.response.status_code})")
        except requests.exceptions.RequestException as e:
            raise DownloadError(f"Error de red descargando archivo {file_id}: {e}")
        except IOError as e:
            raise DownloadError(f"Error de E/S guardando archivo {file_id} en {destination_path}: {e}")


    def upload_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sube un nuevo archivo o una nueva versión de un archivo al servidor MCP.
        El servidor determinará si es un archivo nuevo o una nueva versión basado en su lógica interna
        (por ejemplo, si se proporciona un ID de archivo existente en los metadatos).
        """
        if not os.path.exists(file_path):
            raise UploadError(f"El archivo local '{file_path}' no existe.")

        endpoint = f"{self.base_api_url}/files"
        headers = self._get_headers()
        headers.pop("Content-Type", None) # `requests` lo setea con `multipart/form-data`

        file_name = os.path.basename(file_path)
        files = {"file": (file_name, open(file_path, "rb"))}

        # Los metadatos se pueden enviar como un campo 'data' o 'metadata' en el form-data.
        # Consultar la especificación de la API del servidor MCP.
        # Aquí asumimos que se envía como un string JSON en un campo llamado 'metadata'.
        data_payload = {}
        if metadata:
            data_payload["metadata"] = json.dumps(metadata)

        print(f"Iniciando subida del archivo: {file_path}")
        try:
            with open(file_path, "rb") as fp:
                files = {"file": (file_name, fp)}
                response = requests.post(endpoint, headers=headers, files=files, data=data_payload)

            # Después de que `files` se usa en `requests.post`, el archivo se cierra.
            # No es necesario cerrarlo explícitamente si se abrió dentro del `with`.

            return self._handle_api_response(response)
        except requests.exceptions.RequestException as e:
            raise UploadError(f"Error de red subiendo archivo {file_path}: {e}")
        except IOError as e:
            raise UploadError(f"Error de E/S leyendo archivo {file_path} para subir: {e}")


# Ejemplo de uso (requiere un cliente OAuth funcional y un servidor MCP simulado o real)
if __name__ == "__main__":
    print("Ejemplo de uso de DataManager (requiere configuración y servidor MCP):")

    # Crear un archivo .env con:
    # OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_AUTH_URL, OAUTH_TOKEN_URL
    # MCP_DATA_API_BASE_URL="http://localhost:8000/api/v1/data" (o la URL de tu API)

    if not os.getenv("MCP_DATA_API_BASE_URL"):
        print("Error: MCP_DATA_API_BASE_URL no está configurada en las variables de entorno o .env.")
        if not os.path.exists(".env") or "MCP_DATA_API_BASE_URL" not in open(".env").read():
             with open(".env", "a") as f: # 'a' para añadir, no sobreescribir OAuth
                if "\n" not in open(".env").read()[-2:]: f.write("\n")
                f.write("MCP_DATA_API_BASE_URL=\"http://localhost:8000/api/v1/data\"\n") # Ejemplo
             print("Se ha añadido MCP_DATA_API_BASE_URL al .env con un valor de ejemplo. Ajusta si es necesario.")
        # exit(1) # Comentado para permitir la ejecución parcial si OAuth no está listo

    try:
        oauth_client = OAuthClient() # Asume que oauth_client.py está en el mismo dir y .env configurado

        # Para probar, primero necesitas un token. Ejecuta oauth_client.py si no tienes uno.
        if not oauth_client.get_access_token():
            print("No se pudo obtener token de acceso. Por favor, ejecuta oauth_client.py para autenticarte primero.")
            print("O asegúrate de que tus variables de entorno OAuth están bien configuradas en .env")
            # exit(1) # Comentado para permitir la ejecución parcial

        data_manager = DataManager(oauth_client)

        # 1. Listar archivos (simulado, ya que no hay servidor real)
        print("\n--- Listando archivos (simulado) ---")
        try:
            # Esto fallará si el servidor no está disponible o la URL es incorrecta
            # o si el token no es válido para ese servidor.
            if oauth_client.get_access_token() and MCP_DATA_API_BASE_URL != "https://api.examplemcp.com/data/v1":
                 files_page_1 = data_manager.list_files(page=1, per_page=5)
                 print("Archivos (Página 1):", json.dumps(files_page_1, indent=2))
                 # Podrías iterar por más páginas si files_page_1 indica que hay más.
            else:
                print("Listar archivos omitido: token no disponible o URL base es de ejemplo.")

        except ApiError as e:
            print(f"Error al listar archivos: {e}")
        except Exception as e:
            print(f"Error inesperado al listar archivos: {e}")


        # 2. Subir un archivo (simulado)
        print("\n--- Subiendo archivo (simulado) ---")
        test_upload_file_path = "test_upload.txt"
        with open(test_upload_file_path, "w") as f:
            f.write("Este es un archivo de prueba para subir al servidor MCP.")

        try:
            if oauth_client.get_access_token() and MCP_DATA_API_BASE_URL != "https://api.examplemcp.com/data/v1":
                upload_metadata = {"description": "Archivo de prueba", "tags": ["test", "mcp"]}
                upload_response = data_manager.upload_file(test_upload_file_path, metadata=upload_metadata)
                print("Respuesta de subida:", json.dumps(upload_response, indent=2))
                # Suponiendo que la respuesta contiene un ID de archivo
                # uploaded_file_id = upload_response.get("id")
            else:
                print("Subida de archivo omitida: token no disponible o URL base es de ejemplo.")
        except UploadError as e:
            print(f"Error al subir archivo: {e}")
        except ApiError as e:
            print(f"Error de API al subir archivo: {e}")
        except Exception as e:
            print(f"Error inesperado al subir archivo: {e}")
        finally:
            if os.path.exists(test_upload_file_path):
                os.remove(test_upload_file_path)


        # 3. Descargar un archivo (simulado)
        print("\n--- Descargando archivo (simulado) ---")
        # Necesitarías un ID de archivo real del servidor.
        # file_id_to_download = uploaded_file_id or "un_id_de_archivo_existente"
        file_id_to_download = "sample-file-id" # Placeholder
        download_destination = "./downloaded_files" # Directorio para guardar
        os.makedirs(download_destination, exist_ok=True)

        try:
            if oauth_client.get_access_token() and MCP_DATA_API_BASE_URL != "https://api.examplemcp.com/data/v1" and file_id_to_download != "sample-file-id":
                # data_manager.download_file(file_id_to_download, download_destination)
                # print(f"Intento de descarga del archivo ID {file_id_to_download} a {download_destination}")
                # Si el archivo se descarga, se guardará en downloaded_files/file_id_to_download o con el nombre del header
                print(f"Descarga de {file_id_to_download} omitida (comentada para evitar error si el archivo no existe en servidor real).")
            else:
                print(f"Descarga de archivo '{file_id_to_download}' omitida: token no disponible, URL base es de ejemplo o ID de archivo es placeholder.")

        except DownloadError as e:
            print(f"Error al descargar archivo: {e}")
        except ApiError as e:
            print(f"Error de API al descargar archivo: {e}")
        except Exception as e:
            print(f"Error inesperado al descargar archivo: {e}")
        # finally:
            # Limpieza opcional del archivo descargado o directorio si es solo para prueba.
            # shutil.rmtree(download_destination, ignore_errors=True)


    except ImportError:
        print("Error: No se pudo importar OAuthClient. Asegúrate de que oauth_client.py está en el mismo directorio.")
    except ValueError as e:
        print(f"Error de configuración: {e}")
    except Exception as e:
        print(f"Ocurrió un error general en el script de ejemplo de DataManager: {e}")

# Consideraciones Adicionales para DataManager:
# 1. Asincronía: Similar a OAuthClient, este DataManager usa `requests` (síncrono).
#    Para la integración con FastMCP (asíncrono), las llamadas a la API deberían
#    usar `httpx` con `async/await`.
# 2. URL Base de la API: MCP_DATA_API_BASE_URL debe ser configurable de manera robusta.
# 3. Especificación de la API del Servidor MCP: Los endpoints exactos (/files, /files/{id}/download),
#    los parámetros de paginación, cómo se manejan las versiones de los archivos, y el formato
#    de los metadatos de subida dependen completamente de la API del servidor MCP específico.
#    Este código hace suposiciones razonables.
# 4. Manejo de Errores: El manejo de errores puede expandirse (reintentos, backoff exponencial, etc.).
# 5. Nombres de Archivo en Descarga: Se intenta usar `Content-Disposition`. Si no está, se usa el `file_id`.
#    Podría necesitarse una lógica más sofisticada.
# 6. Progreso de Subida/Descarga: Para archivos grandes, se podría implementar callbacks o un sistema
#    para reportar el progreso. `requests` no lo facilita tanto para subidas como algunas otras librerías.
# 7. Testing: Requiere un mock del servidor HTTP o un servidor de prueba para tests unitarios/integración.
# 8. Seguridad del Token: Ya manejado por OAuthClient, pero es crucial.
# 9. Chunking en Subida: Para archivos muy grandes, la subida podría necesitar ser "chunked" si la API lo soporta.
#    Actualmente, carga todo el archivo en memoria (o `requests` lo streamea desde disco si es `open(file_path, "rb")`).
#    La subida con `files` en `requests` es eficiente para la mayoría de los casos.
# 10. Versiones de Archivos: La lógica de cómo el servidor maneja las versiones (si se sube un archivo
#     con el mismo nombre, o si se necesita un ID de archivo "padre" para una nueva versión)
#     es específica de la API del servidor. El método `upload_file` es genérico en este aspecto.
#     Podría necesitarse un método `upload_new_version(file_path, existing_file_id, metadata)` separado.
# 11. Paginación Completa: El método `list_files` solo obtiene una página. Una función de utilidad
#     `list_all_files` podría construirse sobre ella para obtener todos los archivos iterando
#     a través de las páginas hasta que no haya más resultados.
#
# Este módulo provee una base sólida para la gestión de datos.
# La adaptación a la API específica del servidor MCP y la conversión a asíncrono son los siguientes pasos clave.
