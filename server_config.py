import os
from dotenv import load_dotenv
import logging
import sys

class ServerConfig:
    def __init__(self):
        # Cargar variables de entorno desde .env al inicio
        self.load_environment_variables()

        # Configuración de Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.log_file = os.getenv("LOG_FILE", None) # Si es None, se loguea a stdout/stderr
        self.setup_logging()

        # Variables de OAuth (ya definidas en oauth_client.py pero centralizamos su carga aquí)
        self.oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
        self.oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        self.oauth_auth_url = os.getenv("OAUTH_AUTH_URL")
        self.oauth_token_url = os.getenv("OAUTH_TOKEN_URL")
        self.oauth_redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/callback") # Default si no está en .env

        # Variables de Data Management
        self.mcp_data_api_base_url = os.getenv("MCP_DATA_API_BASE_URL")

        # Variables de Design Automation
        # Por ejemplo, rutas a ejecutables CAD, configuraciones de motores, etc.
        # Estas serían más específicas y podrían cargarse dinámicamente o desde otra sección del config.
        self.cad_engine_configs = self.load_cad_engine_configs() # Placeholder

        # Otras configuraciones del servidor FastMCP
        self.server_host = os.getenv("SERVER_HOST", "127.0.0.1")
        self.server_port = int(os.getenv("SERVER_PORT", "8080"))

        # Entorno (development, production, testing)
        self.environment = os.getenv("APP_ENV", "development").lower()

        # Testing automatizado (flags o configuraciones específicas para tests)
        self.is_testing_mode = (os.getenv("TESTING_MODE", "false").lower() == "true") or (self.environment == "testing")
        if self.is_testing_mode:
            self.setup_test_environment()

        # Clave de caché (ya definida en oauth_client.py, pero la idea es centralizar)
        # La generación/carga de la clave podría ser parte de la config si no la maneja oauth_client.
        self.token_cache_key_file = os.getenv("TOKEN_CACHE_KEY_FILE", "cache.key")


    def load_environment_variables(self):
        """Carga variables desde el archivo .env. Puede ser llamado explícitamente."""
        env_path = os.getenv("ENV_FILE_PATH", ".env")
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
            logging.info(f"Variables de entorno cargadas desde: {os.path.abspath(env_path)}")
        else:
            logging.warning(f"Archivo .env no encontrado en {os.path.abspath(env_path)}. Usando variables de entorno del sistema si existen.")

    def setup_logging(self):
        """Configura el sistema de logging para el servidor."""
        logging.basicConfig(
            level=self.log_level,
            format=self.log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout # Por defecto a stdout
        )

        root_logger = logging.getLogger()

        # Si se especifica un archivo de log, añadir un FileHandler
        if self.log_file:
            try:
                file_handler = logging.FileHandler(self.log_file, mode='a') # 'a' para append
                file_formatter = logging.Formatter(self.log_format)
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)
                logging.info(f"Logging configurado también para el archivo: {self.log_file}")
            except Exception as e:
                logging.error(f"No se pudo configurar el logging a archivo {self.log_file}: {e}")

        logging.info(f"Logging inicializado. Nivel: {self.log_level}, Formato: '{self.log_format}'")
        if self.log_level == "DEBUG":
            logging.debug("Modo DEBUG activado para logging.")


    def load_cad_engine_configs(self) -> dict:
        """
        Carga configuraciones para los motores CAD.
        Esto es un placeholder. En una aplicación real, podría cargar desde un archivo YAML/JSON,
        o desde variables de entorno con un prefijo específico.
        """
        # Ejemplo: buscar variables como CAD_ENGINE_MYENGINE_SCRIPT_PATH, CAD_ENGINE_MYENGINE_TYPE
        # O cargar un archivo de configuración de motores.
        configs = {}
        # Ejemplo de cómo se podría estructurar una config en .env:
        # MOCK_ENGINE_SCRIPT_PATH = "mock_cad_script.py"
        # MOCK_ENGINE_INTERPRETER = "python"
        # MOCK_ENGINE_FORMATS = "step,iges,stl"

        # Este es un ejemplo muy básico:
        if os.getenv("MOCK_ENGINE_SCRIPT_PATH"):
            configs["MyPythonCADTool"] = { # Coincide con el nombre usado en el ejemplo de design_automation_engine
                "script_path": os.getenv("MOCK_ENGINE_SCRIPT_PATH"),
                "interpreter": os.getenv("MOCK_ENGINE_INTERPRETER", "python"),
                "supported_formats": [f.strip() for f in os.getenv("MOCK_ENGINE_FORMATS", "step,any").split(',')],
                "timeout": int(os.getenv("MOCK_ENGINE_TIMEOUT", "300"))
            }
            logging.info(f"Configuración cargada para el motor CAD de ejemplo 'MyPythonCADTool': {configs['MyPythonCADTool']}")
        else:
            logging.info("No se encontró configuración para 'MOCK_ENGINE_SCRIPT_PATH' en el entorno. El motor de ejemplo podría no funcionar como se espera.")

        # Aquí se podrían añadir más lógicas para cargar otras configuraciones de motores.
        return configs

    def setup_test_environment(self):
        """Configuraciones específicas cuando se ejecuta en modo de prueba."""
        logging.info("Modo TESTING activado.")
        # Por ejemplo, usar una base de datos de prueba, URLs de API de prueba, etc.
        # Esto podría implicar sobreescribir algunas variables cargadas previamente.
        self.mcp_data_api_base_url = os.getenv("TEST_MCP_DATA_API_BASE_URL", self.mcp_data_api_base_url)
        # Asegurarse de que el logging sea verboso en testing si es necesario
        if self.log_level not in ["DEBUG"]:
             logging.getLogger().setLevel("DEBUG")
             logging.debug("Nivel de log forzado a DEBUG en modo TESTING.")

        # Podrías querer usar un archivo de caché de token diferente para tests
        self.token_cache_key_file = os.getenv("TEST_TOKEN_CACHE_KEY_FILE", "test_cache.key")
        token_cache_file = os.getenv("TEST_TOKEN_CACHE_FILE", "test_token_cache.enc")
        # Esto es más complejo porque TOKEN_CACHE_FILE se define en oauth_client.py
        # Una mejor manera sería que OAuthClient tome estos nombres de archivo de la configuración.
        # Por ahora, solo un log:
        logging.info(f"En modo test, se usaría idealmente un token_cache_file como '{token_cache_file}' y key '{self.token_cache_key_file}'.")


    def print_config_summary(self):
        """Imprime un resumen de la configuración cargada (cuidado con datos sensibles)."""
        summary = "\n--- Resumen de Configuración del Servidor ---\n"
        summary += f"Entorno de Aplicación (APP_ENV): {self.environment}\n"
        summary += f"Modo Testing: {'Activado' if self.is_testing_mode else 'Desactivado'}\n"
        summary += f"Nivel de Log: {self.log_level}\n"
        summary += f"Archivo de Log: {self.log_file or 'stdout/stderr'}\n"
        summary += f"Servidor Host: {self.server_host}\n"
        summary += f"Servidor Puerto: {self.server_port}\n"

        summary += f"OAuth Client ID: {'Configurado' if self.oauth_client_id else 'NO Configurado'}\n"
        # No imprimir client_secret
        summary += f"OAuth Auth URL: {self.oauth_auth_url or 'NO Configurado'}\n"
        summary += f"OAuth Token URL: {self.oauth_token_url or 'NO Configurado'}\n"
        summary += f"OAuth Redirect URI: {self.oauth_redirect_uri}\n"
        summary += f"Token Cache Key File: {self.token_cache_key_file}\n"

        summary += f"MCP Data API Base URL: {self.mcp_data_api_base_url or 'NO Configurado'}\n"

        summary += "Configuraciones de Motores CAD:\n"
        if self.cad_engine_configs:
            for name, cfg in self.cad_engine_configs.items():
                summary += f"  - Motor '{name}': script='{cfg.get('script_path', 'N/A')}', formatos={cfg.get('supported_formats', [])}\n"
        else:
            summary += "  (No se cargaron configuraciones específicas de motores CAD desde el entorno)\n"
        summary += "--------------------------------------------\n"

        # Usar logging.info para este resumen para que aparezca en logs
        # Dividir en múltiples llamadas a logging.info para legibilidad si es muy largo
        for line in summary.splitlines():
            logging.info(line)


