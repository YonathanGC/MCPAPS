from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
import shutil
import subprocess
import uuid

# Suponiendo que DataManager y OAuthClient están disponibles para descargar/subir archivos CAD
from data_manager import DataManager
from oauth_client import OAuthClient

class CADEngineError(Exception):
    """Error base para problemas relacionados con el motor CAD."""
    pass

class CADFileNotFoundError(CADEngineError):
    """Error cuando un archivo CAD necesario no se encuentra."""
    pass

class CADProcessingError(CADEngineError):
    """Error durante el procesamiento de un archivo CAD por un motor."""
    pass


class BaseCADEngine(ABC):
    """Clase base abstracta para un motor de Design Automation."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.temp_dir_base = self.config.get("temp_dir_base", "_cad_temp")
        os.makedirs(self.temp_dir_base, exist_ok=True)

    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Devuelve una lista de formatos de archivo CAD soportados por este motor (ej. ['step', 'iges', 'stl'])."""
        pass

    @abstractmethod
    def modify_file(self, input_file_path: str, output_file_path: str, parameters: Dict[str, Any]) -> None:
        """
        Modifica un archivo CAD según los parámetros dados.
        Lee de input_file_path y escribe el resultado en output_file_path.
        Lanza CADProcessingError si la modificación falla.
        """
        pass

    def _create_temp_workspace(self) -> str:
        """Crea un directorio de trabajo temporal único."""
        temp_workspace = os.path.join(self.temp_dir_base, str(uuid.uuid4()))
        os.makedirs(temp_workspace, exist_ok=True)
        return temp_workspace

    def _cleanup_workspace(self, workspace_dir: str):
        """Limpia (elimina) el directorio de trabajo temporal."""
        if os.path.exists(workspace_dir) and workspace_dir.startswith(os.path.abspath(self.temp_dir_base)):
            shutil.rmtree(workspace_dir)
        else:
            print(f"Advertencia: Intento de limpiar un directorio no válido o fuera de la base: {workspace_dir}")


class ExampleScriptEngine(BaseCADEngine):
    """
    Un motor CAD de ejemplo que utiliza un script externo (ej. Python con una biblioteca CAD, o un ejecutable).
    Este es un placeholder y necesitaría un script real para funcionar.
    """
    def __init__(self, name: str = "ExampleScriptEngine", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.script_path = self.config.get("script_path")
        if not self.script_path:
            raise ValueError("La configuración de ExampleScriptEngine debe incluir 'script_path'.")
        if not os.path.exists(self.script_path) or not os.access(self.script_path, os.X_OK):
            # Podría ser un script de python, no necesariamente ejecutable por sí mismo
            # pero el intérprete sí. Aquí es una simplificación.
            print(f"Advertencia: script_path '{self.script_path}' no encontrado o no ejecutable.")


    def supported_formats(self) -> List[str]:
        # Esto debería consultarse del script o estar en la configuración
        return self.config.get("supported_formats", ["step", "stl", "iges", "any"])

    def modify_file(self, input_file_path: str, output_file_path: str, parameters: Dict[str, Any]) -> None:
        if not os.path.exists(input_file_path):
            raise CADFileNotFoundError(f"Archivo de entrada no encontrado: {input_file_path}")

        # Convertir parámetros a argumentos de línea de comandos. Esto es un ejemplo simple.
        # Un script real podría tomar un archivo JSON de parámetros.
        param_args = []
        for key, value in parameters.items():
            param_args.append(f"--{key}")
            param_args.append(str(value))

        # Comando para ejecutar el script. Ajustar según sea necesario.
        # Ejemplo: python /ruta/al/script.py --input /ruta/in --output /ruta/out --param1 val1
        command = [
            self.config.get("interpreter", "python"), # o directamente el script si es un ejecutable
            self.script_path,
            "--input", input_file_path,
            "--output", output_file_path
        ] + param_args

        print(f"Ejecutando motor CAD ({self.name}): {' '.join(command)}")
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=self.config.get("timeout", 300)) # Timeout de 5 mins

            if process.returncode != 0:
                error_message = f"Script CAD falló con código {process.returncode}.\n" \
                                f"Stdout: {stdout.decode(errors='ignore')}\n" \
                                f"Stderr: {stderr.decode(errors='ignore')}"
                raise CADProcessingError(error_message)

            if not os.path.exists(output_file_path):
                raise CADProcessingError(f"Script CAD completado pero no generó archivo de salida: {output_file_path}")

            print(f"Archivo CAD modificado generado: {output_file_path}")

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            error_message = f"Script CAD excedió el tiempo límite.\n" \
                            f"Stdout: {stdout.decode(errors='ignore')}\n" \
                            f"Stderr: {stderr.decode(errors='ignore')}"
            raise CADProcessingError(error_message)
        except Exception as e:
            raise CADProcessingError(f"Error ejecutando script CAD: {e}")


