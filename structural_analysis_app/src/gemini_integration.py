import os
import google.generativeai as genai

# Cargar la API Key desde una variable de entorno
API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_CONFIGURED_SUCCESSFULLY = False

def configure_gemini_once():
    """Configura la API de Gemini con la API Key, solo una vez."""
    global GEMINI_CONFIGURED_SUCCESSFULLY
    if GEMINI_CONFIGURED_SUCCESSFULLY:
        return True
    if not API_KEY:
        print("Error: La variable de entorno GOOGLE_API_KEY no está configurada.")
        GEMINI_CONFIGURED_SUCCESSFULLY = False
        return False
    try:
        genai.configure(api_key=API_KEY)
        GEMINI_CONFIGURED_SUCCESSFULLY = True
        print("API de Gemini configurada exitosamente.")
        return True
    except Exception as e:
        print(f"Error al configurar Gemini: {e}")
        GEMINI_CONFIGURED_SUCCESSFULLY = False
        return False

def generate_text_with_gemini(prompt_text, model_name="gemini-pro"):
    """
    Genera texto usando el modelo Gemini especificado.

    Args:
        prompt_text (str): El prompt para enviar al modelo.
        model_name (str): El nombre del modelo a usar (ej. "gemini-pro").

    Returns:
        str: El texto generado por el modelo, o un mensaje de error si falla.
    """
    if not GEMINI_CONFIGURED_SUCCESSFULLY:
        if not configure_gemini_once():
             return "Error: API de Gemini no configurada. Verifica la GOOGLE_API_KEY."

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_text)

        # Debug: Imprimir la respuesta completa para inspección si es necesario
        # print(f"Respuesta completa de Gemini: {response}")

        if response and hasattr(response, 'text') and response.text:
            return response.text
        # A veces la respuesta está en parts, incluso si response.text está vacío o None
        if response and response.parts:
             return "".join(part.text for part in response.parts if hasattr(part, 'text'))
        # Estructura más profunda para algunos casos (basado en documentación y experiencia)
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
             return response.candidates[0].content.parts[0].text

        # Si no se encuentra texto, devolver un error específico
        print(f"Respuesta inesperada o vacía de Gemini. Prompt: '{prompt_text[:100]}...' Respuesta: {response}")
        return "Error: No se pudo extraer texto de la respuesta de Gemini o la respuesta estaba vacía."

    except Exception as e:
        print(f"Error durante la generación de texto con Gemini: {e}")
        return f"Error de Gemini: {str(e)}"


def generate_analysis_summary_prompt(analysis_results):
    """
    Crea un prompt para Gemini para resumir los resultados del análisis.
    """
    if not analysis_results or analysis_results.get("status") != "success":
        return None

    length = analysis_results.get('beam_length_mm', 'N/A')
    profile = analysis_results.get('profile_id', 'N/A')
    material = analysis_results.get('material_id', 'N/A')
    load = analysis_results.get('applied_load_N', 'N/A')
    deflection = analysis_results.get('mid_span_deflection_mm', 'N/A')
    reac1 = analysis_results.get('reaction_node1_y_N', 'N/A')
    reac2 = analysis_results.get('reaction_node3_y_N', 'N/A')

    # Asegurarse de que los valores numéricos tengan el formato correcto si son N/A
    length_str = f"{length:.2f}" if isinstance(length, (int, float)) else str(length)
    load_str = f"{load:.2f}" if isinstance(load, (int, float)) else str(load)
    deflection_str = f"{deflection:.4f}" if isinstance(deflection, (int, float)) else str(deflection)
    reac1_str = f"{reac1:.2f}" if isinstance(reac1, (int, float)) else str(reac1)
    reac2_str = f"{reac2:.2f}" if isinstance(reac2, (int, float)) else str(reac2)


    prompt = f"""
    Eres un asistente de ingeniería estructural. Por favor, genera un breve resumen descriptivo
    (aproximadamente 2-3 frases concisas y técnicas) del siguiente análisis de una viga
    simplemente apoyada con una carga puntual central.

    Datos del Análisis:
    - Longitud de la viga: {length_str} mm
    - Perfil estructural: {profile}
    - Material: {material}
    - Carga puntual aplicada en el centro (hacia abajo si es negativa): {load_str} N
    Resultados Principales:
    - Deflexión máxima en el centro: {deflection_str} mm
    - Reacción en apoyo izquierdo (Nodo 1): {reac1_str} N
    - Reacción en apoyo derecho (Nodo 3): {reac2_str} N

    Ejemplo de resumen deseado: "Se realizó el análisis de una viga {profile} de {material} con una longitud de {length_str} mm,
    sometida a una carga central de {load_str} N. La deflexión máxima resultante fue de {deflection_str} mm,
    con reacciones simétricas en los apoyos de {reac1_str} N cada uno."

    Genera un resumen similar para los datos proporcionados, manteniendo un tono profesional e informativo.
    Evita frases como "Aquí tienes un resumen:" o similares. Ve directo al resumen.
    """
    return prompt.strip()


if __name__ == '__main__':
    # Configurar Gemini una vez al inicio del script de prueba
    if not configure_gemini_once():
        print("Terminando prueba debido a error de configuración de Gemini.")
    else:
        print(f"Clave API de Gemini detectada: ...{API_KEY[-4:] if API_KEY else 'NINGUNA'}")

        sample_results = {
            "beam_length_mm": 6000.0, "profile_id": "IR305x41.0", "material_id": "ACERO_A572_GR50",
            "applied_load_N": -15000.0, "mid_span_deflection_mm": -3.521,
            "reaction_node1_y_N": 7500.0, "reaction_node3_y_N": 7500.0,
            "status": "success"
        }

        test_prompt = generate_analysis_summary_prompt(sample_results)
        if test_prompt:
            print("\n--- Prompt Generado ---")
            print(test_prompt)

            print("\n--- Solicitando resumen a Gemini (modelo gemini-pro) ---")
            # Usar el modelo gemini-1.0-pro-latest o gemini-pro para texto
            summary = generate_text_with_gemini(test_prompt, model_name="gemini-1.0-pro")

            print("\n--- Resumen de Gemini ---")
            if summary:
                print(summary)
            else:
                print("No se pudo generar el resumen o la respuesta fue vacía.")
        else:
            print("No se pudo generar el prompt (datos de análisis inválidos).")

        # Prueba de generación directa
        # print("\n--- Prueba de generación directa ---")
        # direct_prompt = "Explica brevemente qué es el análisis de elementos finitos en ingeniería estructural."
        # direct_summary = generate_text_with_gemini(direct_prompt, model_name="gemini-1.0-pro")
        # print("\n--- Respuesta de Gemini (directa) ---")
        # if direct_summary:
        #     print(direct_summary)
        # else:
        #     print("No se pudo generar el resumen directo o la respuesta fue vacía.")
