import os
import sys
import logging
from typing import List, Dict, Any, Optional

# Intentar importar FastMCP y componentes relacionados
try:
    from fastmcp import FastMCP, Tool, MCPContext, Resource, BaseModel
    from fastmcp.server_app import create_app # Para crear una app ASGI completa
    import uvicorn
except ImportError:
    logging.error("FastMCP no está instalado. Por favor, instálalo con 'pip install fastmcp uvicorn'.")
    sys.exit(1)

# Importar módulos del proyecto
# Asumimos que server_config carga la configuración al ser importado.
from server_config import config

# Importar los clientes y servicios (versiones síncronas por ahora)
# Necesitarán ser adaptados a async o envueltos para uso en FastMCP asíncrono.
from oauth_client import OAuthClient
from data_manager import DataManager, ApiError as DataManagerApiError # Renombrar para evitar conflicto con posible ApiError de FastMCP
from design_automation_engine import DesignAutomationService, ExampleScriptEngine, CADProcessingError, CADFileNotFoundError

# --- Configuración Inicial y Logging ---
# El logging ya debería estar configurado por la importación de server_config.
# Imprimir un resumen de la configuración para verificar.
config.print_config_summary()

# --- Instancias de Servicios ---
# Estas instancias se crearán una vez y se usarán en las herramientas/recursos.

# 1. OAuthClient
# OAuthClient necesita las variables de entorno que carga ServerConfig.
# No necesita argumentos si las variables de entorno están seteadas.
try:
    oauth_client_instance = OAuthClient()
    logging.info("Instancia de OAuthClient creada.")
except ValueError as e:
    logging.error(f"Error al inicializar OAuthClient: {e}. Asegúrate de que las variables de entorno OAuth estén configuradas.")
    # Podríamos decidir salir o continuar con funcionalidad limitada. Por ahora, continuamos.
    oauth_client_instance = None
except Exception as e:
    logging.error(f"Excepción inesperada al inicializar OAuthClient: {e}")
    oauth_client_instance = None

# 2. DataManager
# DataManager necesita una instancia de OAuthClient.
if oauth_client_instance:
    try:
        data_manager_instance = DataManager(oauth_client=oauth_client_instance, base_api_url=config.mcp_data_api_base_url)
        logging.info("Instancia de DataManager creada.")
    except ValueError as e:
        logging.error(f"Error al inicializar DataManager: {e}")
        data_manager_instance = None
    except Exception as e:
        logging.error(f"Excepción inesperada al inicializar DataManager: {e}")
        data_manager_instance = None
else:
    logging.warning("No se pudo crear DataManager porque OAuthClient no está disponible.")
    data_manager_instance = None

# 3. DesignAutomationService
# DesignAutomationService necesita una instancia de DataManager.
if data_manager_instance:
    try:
        design_auto_service_instance = DesignAutomationService(data_manager=data_manager_instance)
        logging.info("Instancia de DesignAutomationService creada.")

        # Registrar motores CAD configurados
        # Esto es un ejemplo basado en la carga de config en server_config.py
        for engine_name, engine_cfg_data in config.cad_engine_configs.items():
            if engine_name == "MyPythonCADTool": # Nombre de ejemplo
                try:
                    # Asegurarse de que el script_path sea absoluto o relativo al directorio correcto
                    # Aquí asumimos que está relativo al CWD o es absoluto.
                    # En una app real, la gestión de rutas sería más robusta.
                    script_path = engine_cfg_data.get("script_path")
                    if script_path and not os.path.isabs(script_path):
                        script_path = os.path.abspath(script_path)
                        engine_cfg_data["script_path"] = script_path # Actualizar con path absoluto

                    if not script_path or not os.path.exists(script_path):
                         logging.warning(f"Script path para {engine_name} ('{script_path}') no encontrado. El motor podría no funcionar.")

                    engine = ExampleScriptEngine(name=engine_name, config=engine_cfg_data)
                    design_auto_service_instance.register_engine(engine)
                except Exception as e:
                    logging.error(f"Error al registrar el motor CAD '{engine_name}': {e}")
            # Aquí se podrían registrar otros tipos de motores basados en su config

    except Exception as e:
        logging.error(f"Excepción inesperada al inicializar DesignAutomationService: {e}")
        design_auto_service_instance = None
else:
    logging.warning("No se pudo crear DesignAutomationService porque DataManager no está disponible.")
    design_auto_service_instance = None