class DesignAutomationService:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.engines: Dict[str, BaseCADEngine] = {}
        self._temp_download_dir = "_da_downloads"
        os.makedirs(self._temp_download_dir, exist_ok=True)

    def register_engine(self, engine: BaseCADEngine):
        """Registra un nuevo motor CAD."""
        if engine.name in self.engines:
            print(f"Advertencia: El motor CAD '{engine.name}' ya está registrado. Será sobreescrito.")
        self.engines[engine.name] = engine
        print(f"Motor CAD '{engine.name}' registrado.")

    def get_engine(self, engine_name: str) -> Optional[BaseCADEngine]:
        """Obtiene un motor CAD por su nombre."""
        return self.engines.get(engine_name)

    def list_available_engines(self) -> List[Dict[str, Any]]:
        """Lista los motores CAD disponibles y sus formatos soportados."""
        return [
            {"name": name, "supported_formats": engine.supported_formats()}
            for name, engine in self.engines.items()
        ]

    def run_workflow(self, workflow_definition: Dict[str, Any]) -> str:
        """
        Ejecuta un workflow de automatización de diseño.
        Un workflow es una secuencia de pasos, donde cada paso usa un motor CAD.

        Formato esperado del workflow_definition (ejemplo):
        {
            "name": "MiWorkflowSimple",
            "input_file_id": "id_del_archivo_cad_original_en_mcp",
            "input_file_version": "latest", // opcional
            "steps": [
                {
                    "engine_name": "ExampleScriptEngine",
                    "parameters": {"param1": "valor1", "scale": 1.5},
                    "output_filename_suffix": "_mod1"
                },
                // Más pasos pueden seguir, usando la salida del anterior como entrada
            ],
            "output_metadata": {"description": "Resultado de MiWorkflowSimple"} // opcional
        }
        Devuelve el ID del archivo resultante subido al DataManager.
        """
        print(f"Iniciando workflow: {workflow_definition.get('name', 'Workflow Sin Nombre')}")

        input_file_id = workflow_definition.get("input_file_id")
        if not input_file_id:
            raise ValueError("El workflow debe especificar 'input_file_id'.")

        input_file_version = workflow_definition.get("input_file_version", "latest")

        current_file_path = None
        workspace_dir = None
        original_downloaded_filename = None

        try:
            # Crear un workspace temporal para este workflow
            # Usaremos el workspace del primer motor que se use, o uno genérico si no hay motores.
            # Mejor crear uno específico para el workflow.
            workspace_dir_base = self.engines.get(workflow_definition["steps"][0]["engine_name"]) if workflow_definition.get("steps") else None
            if workspace_dir_base and hasattr(workspace_dir_base, 'temp_dir_base'):
                 workspace_dir = os.path.join(workspace_dir_base.temp_dir_base, f"wf_{str(uuid.uuid4())}")
            else: # Fallback si el motor no tiene temp_dir_base o no hay pasos
                 workspace_dir = os.path.join(self._temp_download_dir, f"wf_{str(uuid.uuid4())}")
            os.makedirs(workspace_dir, exist_ok=True)


            # 1. Descargar el archivo de entrada inicial
            print(f"Descargando archivo de entrada ID: {input_file_id} (versión: {input_file_version})")
            # El DataManager debería poder devolver la ruta al archivo descargado o su nombre.
            # Por ahora, asumimos que lo descarga a un directorio y podemos predecir/obtener el nombre.
            # Vamos a hacer que DataManager.download_file guarde en un path específico que le damos.

            # Necesitamos un nombre de archivo para la descarga inicial.
            # Podríamos obtenerlo de un `get_file_metadata(input_file_id)` o usar el ID.
            # Por simplicidad, intentaremos construir un path.
            # DataManager.download_file ahora crea el directorio si es un path completo.
            initial_download_path_placeholder = os.path.join(workspace_dir, input_file_id + "_initial_download")
            self.data_manager.download_file(input_file_id, initial_download_path_placeholder, version=input_file_version)

            # DataManager.download_file ahora maneja si el path es dir o file.
            # Si es dir, usa el nombre del header o file_id. Necesitamos saber cuál fue.
            # Vamos a asumir que si initial_download_path_placeholder es un dir, el archivo estará DENTRO.
            # Si es un archivo, será ESE archivo.
            # Mejorar: download_file podría devolver el path final del archivo.
            # Solución temporal: buscar el archivo descargado en el workspace_dir.
            # Esto es frágil. DataManager.download_file debería ser más explícito.

            # Asumimos que download_file guarda directamente con el nombre correcto en el dir.
            # Si initial_download_path_placeholder era `dir/file_id_initial_download` y se descargó `realname.step`
            # entonces el archivo es `dir/realname.step`.
            # Si `download_file` usó `file_id` como nombre porque no había header, será `dir/file_id`.

            # Vamos a hacer que download_file guarde el archivo con un nombre predecible si el path es un directorio.
            # Por ahora, para simplificar, asumimos que el archivo descargado es el único en initial_download_path_placeholder
            # o que tiene un nombre deducible.
            # HACK: Si initial_download_path_placeholder fue usado como archivo, es current_file_path.
            #       Si fue usado como directorio, buscar el archivo dentro.

            # Modificación en data_manager.py (mental): download_file(file_id, dest_path)
            # si dest_path es un dir, el archivo se guarda como os.path.join(dest_path, determined_filename)
            # y esta función devuelve el path completo al archivo.
            # Por ahora, asumimos que el archivo es el único en workspace_dir o tiene un nombre conocido.
            # Vamos a simplificar: download_file descarga a un nombre predecible.
            # Supongamos que el archivo se llama como el file_id dentro del workspace_dir, y la extensión se infiere o se maneja.
            # Esto es un punto débil. El DataManager debería informar el nombre real del archivo descargado.

            # Parche: Asumimos que download_file guarda el archivo con un nombre predecible
            # o que podemos encontrarlo.
            # Por ahora, usaremos un nombre fijo para la entrada y salida de cada paso.

            # El archivo descargado se llamará como el file_id o el nombre del header.
            # Vamos a asumir que DataManager.download_file ahora devuelve el path completo del archivo descargado.
            # (Esto es un cambio hipotético en DataManager para que esto funcione limpiamente)
            # Simulación del cambio:
            # current_file_path = self.data_manager.download_file_and_get_path(input_file_id, workspace_dir, version=input_file_version)

            # Solución sin cambiar DataManager:
            # Descargamos a un directorio temporal específico para este archivo.
            download_target_dir = os.path.join(workspace_dir, "input_0")
            os.makedirs(download_target_dir, exist_ok=True)
            self.data_manager.download_file(input_file_id, download_target_dir, version=input_file_version)
            downloaded_files = os.listdir(download_target_dir)
            if not downloaded_files:
                raise CADFileNotFoundError(f"No se descargó ningún archivo para ID {input_file_id} en {download_target_dir}")
            if len(downloaded_files) > 1:
                print(f"Advertencia: Múltiples archivos descargados para {input_file_id}. Usando el primero: {downloaded_files[0]}")
            original_downloaded_filename = downloaded_files[0]
            current_file_path = os.path.join(download_target_dir, original_downloaded_filename)


            # 2. Ejecutar cada paso del workflow
            for i, step in enumerate(workflow_definition.get("steps", [])):
                engine_name = step.get("engine_name")
                engine = self.get_engine(engine_name)
                if not engine:
                    raise ValueError(f"Motor CAD '{engine_name}' no encontrado para el paso {i+1}.")

                print(f"Ejecutando paso {i+1}/{len(workflow_definition['steps'])} con motor '{engine_name}'...")

                # Determinar el nombre del archivo de salida para este paso
                # Usar el nombre original, añadir sufijo, mantener extensión.
                base, ext = os.path.splitext(original_downloaded_filename)
                output_filename = f"{base}{step.get('output_filename_suffix', f'_step{i+1}')}{ext}"
                output_file_path = os.path.join(workspace_dir, output_filename)

                engine.modify_file(current_file_path, output_file_path, step.get("parameters", {}))

                # La salida de este paso es la entrada del siguiente
                current_file_path = output_file_path
                original_downloaded_filename = output_filename # Actualizar para el siguiente sufijo

            # 3. Subir el archivo resultante final
            if not current_file_path or not os.path.exists(current_file_path):
                raise CADProcessingError("El workflow no produjo un archivo de salida final.")

            print(f"Subiendo archivo resultante: {current_file_path}")
            output_metadata = workflow_definition.get("output_metadata", {})
            if "original_input_id" not in output_metadata:
                output_metadata["original_input_id"] = input_file_id
            if "workflow_name" not in output_metadata:
                 output_metadata["workflow_name"] = workflow_definition.get('name', 'Workflow Sin Nombre')

            upload_response = self.data_manager.upload_file(current_file_path, metadata=output_metadata)

            result_file_id = upload_response.get("id")
            if not result_file_id:
                raise UploadError("La subida del archivo resultante no devolvió un ID.")

            print(f"Workflow completado. Archivo resultante subido con ID: {result_file_id}")
            return result_file_id

        except Exception as e:
            print(f"Error durante la ejecución del workflow: {e}")
            # Podríamos querer subir un log de error o un estado de fallo.
            raise # Re-lanzar la excepción para que sea manejada externamente.
        finally:
            # 4. Limpiar el workspace temporal
            if workspace_dir and os.path.exists(workspace_dir):
                # Para motores que usan su propio sistema de temp, no limpiar aquí.
                # El motor es responsable de su propio _create_temp_workspace y _cleanup_workspace
                # Este workspace_dir es para el workflow en general (descargas, salidas intermedias).
                # shutil.rmtree(workspace_dir)
                # print(f"Workspace del workflow {workspace_dir} limpiado.")
                # Dejamos la limpieza del workspace del motor al motor mismo.
                # La limpieza del _temp_download_dir general o del workspace_dir del workflow:
                if workspace_dir.startswith(os.path.abspath(self._temp_download_dir)) or \
                   (workspace_dir_base and workspace_dir.startswith(os.path.abspath(workspace_dir_base.temp_dir_base))):
                    shutil.rmtree(workspace_dir)
                    print(f"Workspace del workflow {workspace_dir} limpiado.")
                else:
                    print(f"Advertencia: Workspace del workflow {workspace_dir} no se limpiará (ruta no esperada).")