# Crear una instancia global de la configuración para ser importada por otros módulos
# Esto sigue el patrón de singleton para la configuración.
config = ServerConfig()

if __name__ == "__main__":
    # Este bloque se ejecuta si server_config.py es el script principal.
    # Útil para verificar rápidamente la carga de configuración.

    print("Ejecutando server_config.py directamente para prueba.")

    # Crear un .env de ejemplo si no existe para esta prueba
    if not os.path.exists(".env"):
        print("Creando archivo .env de ejemplo para la prueba de server_config.py...")
        with open(".env", "w") as f:
            f.write("APP_ENV=development\n")
            f.write("LOG_LEVEL=DEBUG\n")
            f.write("LOG_FILE=server_test.log\n") # Para probar el logging a archivo
            f.write("OAUTH_CLIENT_ID=\"sample_client_id_from_env\"\n")
            f.write("MCP_DATA_API_BASE_URL=\"http://localhost:9000/api/test\"\n")
            f.write("MOCK_ENGINE_SCRIPT_PATH=\"./scripts/cad/mock_processor.py\"\n") # Ejemplo
            f.write("MOCK_ENGINE_FORMATS=\"step,iges\"\n")
        # Recargar la configuración si creamos el .env ahora
        config = ServerConfig()

    config.print_config_summary()

    logging.debug("Este es un mensaje de debug desde server_config.")
    logging.info("Este es un mensaje de info desde server_config.")
    logging.warning("Este es un mensaje de warning desde server_config.")
    logging.error("Este es un mensaje de error desde server_config.")
    logging.critical("Este es un mensaje critical desde server_config.")

    print(f"\nPara ver el log en archivo (si LOG_FILE está configurado en .env), revisa: {config.log_file}")
    print(f"APP_ENV actual: {config.environment}")
    print(f"Modo testing: {config.is_testing_mode}")

    # Ejemplo de cómo acceder a una configuración específica:
    # print(f"Client ID de OAuth: {config.oauth_client_id}")