# --- Adaptación a Asíncrono (Placeholder) ---
# Los servicios actuales (OAuthClient, DataManager, DesignAutomationService) son síncronos.
# FastMCP es asíncrono. Para producción, estos servicios deberían ser reescritos usando httpx y async/await.
# Como solución temporal (NO RECOMENDADA PARA PRODUCCIÓN), se pueden envolver las llamadas síncronas
# usando `context.run_in_executor` o `asyncio.to_thread` (Python 3.9+).

async def run_sync_in_executor(func, *args, **kwargs):
    """Ejecuta una función síncrona en un ejecutor de hilos."""
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# --- Definición de Herramientas (Tools) y Recursos (Resources) para FastMCP ---

mcp_server = FastMCP(
    title="Servidor MCP Avanzado",
    description="Un servidor MCP con OAuth, Data Management y Design Automation.",
    version="1.0.0"
)

# Modelos Pydantic para las entradas y salidas de las herramientas
class FileListParams(BaseModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 100

class FileDownloadParams(BaseModel):
    file_id: str
    destination_path: str # En un servidor real, esto podría ser manejado internamente
    version: Optional[str] = "latest"

class FileUploadParams(BaseModel):
    file_path: str # Ruta local al archivo a subir (para un cliente CLI podría tener sentido)
                   # Para un servidor, esto podría ser un ID de un archivo ya en una staging area, o el contenido.
    metadata_json: Optional[str] = None # JSON string para los metadatos

class CADWorkflowParams(BaseModel):
    workflow_definition_json: str # El workflow como un string JSON

# --- Herramientas de Data Management ---
if data_manager_instance:
    @mcp_server.tool()
    async def list_mcp_files(params: FileListParams, context: MCPContext) -> Dict[str, Any]:
        """
        Lista los archivos disponibles en el servidor MCP.
        Permite paginación (page, per_page). Límite de 100 registros por página.
        """
        context.log.info(f"Listando archivos: page={params.page}, per_page={params.per_page}")
        if not data_manager_instance:
            return {"error": "DataManager no está disponible."}
        try:
            # Adaptación para llamada síncrona
            result = await run_sync_in_executor(
                data_manager_instance.list_files,
                page=params.page,
                per_page=params.per_page
            )
            return result
        except DataManagerApiError as e:
            context.log.error(f"Error de API al listar archivos: {e}")
            return {"error": str(e), "status_code": e.status_code, "details": e.response_text}
        except Exception as e:
            context.log.error(f"Error inesperado al listar archivos: {e}")
            return {"error": f"Error inesperado: {str(e)}"}

    @mcp_server.tool()
    async def download_mcp_file(params: FileDownloadParams, context: MCPContext) -> Dict[str, str]:
        """
        Descarga un archivo específico del servidor MCP.
        Se necesita file_id y una ruta de destino (destination_path).
        Opcionalmente, una versión del archivo.
        """
        context.log.info(f"Solicitud de descarga: file_id='{params.file_id}', dest='{params.destination_path}', ver='{params.version}'")
        if not data_manager_instance:
            return {"error": "DataManager no está disponible."}

        # Validación de destination_path (muy básica, en un entorno real sería más seguro)
        # Por seguridad, no permitir paths absolutos o que salgan de un directorio base.
        # Aquí, para simplificar, asumimos que el cliente sabe lo que hace o que hay otra capa de validación.
        # O mejor, el servidor decide dónde guardar y devuelve una referencia o el contenido.
        # Por ahora, lo dejamos como está en DataManager, pero es un punto de atención.
        # En un servidor real, el "destination_path" sería probablemente un path DENTRO del servidor.
        # O la herramienta devolvería el contenido del archivo directamente.

        # Para este ejemplo, vamos a asumir que destination_path es un nombre de archivo sugerido
        # y el servidor lo guardará en un directorio temporal/de trabajo y devolverá ese path.
        # O, si es una API, podría devolver el contenido binario.
        # Simplificación: Usamos el DataManager como está.

        try:
            # Adaptación para llamada síncrona
            await run_sync_in_executor(
                data_manager_instance.download_file,
                file_id=params.file_id,
                destination_path=params.destination_path, # Esto necesita ser repensado para un servidor real
                version=params.version
            )
            # Verificar si el archivo fue creado donde se esperaba (esto es una simplificación)
            if os.path.exists(params.destination_path) or \
               any(os.path.exists(os.path.join(params.destination_path, f)) for f in os.listdir(params.destination_path) if os.path.isdir(params.destination_path)): # Si es un dir
                return {"status": "success", "message": f"Archivo {params.file_id} descargado a (o en) {params.destination_path}"}
            else:
                 # Esto es un poco hacky, ya que download_file puede ponerlo en un subdirectorio con el nombre del header.
                 # El DataManager debería devolver el path final.
                return {"status": "warning", "message": f"Descarga de {params.file_id} procesada, pero la verificación del archivo en {params.destination_path} es incierta. Revisa el log."}

        except DataManagerApiError as e: # Usar el alias
            context.log.error(f"Error de API al descargar archivo {params.file_id}: {e}")
            return {"error": str(e), "status_code": e.status_code, "details": e.response_text}
        except Exception as e:
            context.log.error(f"Error inesperado al descargar archivo {params.file_id}: {e}")
            return {"error": f"Error inesperado: {str(e)}"}

    @mcp_server.tool()
    async def upload_mcp_file(params: FileUploadParams, context: MCPContext) -> Dict[str, Any]:
        """
        Sube un archivo al servidor MCP.
        Se necesita la ruta local al archivo (file_path) y opcionalmente metadatos en JSON.
        """
        context.log.info(f"Solicitud de subida: file_path='{params.file_path}'")
        if not data_manager_instance:
            return {"error": "DataManager no está disponible."}

        # En un servidor real, `file_path` sería problemático por seguridad y acceso.
        # Usualmente se recibiría el contenido del archivo (multipart/form-data) o un ID de un staging.
        # Aquí, como el DataManager lo toma, y esto podría ser usado por un cliente CLI local, lo mantenemos.
        if not os.path.exists(params.file_path):
            return {"error": f"Archivo local no encontrado: {params.file_path}"}

        try:
            metadata = None
            if params.metadata_json:
                import json
                try:
                    metadata = json.loads(params.metadata_json)
                except json.JSONDecodeError:
                    return {"error": "Formato de metadata_json inválido."}

            # Adaptación para llamada síncrona
            result = await run_sync_in_executor(
                data_manager_instance.upload_file,
                file_path=params.file_path,
                metadata=metadata
            )
            return result
        except DataManagerApiError as e: # Usar el alias
            context.log.error(f"Error de API al subir archivo {params.file_path}: {e}")
            return {"error": str(e), "status_code": e.status_code, "details": e.response_text}
        except Exception as e:
            context.log.error(f"Error inesperado al subir archivo {params.file_path}: {e}")
            return {"error": f"Error inesperado: {str(e)}"}

else:
    logging.warning("Las herramientas de Data Management no estarán disponibles porque DataManager no se inicializó.")


# --- Herramientas de Design Automation ---
if design_auto_service_instance:
    @mcp_server.tool()
    async def list_cad_engines(context: MCPContext) -> List[Dict[str, Any]]:
        """Lista los motores CAD de Design Automation disponibles y sus formatos soportados."""
        context.log.info("Listando motores CAD disponibles.")
        if not design_auto_service_instance:
             return [{"error": "DesignAutomationService no está disponible."}] # Devolver lista con error
        # Esta llamada es síncrona pero muy rápida (lectura de memoria)
        return design_auto_service_instance.list_available_engines()

    @mcp_server.tool()
    async def run_cad_workflow(params: CADWorkflowParams, context: MCPContext) -> Dict[str, Any]:
        """
        Ejecuta un workflow de Design Automation.
        Requiere una definición de workflow en formato JSON (workflow_definition_json).
        """
        context.log.info(f"Solicitud para ejecutar workflow CAD.")
        if not design_auto_service_instance:
            return {"error": "DesignAutomationService no está disponible."}

        try:
            import json
            workflow_def = json.loads(params.workflow_definition_json)
        except json.JSONDecodeError:
            context.log.error("Error al parsear workflow_definition_json.")
            return {"error": "workflow_definition_json inválido. Debe ser un JSON string."}

        try:
            # Adaptación para llamada síncrona
            # run_workflow puede ser de larga duración. En producción, esto debería ser una tarea en background.
            context.log.info(f"Iniciando ejecución síncrona (en executor) del workflow: {workflow_def.get('name')}")

            # Aquí es donde el manejo de paths temporales se vuelve crucial.
            # DesignAutomationService crea sus propios directorios temporales.
            # Si se ejecuta en un contenedor, estos paths deben ser válidos dentro del contenedor.

            result_file_id = await run_sync_in_executor(
                design_auto_service_instance.run_workflow,
                workflow_definition=workflow_def
            )
            context.log.info(f"Workflow CAD completado. ID del archivo resultado: {result_file_id}")
            return {"status": "success", "result_file_id": result_file_id}
        except (CADProcessingError, CADFileNotFoundError, DataManagerApiError) as e: # Usar el alias
            context.log.error(f"Error específico del workflow CAD: {e}")
            return {"error": f"Error en workflow CAD: {str(e)}"}
        except ValueError as e: # Ej. motor no encontrado, input_file_id faltante
             context.log.error(f"Error de valor en workflow CAD: {e}")
             return {"error": f"Error de configuración del workflow: {str(e)}"}
        except Exception as e:
            context.log.error(f"Error inesperado ejecutando workflow CAD: {e}", exc_info=True)
            return {"error": f"Error inesperado en workflow: {str(e)}"}
else:
    logging.warning("Las herramientas de Design Automation no estarán disponibles porque DesignAutomationService no se inicializó.")


# --- Endpoint de Callback para OAuth (si es necesario manejarlo aquí) ---
# FastMCP puede exponer endpoints HTTP normales también, o integrarse con FastAPI/Starlette.
# Si el flujo OAuth es "authorization_code", el redirect URI necesita un handler.
# Este es un ejemplo muy básico. En una app real, se usaría `mcp_server.mount_asgi_app`
# con una app FastAPI/Starlette que defina el endpoint.
# O si FastMCP tiene una forma nativa de definir rutas HTTP simples.

# @mcp_server.route("/oauth/callback", methods=["GET"]) # Sintaxis hipotética para FastMCP route
async def oauth_callback_handler(request): # `request` sería un objeto tipo Starlette/FastAPI Request
    """
    Maneja el callback de OAuth2 después de que el usuario autoriza la aplicación.
    Extrae el 'code' y lo intercambia por un token.
    """
    # Esto es pseudocódigo. La integración real depende de cómo FastMCP expone las requests HTTP.
    # Asumimos que podemos obtener `code` y `state` de `request.query_params`.
    auth_code = request.query_params.get("code")
    state = request.query_params.get("state") # Debería validarse contra uno guardado en sesión

    logging.info(f"OAuth callback recibido. Código: {'presente' if auth_code else 'ausente'}, Estado: {state}")

    if not auth_code:
        return {"error": "No se recibió código de autorización en el callback."} # Respuesta JSON

    if not oauth_client_instance:
        return {"error": "OAuthClient no está disponible para procesar el callback."}

    try:
        # Adaptación para llamada síncrona
        token_data = await run_sync_in_executor(
            oauth_client_instance.exchange_code_for_token,
            authorization_code=auth_code
        )
        logging.info(f"Token intercambiado exitosamente a través de callback. Access token (parcial): {str(token_data.get('access_token'))[:20]}...")
        # En una app web, aquí redirigirías al usuario o mostrarías un mensaje de éxito.
        # Para una API, simplemente devolver el estado o el token (aunque devolver el token aquí es riesgoso).
        return {"status": "success", "message": "Autenticación OAuth completada. Puedes cerrar esta ventana."}
    except Exception as e:
        logging.error(f"Error al intercambiar código por token en callback: {e}")
        return {"error": f"Fallo en el intercambio de token: {str(e)}"}

# Para integrar el callback con la app ASGI principal:
# Necesitaríamos una app Starlette/FastAPI y montarla.
try:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def actual_http_oauth_callback(request: Request):
        # Aquí va la lógica de oauth_callback_handler, pero usando Starlette Request/Response
        auth_code = request.query_params.get("code")
        state = request.query_params.get("state")
        logging.info(f"Callback OAuth HTTP recibido. Código: {'presente' if auth_code else 'ausente'}, Estado: {state}")

        if not auth_code:
            return JSONResponse({"error": "No se recibió código de autorización en el callback."}, status_code=400)
        if not oauth_client_instance:
             return JSONResponse({"error": "OAuthClient no está disponible para procesar el callback."}, status_code=500)
        try:
            token_data = await run_sync_in_executor(oauth_client_instance.exchange_code_for_token, authorization_code=auth_code)
            logging.info(f"Token intercambiado exitosamente. Access token (parcial): {str(token_data.get('access_token'))[:20]}...")
            return JSONResponse({"status": "success", "message": "Autenticación OAuth completada."})
        except Exception as e:
            logging.error(f"Error al intercambiar código por token en callback: {e}")
            return JSONResponse({"error": f"Fallo en el intercambio de token: {str(e)}"}, status_code=500)

    # Crear una app Starlette solo para el callback
    # El path del redirect URI debe coincidir con OAUTH_REDIRECT_URI
    # ej. si OAUTH_REDIRECT_URI es http://localhost:8080/mcp/oauth/callback
    # el path para la ruta aquí sería "/mcp/oauth/callback"
    # Vamos a asumir que OAUTH_REDIRECT_URI es "http://localhost:<port>/oauth/callback"
    # y que el servidor FastMCP se sirve en la raíz.
    parsed_redirect_uri = None
    if config.oauth_redirect_uri:
        from urllib.parse import urlparse
        parsed_redirect_uri = urlparse(config.oauth_redirect_uri)

    callback_path = parsed_redirect_uri.path if parsed_redirect_uri else "/oauth/callback"

    http_app = Starlette(routes=[
        Route(callback_path, endpoint=actual_http_oauth_callback, methods=["GET"]),
    ])

    # Montar esta app en el servidor FastMCP
    # El path de montaje debe ser el prefijo común si OAUTH_REDIRECT_URI tiene subdirectorios
    # que no son parte del path de la ruta en sí.
    # Ejemplo: si redirect URI es /api/v1/oauth/callback, y la ruta en Starlette es /oauth/callback,
    # entonces se monta en /api/v1.
    # Si el path de la ruta ya es el path completo del URI, montar en "/".
    mcp_server.mount_asgi_app(http_app, path="/") # Montar en la raíz para que el callback_path funcione directamente
    logging.info(f"Endpoint de callback OAuth configurado en: {callback_path}")

except ImportError:
    logging.warning("Starlette no está instalado. El endpoint de callback OAuth HTTP no estará disponible.")
    logging.warning("Instala Starlette con 'pip install starlette' si necesitas manejar el callback OAuth.")


# --- Ejecución del Servidor ---
if __name__ == "__main__":
    # Usar create_app para obtener la aplicación ASGI completa que incluye la UI web de FastMCP (Swagger/Redoc)
    # y los endpoints del servidor MCP.
    app = create_app(mcp_server)

    logging.info(f"Iniciando servidor FastMCP en http://{config.server_host}:{config.server_port}")
    logging.info("Presiona CTRL+C para detener el servidor.")

    # Verificar si las variables OAuth están configuradas, advertir si no.
    if not all([config.oauth_client_id, config.oauth_client_secret, config.oauth_auth_url, config.oauth_token_url]):
        logging.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logging.warning("!!! ADVERTENCIA: Variables de entorno OAuth no están completamente configuradas !!!")
        logging.warning("!!! El flujo de autenticación OAuth y las herramientas que dependen de él    !!!")
        logging.warning("!!! probablemente no funcionarán. Revisa tu archivo .env o el entorno.      !!!")
        logging.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        if not os.path.exists(".env"):
            logging.warning("No se encontró archivo .env. Crea uno con las variables necesarias.")
        else:
            logging.warning(f"Archivo .env encontrado en {os.path.abspath('.env')}. Verifica su contenido.")

    uvicorn.run(app, host=config.server_host, port=config.server_port, log_level=config.log_level.lower())

# Consideraciones Finales:
# 1. Asincronía: La adaptación con `run_sync_in_executor` es una muleta. Idealmente,
#    OAuthClient, DataManager y DesignAutomationService (y sus motores) deberían ser
#    nativamente asíncronos usando `httpx` para llamadas de red y `aiofiles` para E/S de archivos.
#    Las operaciones de larga duración (como `run_workflow`) deberían ser manejadas por un sistema
#    de colas de tareas (Celery, RQ, Dramatiq) para no bloquear el event loop de asyncio.
# 2. Seguridad de Endpoints:
#    - El `destination_path` en `download_mcp_file` y `file_path` en `upload_mcp_file`
#      son problemáticos para un servidor expuesto. Deben ser validados cuidadosamente o,
#      mejor aún, gestionados internamente por el servidor (ej. subidas a un área de staging,
#      descargas desde una ubicación controlada o streaming directo del contenido).
#    - El callback OAuth debería validar el parámetro `state` para prevenir CSRF.
# 3. Gestión de Estado y Sesiones: Para el flujo OAuth y el parámetro `state`, se necesita
#    alguna forma de gestión de sesión si el servidor va a ser usado por múltiples usuarios
#    a través de una interfaz web. FastMCP está más orientado a ser un backend para LLMs o
#    aplicaciones, donde el cliente podría manejar el estado.
# 4. Robustez y Manejo de Errores: Aunque se ha añadido manejo de errores, en producción
#    se necesitaría un logging y monitoreo más exhaustivos.
# 5. Configuración de Motores CAD: La carga de configuración de motores CAD es muy básica.
#    Un sistema más dinámico (ej. plugins, configs en YAML/JSON) sería más flexible.
# 6. Pruebas de Integración: Se necesitarían tests de integración para verificar que todas
#    las partes funcionan juntas correctamente, incluyendo la interacción con un servidor MCP
#    (real o mockeado) y un proveedor OAuth (mockeado).
# 7. UI Web de FastMCP: `create_app` genera automáticamente interfaces como Swagger UI
#    para interactuar con las herramientas. Esto es útil para desarrollo y pruebas.
#
# Este `main_server.py` ensambla los componentes desarrollados. Los puntos más críticos
# para mejorar hacia un estado de producción son la asincronía completa y la seguridad
# de los endpoints que manejan rutas de archivos.
#
# Para ejecutar:
# - Asegúrate de tener todas las dependencias: fastmcp, uvicorn, requests, cryptography, python-dotenv, starlette (opcional para callback HTTP)
# - Configura tu archivo `.env` con las credenciales OAuth, URLs, etc.
# - Ejecuta `python main_server.py`
# - Accede a la UI de FastMCP (usualmente en http://localhost:8080/docs o /redoc) para ver las herramientas.
#
# Si falta `mock_cad_script.py` (del ejemplo de DesignAutomationService), el motor de ejemplo no se cargará correctamente.
# Deberías crear ese script o ajustar la carga de configuración del motor.
# El `ExampleScriptEngine` y su config en `server_config.py` asumen que `mock_cad_script.py` existe.
# Si no, aparecerá un warning pero el servidor debería iniciar.
#
# Si el `oauth_redirect_uri` en `.env` es, por ejemplo, `http://localhost:8080/myapp/callback`,
# entonces el `callback_path` debería ser `/myapp/callback` y el montaje de `http_app`
# podría necesitar ser en `/myapp` si la ruta en Starlette es solo `/callback`.
# La configuración actual asume que el path en el URI y el path en la ruta de Starlette coinciden
# y el servidor se monta en la raíz.
# Ejemplo: OAUTH_REDIRECT_URI = "http://localhost:8080/oauth/callback"
#          callback_path = "/oauth/callback"
#          Starlette Route path = "/oauth/callback"
#          mcp_server.mount_asgi_app(http_app, path="/") -> El callback estará en /oauth/callback
# Esto es correcto.
#
# Si `OAUTH_REDIRECT_URI` es, por ejemplo, `http://localhost:8080/api/v1/oauth_callback_endpoint`
# Entonces `callback_path` sería `/api/v1/oauth_callback_endpoint`.
# La `Route` en Starlette debería ser `Route("/api/v1/oauth_callback_endpoint", ...)`
# Y el montaje en `mcp_server` seguiría siendo `path="/"`.
# La implementación actual de `callback_path` y `Route(callback_path, ...)` es correcta.
#
# Es importante que `OAUTH_REDIRECT_URI` en `.env` coincida exactamente con lo registrado
# en el proveedor OAuth, y que el servidor exponga el endpoint en esa misma ruta.
#
# El `destination_path` en `download_mcp_file`:
# La herramienta actual lo expone como parámetro. Esto es inseguro.
# Alternativas:
# 1. La herramienta genera un path seguro en el servidor, descarga allí y devuelve ese path.
#    (Requiere que el cliente pueda acceder a ese path o que sea relativo a un workspace conocido).
# 2. La herramienta devuelve el contenido del archivo directamente (Base64 encoded, o como stream si MCP lo soporta).
#    FastMCP podría tener formas de manejar respuestas binarias.
# 3. La herramienta devuelve un ID de un "job de descarga" y otro endpoint/tool permite obtener el archivo.
#
# Por simplicidad, el ejemplo actual mantiene el `destination_path` como parámetro,
# pero esto es una gran advertencia de seguridad/diseño.
#
# Similarmente para `upload_mcp_file` y `file_path`.
# Alternativas:
# 1. Un endpoint HTTP separado para subir el archivo (multipart/form-data) que lo ponga en un staging area
#    y devuelva un ID. Luego la tool usa ese ID.
# 2. La tool acepta el contenido del archivo como un string Base64 (malo para archivos grandes).
# FastMCP (o la app ASGI montada) puede manejar subidas de archivos directamente.
#
# Estos son problemas comunes al diseñar APIs de archivos. El código actual es una primera pasada.