# Ejemplo de uso
if __name__ == "__main__":
    print("Ejemplo de Design Automation Service:")

    # --- Configuración simulada ---
    # 1. Cliente OAuth (simulado, necesitaría configuración real para DataManager)
    class MockOAuthClient:
        def get_access_token(self):
            print("[MockOAuthClient] Solicitando token de acceso...")
            # Devolver un token falso si es necesario para pasar las comprobaciones iniciales
            # o None para simular que no hay token.
            # return "mock_access_token_string"
            # Para que el ejemplo de DataManager no intente usarlo si es None:
            if not all([os.getenv("OAUTH_CLIENT_ID"), os.getenv("OAUTH_CLIENT_SECRET"), os.getenv("OAUTH_AUTH_URL"), os.getenv("OAUTH_TOKEN_URL")]):
                print("[MockOAuthClient] Variables OAuth no configuradas, devolviendo None para el token.")
                return None
            return "mock_access_token_for_real_oauth_path_testing_if_vars_exist"


    # 2. DataManager (simulado para no hacer llamadas HTTP reales)
    class MockDataManager:
        def __init__(self, oauth_client):
            self.oauth_client = oauth_client
            self._mock_files = {} # Simula archivos en el servidor: {"id1": "ruta/local/simulada/file1.step"}
            self._mock_fs_base = "_mock_mcp_fs"
            os.makedirs(self._mock_fs_base, exist_ok=True)

        def download_file(self, file_id: str, destination_path: str, version: Optional[str] = "latest"):
            print(f"[MockDataManager] Intentando descargar file_id '{file_id}' (v: {version}) a '{destination_path}'")
            if file_id not in self._mock_files:
                raise DownloadError(f"Mock file_id '{file_id}' no encontrado.")

            source_file_content = self._mock_files[file_id].get("content", "Contenido de prueba CAD.")
            # Simular nombre de archivo desde header o usar file_id
            filename_to_save = self._mock_files[file_id].get("filename", f"{file_id}.mockcad")

            if os.path.isdir(destination_path):
                final_filepath = os.path.join(destination_path, filename_to_save)
            else: # destination_path es un path de archivo completo
                final_filepath = destination_path
                os.makedirs(os.path.dirname(final_filepath) or '.', exist_ok=True)

            with open(final_filepath, "w") as f:
                f.write(source_file_content)
            print(f"[MockDataManager] Archivo '{filename_to_save}' 'descargado' a '{final_filepath}'.")
            # En un DataManager real, esta función podría devolver el path final.
            # Aquí, el DesignAutomationService tendrá que deducirlo.

        def upload_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            print(f"[MockDataManager] Intentando subir archivo '{file_path}' con metadata: {metadata}")
            if not os.path.exists(file_path):
                raise UploadError(f"Mock upload: archivo local '{file_path}' no existe.")

            new_file_id = f"uploaded_{str(uuid.uuid4())[:8]}"
            # Simular "guardar" el archivo en el sistema de archivos mock del servidor
            mock_server_path = os.path.join(self._mock_fs_base, new_file_id + "_" + os.path.basename(file_path))
            shutil.copy(file_path, mock_server_path)

            self._mock_files[new_file_id] = {
                "path_on_server": mock_server_path,
                "filename": os.path.basename(file_path),
                "content": open(file_path, "r").read() # Para simplificar, si es texto
            }
            print(f"[MockDataManager] Archivo '{file_path}' 'subido' como ID '{new_file_id}'.")
            return {"id": new_file_id, "name": os.path.basename(file_path), "metadata": metadata}

        def add_mock_file(self, file_id: str, filename: str, content: str):
            """Método de ayuda para poblar el DataManager mock."""
            mock_path = os.path.join(self._mock_fs_base, filename)
            with open(mock_path, "w") as f:
                f.write(content)
            self._mock_files[file_id] = {"path_on_server": mock_path, "filename": filename, "content": content}
            print(f"[MockDataManager] Archivo mock '{filename}' (ID: {file_id}) añadido.")


    # 3. Script CAD de ejemplo (crear un script python simple)
    example_script_content = """
import argparse
import os
import shutil

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock CAD Modification Script")
    parser.add_argument("--input", required=True, help="Input CAD file path")
    parser.add_argument("--output", required=True, help="Output CAD file path")
    parser.add_argument("--action", default="copy", help="Action to perform (e.g., 'copy', 'add_suffix')")
    parser.add_argument("--suffix", default="_modified", help="Suffix to add if action is 'add_suffix'")
    # Añadir más parámetros según sea necesario para simular la modificación
    parser.add_argument("--scale", type=float, help="A scale parameter example")


    args = parser.parse_args()
    print(f"Mock CAD Script: Input: {args.input}, Output: {args.output}, Action: {args.action}, Suffix: {args.suffix}, Scale: {args.scale}")

    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found!")
        exit(1)

    # Simular alguna modificación
    if args.action == "copy":
        shutil.copy(args.input, args.output)
        print(f"Mock CAD Script: Copied {args.input} to {args.output}")
    elif args.action == "add_suffix_to_content":
        with open(args.input, "r") as f_in, open(args.output, "w") as f_out:
            content = f_in.read()
            f_out.write(content + args.suffix)
        print(f"Mock CAD Script: Added suffix '{args.suffix}' to content of {args.input} and saved to {args.output}")
    else:
        # Por defecto, solo copia
        shutil.copy(args.input, args.output)
        print(f"Mock CAD Script: Action '{args.action}' desconocida, copiado por defecto.")

    # Simular que se usa el parámetro scale si existe
    if args.scale is not None:
        print(f"Mock CAD Script: Se aplicaría un escalado de {args.scale}.")

    if not os.path.exists(args.output):
        print(f"Error: El script no generó el archivo de salida {args.output}")
        exit(1)

    print("Mock CAD Script: Modificación completada exitosamente.")
    exit(0)
"""
    mock_script_path = os.path.join(os.getcwd(), "mock_cad_script.py")
    with open(mock_script_path, "w") as f:
        f.write(example_script_content)
    # Hacerlo ejecutable es opcional si se llama con `python mock_cad_script.py`
    # os.chmod(mock_script_path, 0o755)


    # --- Inicialización ---
    mock_oauth_client = MockOAuthClient()
    # Usar el DataManager real si se quiere probar con un servidor, o el MockDataManager
    # data_manager_instance = DataManager(mock_oauth_client) # Real
    data_manager_instance = MockDataManager(mock_oauth_client) # Mock

    # Añadir un archivo CAD de prueba al MockDataManager
    initial_cad_file_id = "cad123"
    initial_cad_filename = "robot_arm_base.step"
    initial_cad_content = "Este es el contenido simulado de un archivo STEP para el robot_arm_base."
    data_manager_instance.add_mock_file(initial_cad_file_id, initial_cad_filename, initial_cad_content)


    design_auto_service = DesignAutomationService(data_manager_instance)

    # Configurar y registrar el motor CAD de ejemplo
    engine_config = {
        "script_path": mock_script_path,
        "interpreter": "python", # Asegúrate de que 'python' está en el PATH o usa la ruta completa
        "supported_formats": ["step", "iges", "any"], # "any" para que el mock acepte cualquier cosa
        "timeout": 60 # segundos
    }
    example_engine = ExampleScriptEngine(name="MyPythonCADTool", config=engine_config)
    design_auto_service.register_engine(example_engine)

    print("\nMotores disponibles:", design_auto_service.list_available_engines())

    # --- Definir y ejecutar un workflow ---
    workflow_def = {
        "name": "ModificarRobotArmBase",
        "input_file_id": initial_cad_file_id,
        # "input_file_version": "1", # Opcional
        "steps": [
            {
                "engine_name": "MyPythonCADTool",
                "parameters": {
                    "action": "add_suffix_to_content", # Acción definida en el mock_cad_script.py
                    "suffix": "_v2_modified",
                    "scale": 2.0
                },
                "output_filename_suffix": "_mod_v2" # Sufijo para el nombre del archivo de salida
            }
            # Se podrían añadir más pasos aquí, por ejemplo, para convertir a otro formato
            # o aplicar más modificaciones.
        ],
        "output_metadata": {
            "description": "Robot arm base modificada a v2 y escalada.",
            "custom_prop": "valor_custom"
        }
    }

    print(f"\n--- Ejecutando workflow: {workflow_def['name']} ---")
    try:
        result_id = design_auto_service.run_workflow(workflow_def)
        print(f"--- Workflow completado exitosamente. ID del archivo resultante: {result_id} ---")

        # Verificar el archivo subido en el mock
        if isinstance(data_manager_instance, MockDataManager):
            if result_id in data_manager_instance._mock_files:
                print("Detalles del archivo resultante en MockDataManager:")
                print(data_manager_instance._mock_files[result_id])
                # Imprimir contenido del archivo "subido"
                uploaded_content_path = data_manager_instance._mock_files[result_id]["path_on_server"]
                with open(uploaded_content_path, "r") as f:
                    print(f"\nContenido del archivo '{os.path.basename(uploaded_content_path)}' (simulado en servidor):")
                    print(f.read())

    except Exception as e:
        print(f"--- Error en el workflow: {e} ---")
    finally:
        # Limpieza de archivos temporales creados por el ejemplo
        if os.path.exists(mock_script_path):
            os.remove(mock_script_path)
        if os.path.exists("_cad_temp"): # Directorio base del motor
            shutil.rmtree("_cad_temp", ignore_errors=True)
        if os.path.exists("_da_downloads"): # Directorio de descargas del servicio
            shutil.rmtree("_da_downloads", ignore_errors=True)
        if os.path.exists("_mock_mcp_fs"): # Directorio del MockDataManager
             shutil.rmtree("_mock_mcp_fs", ignore_errors=True)
        print("\nLimpieza de archivos de ejemplo completada.")