# Consideraciones para Configuración Profesional:
# 1. Entorno Virtual Automatizado:
#    - El plan original mencionaba "Entorno virtual automatizado". Esto usualmente se refiere a
#      scripts de shell (activate.sh/bat) o herramientas como Poetry/PDM que manejan el entorno.
#      Python en sí no "automatiza" la creación del venv al iniciar una app, sino que se asume
#      que la app se ejecuta DENTRO de un venv ya activado.
#    - Lo que podemos hacer desde Python es verificar si se está en un venv:
#      `if sys.prefix == sys.base_prefix: logging.warning("No se está ejecutando en un entorno virtual.")`
#      Esto se podría añadir al inicio de la clase ServerConfig o al script principal del servidor.
#
# 2. Variables de Entorno Seguras:
#    - `python-dotenv` es bueno para desarrollo.
#    - En producción, las variables de entorno suelen ser inyectadas por el sistema de despliegue
#      (ej. Docker, Kubernetes secrets, variables de entorno del PaaS).
#    - Para secretos (como OAUTH_CLIENT_SECRET), se deben tomar precauciones adicionales:
#      - No loguearlos. (print_config_summary ya lo evita para el secret).
#      - Considerar el uso de gestores de secretos (HashiCorp Vault, AWS Secrets Manager, etc.)
#        e integrarlos para cargar estos valores en lugar de tenerlos en .env en producción.
#        Esto está fuera del alcance de este módulo de configuración simple.
#
# 3. Testing Automatizado (Configuración):
#    - `is_testing_mode` y `setup_test_environment` sientan las bases.
#    - Los frameworks de testing (pytest, unittest) usarían esto para, por ejemplo,
#      configurar bases de datos en memoria, mockear servicios externos, etc.
#    - `pytest` tiene mecanismos como `conftest.py` y fixtures que son más idóneos para
#      manejar la configuración específica de tests que hacerlo directamente en `ServerConfig`.
#      Pero `ServerConfig` puede leer una variable `APP_ENV=testing` para ajustar su comportamiento.
#
# 4. Logging Detallado:
#    - `setup_logging` implementa logging configurable a stdout y/o archivo.
#    - Se pueden añadir más handlers (SysLog, Sentry para errores, etc.).
#    - Estructura de logs (JSON logs) puede ser útil para sistemas de recolección de logs.
#
# 5. Modularidad de la Configuración:
#    - Para aplicaciones grandes, la configuración puede dividirse en más clases o módulos
#      (ej. `AuthConfig`, `DatabaseConfig`, `ServicesConfig`).
#
# 6. Validación de Configuración:
#    - Usar Pydantic (o similar) para definir modelos de configuración y validar que las
#      variables de entorno necesarias estén presentes y tengan el tipo correcto.
#      Ejemplo: `class OAuthSettings(BaseSettings): client_id: str; client_secret: SecretStr; ...`
#      Esto es altamente recomendado para robustez. FastMCP mismo usa Pydantic para settings.
#
# 7. Actualización en Caliente / Recarga de Configuración:
#    - No implementado. Algunos servidores pueden soportar recargar configuración sin reinicio.
#      Esto es complejo.
#
# Este módulo `server_config.py` provee una base sólida para la gestión de la configuración.
# La integración con Pydantic sería una mejora significativa para la validación.
# La automatización del venv es más un tema de scripts de proyecto/despliegue.
# La seguridad de secretos en producción requiere herramientas externas.
# El testing automatizado se apoyará en esto, pero su configuración detallada será parte del setup de tests.
