# Módulo para enviar indicaciones a DeepSeek y obtener respuesta

import os
import requests # Necesitarás instalar esta librería: pip install requests
from dotenv import load_dotenv # Necesitarás: pip install python-dotenv

# Cargar variables de entorno desde .env
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions" # Confirmar la URL correcta en la documentación de DeepSeek

class DeepSeekAIClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        if not self.api_key:
            raise ValueError("DeepSeek API Key no encontrada. Asegúrate de configurarla en el archivo .env o pasarla al constructor.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _call_deepseek_api(self, messages, model="deepseek-chat", temperature=0.7, max_tokens=1024):
        """
        Función base para llamar a la API de chat de DeepSeek.
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Otros parámetros como stream, top_p, etc., pueden ser añadidos aquí.
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=self.headers, json=payload)
            response.raise_for_status()  # Lanza un error para respuestas HTTP 4xx/5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al llamar a la API de DeepSeek: {e}")
            if response is not None:
                print(f"Respuesta del servidor: {response.text}")
            return None

    def interpret_prompt(self, prompt: str, context_data: dict = None) -> dict:
        """
        Interpreta una instrucción en lenguaje natural para convertirla en acciones o parámetros.
        - prompt: La instrucción del usuario en español.
        - context_data: Datos adicionales del modelo RSTAB o del estado actual que puedan ser útiles.
        Retorna un diccionario con la interpretación (ej. acciones, parámetros, elementos afectados).
        """
        # TODO: Refinar el prompt del sistema para guiar mejor a DeepSeek
        # Se podría incluir información sobre la estructura esperada de la respuesta JSON.
        system_message_content = (
            "Eres un asistente experto en ingeniería estructural que interpreta instrucciones "
            "para modificar modelos en Dlubal RSTAB. Tu objetivo es traducir la instrucción del usuario "
            "a un formato estructurado (JSON) que pueda ser utilizado por un script para interactuar con RSTAB. "
            "La instrucción estará en español.\n"
            "Considera los siguientes tipos de acciones comunes: 'crear_elemento', 'modificar_elemento', "
            "'eliminar_elemento', 'definir_carga', 'consultar_propiedades', 'ejecutar_analisis', 'exportar_resultados'.\n"
            "Especifica los parámetros clave como 'tipo_elemento' (viga, columna, losa, zapata, etc.), "
            "'material', 'seccion_transversal', 'coordenadas', 'magnitud_carga', 'normativa_diseno', etc.\n"
            "Si la instrucción es ambigua o incompleta para generar una acción clara, indícalo."
        )

        if context_data:
            system_message_content += f"\nContexto adicional del modelo actual: {str(context_data)}"

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": prompt}
        ]

        print(f"Enviando prompt a DeepSeek para interpretación: \"{prompt}\"")
        api_response = self._call_deepseek_api(messages)

        if api_response and api_response.get("choices"):
            try:
                # Asumimos que la respuesta de DeepSeek contendrá un JSON en el contenido del mensaje
                content = api_response["choices"][0]["message"]["content"]
                # Podrías necesitar un post-procesamiento para asegurar que sea un JSON válido
                # o instruir a DeepSeek para que siempre devuelva JSON.
                # Por ahora, devolvemos el contenido directamente.
                # Idealmente, esto sería un diccionario Python parseado desde un JSON.
                # Ejemplo: return json.loads(content)
                print(f"Respuesta de DeepSeek (interpret_prompt): {content}")
                # Placeholder para la estructura de retorno esperada
                return {"interpreted_actions": content, "original_prompt": prompt}
            except (KeyError, IndexError) as e:
                print(f"Error al parsear la respuesta de DeepSeek: {e}")
                return {"error": "Formato de respuesta inesperado de DeepSeek", "details": str(api_response)}
        else:
            return {"error": "No se recibió respuesta válida de DeepSeek", "details": str(api_response)}


    def suggest_design_change(self, task_data: dict, mexico_code_rules: dict = None) -> dict:
        """
        Sugiere cambios de diseño basados en una tarea interpretada y normativas.
        - task_data: Diccionario proveniente de `interpret_prompt` o una descripción de la tarea.
        - mexico_code_rules: Un diccionario o estructura con reglas de diseño mexicanas relevantes.
        Retorna un diccionario con las sugerencias de cambio para RSTAB.
        """
        # TODO: Refinar el prompt del sistema para guiar a DeepSeek en la sugerencia de diseño.
        # Incluir información sobre cómo aplicar las normativas mexicanas.
        system_message_content = (
            "Eres un asistente experto en ingeniería estructural especializado en normativas mexicanas (NTC, CFE, AISC-LRFD). "
            "Dada una tarea de diseño o modificación estructural, y opcionalmente un conjunto de reglas de diseño, "
            "genera una sugerencia detallada de los cambios a aplicar en un modelo de RSTAB. "
            "La respuesta debe ser un JSON que describa las modificaciones (ej. nuevas secciones, materiales, dimensiones)."
            "Prioriza la seguridad, eficiencia y cumplimiento normativo."
        )

        user_prompt = f"Tarea de diseño: {task_data.get('interpreted_actions', task_data)}. "
        if mexico_code_rules:
            user_prompt += f"Considerar las siguientes reglas de diseño: {str(mexico_code_rules)}. "
        user_prompt += "Por favor, proporciona los cambios sugeridos en formato JSON para RSTAB."

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": user_prompt}
        ]

        print(f"Enviando tarea a DeepSeek para sugerencia de diseño: \"{task_data}\"")
        api_response = self._call_deepseek_api(messages, model="deepseek-chat") # Podrías usar un modelo más avanzado si está disponible

        if api_response and api_response.get("choices"):
            try:
                content = api_response["choices"][0]["message"]["content"]
                print(f"Respuesta de DeepSeek (suggest_design_change): {content}")
                # Idealmente, esto sería un diccionario Python parseado desde un JSON.
                # Ejemplo: return json.loads(content)
                return {"design_suggestions": content, "based_on_task": task_data}
            except (KeyError, IndexError) as e:
                print(f"Error al parsear la respuesta de DeepSeek: {e}")
                return {"error": "Formato de respuesta inesperado de DeepSeek", "details": str(api_response)}
        else:
            return {"error": "No se recibió respuesta válida de DeepSeek", "details": str(api_response)}

if __name__ == '__main__':
    # Ejemplo de uso (requiere que DEEPSEEK_API_KEY esté en .env)
    if not DEEPSEEK_API_KEY:
        print("Advertencia: DEEPSEEK_API_KEY no está configurada. Las llamadas a la API fallarán.")
        print("Por favor, crea un archivo .env con tu API Key o establece la variable de entorno.")
    else:
        ai_client = DeepSeekAIClient()

        # Ejemplo 1: Interpretar una instrucción simple
        prompt_usuario = "Rediseñar vigas de acero con perfil IPR en acero A992 según LRFD 2021."
        # Podrías pasar datos del modelo actual si los tuvieras:
        # context = {"current_beams": [{"id": 1, "section": "IPE200", "material": "S235"}, ...]}
        # interpretacion = ai_client.interpret_prompt(prompt_usuario, context_data=context)
        interpretacion = ai_client.interpret_prompt(prompt_usuario)
        print("\n--- Interpretación del Prompt ---")
        print(interpretacion)

        # Ejemplo 2: Sugerir un cambio de diseño (basado en una interpretación o tarea)
        if interpretacion and not interpretacion.get("error"):
            # Suponiendo que la interpretación ya es suficiente para una tarea
            # o que tienes reglas de `mexico_codes.py` para pasar.
            # reglas_ntc_ejemplo = {"concreto": {"resistencia_minima_fc": 250}} # kg/cm2
            # sugerencias = ai_client.suggest_design_change(
            #    task_data=interpretacion,
            #    mexico_code_rules=reglas_ntc_ejemplo
            # )
            sugerencias = ai_client.suggest_design_change(task_data=interpretacion)
            print("\n--- Sugerencias de Diseño ---")
            print(sugerencias)

        # Ejemplo 3: Otra instrucción
        prompt_cimentacion = "Modificar la cimentación de zapata aislada por una combinada según NTC-CDMX para las columnas C1 y C2."
        interpretacion_cimentacion = ai_client.interpret_prompt(prompt_cimentacion)
        print("\n--- Interpretación del Prompt (Cimentación) ---")
        print(interpretacion_cimentacion)
        if interpretacion_cimentacion and not interpretacion_cimentacion.get("error"):
            sugerencias_cimentacion = ai_client.suggest_design_change(task_data=interpretacion_cimentacion)
            print("\n--- Sugerencias de Diseño (Cimentación) ---")
            print(sugerencias_cimentacion)