# Consideraciones para Design Automation:
# 1. Motores CAD Reales: `ExampleScriptEngine` es un placeholder. Para uso real, se necesitarían
#    implementaciones que interactúen con software CAD real (ej. FreeCAD, OpenSCAD, Onshape API,
#    Autodesk Forge, etc.). Esto puede implicar:
#    - Uso de APIs de Python para estos programas (ej. `freecadcmd` para FreeCAD).
#    - Llamadas a ejecutables de línea de comandos.
#    - Interacción con APIs web (requeriría manejo de autenticación adicional para esas APIs).
# 2. Formatos de Archivo: La conversión entre formatos puede ser un paso común en los workflows.
#    Cada motor debe declarar qué formatos de entrada/salida soporta.
# 3. Manejo de Parámetros: La forma en que los `parameters` del workflow se traducen a comandos
#    o configuraciones para el motor CAD es crucial y específica del motor.
# 4. Gestión de Workspaces: El manejo de archivos temporales (descargas, salidas intermedias,
#    archivos generados por el motor CAD) necesita ser robusto. La limpieza es importante.
#    Cada motor puede tener su propio método de workspace si es necesario.
# 5. Asincronía y Tareas de Larga Duración: Las modificaciones CAD pueden tardar mucho. En un
#    servidor FastMCP real, estas operaciones deberían ser asíncronas y posiblemente
#    manejadas por un sistema de colas de tareas (ej. Celery) para no bloquear el servidor.
#    El `DesignAutomationService` y los motores tendrían que ser `async`.
# 6. Seguridad: Si los motores ejecutan scripts o comandos externos, la validación de entradas
#    y el sandboxing pueden ser necesarios para prevenir vulnerabilidades.
# 7. Dependencias de Motores: Cada motor puede tener sus propias dependencias de software.
#    Esto es más un problema de despliegue (ej. contenedores Docker para cada motor o para el servicio).
# 8. Robustez del Workflow: ¿Qué sucede si un paso falla? ¿Se pueden reanudar workflows?
#    ¿Se guardan los resultados intermedios? El ejemplo actual es lineal y falla en el primer error.
# 9. Paralelización: Algunos workflows podrían tener pasos que se pueden ejecutar en paralelo.
# 10. Configuración de Motores: Los motores pueden necesitar configuraciones complejas (rutas a
#     ejecutables, claves de API para servicios CAD en la nube, etc.). Esto debería manejarse
#     a través de un sistema de configuración seguro.
# 11. DataManager Real: La interacción con un `DataManager` real (que usa `oauth_client` real)
#     es fundamental. El ejemplo usa mocks para ser autocontenido.
# 12. Logging Detallado: Cada paso del engine y del workflow debería tener un logging detallado.
#
# Este módulo establece una arquitectura base para la automatización del diseño.
# La clave está en la implementación de `BaseCADEngine` específicos para las herramientas CAD deseadas
# y la adaptación a un entorno asíncrono para FastMCP.
