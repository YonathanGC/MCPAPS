# ai_controller.py
# This module interfaces with an AI model (like Gemini/Jules)
# to interpret natural language prompts and generate code or commands.

import os
import json
from dotenv import load_dotenv

# Attempt to import the Gemini library, but don't fail if it's not installed yet,
# as this module should still be usable with placeholders.
try:
    import google.generativeai as genai
except ImportError:
    genai = None # Allows the rest of the file to be parsed

# Load environment variables
load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# OAuth2 related environment variables (if used)
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL") # e.g., 'https://oauth2.googleapis.com/token'
OAUTH_SCOPES = os.getenv("OAUTH_SCOPES") # e.g., 'https://www.googleapis.com/auth/generative-language.tuning'

# --- Module State ---
_ai_model_client = None # Holds the initialized generative model client (e.g., Gemini)
_is_authenticated = False

# --- System Prompts (Templates) ---
# These are crucial for guiding the AI's behavior.
# They should be refined based on testing and the specific capabilities of the chosen AI model.

DEFAULT_INTERPRET_SYSTEM_PROMPT = """
You are an expert assistant for AEC (Architecture, Engineering, Construction) and GIS workflows.
Your task is to interpret user requests and translate them into a structured JSON format.
The JSON output MUST be a single, valid JSON object. Do NOT use markdown like ```json ... ```.
The JSON output should include:
- 'target_app': The primary application to interact with (e.g., 'revit', 'autocad', 'civil3d', 'robot', 'dynamo', 'arcgis', 'qgis'). Determine this from the prompt.
- 'action': A concise keyword or short phrase for the main action (e.g., 'open_project', 'filter_elements', 'export_data', 'run_script', 'generate_report', 'create_surface', 'draw_line').
- 'parameters': A dictionary of parameters specific to the action and target_app. Extract all relevant details from the prompt.
  - Example for Revit: "project_path", "element_filters" (as a dict), "export_settings" (as a dict).
  - Example for AutoCAD: "drawing_path", "command_sequence" (as a list of strings), "layer_operations" (as a dict).
  - Example for ArcGIS: "item_id", "layer_url", "query_where_clause", "buffer_distance".

If the prompt is ambiguous or lacks critical information for a specific action, try to make reasonable assumptions
or include a field like 'clarification_needed' with a question for the user.

User prompt: "{user_prompt}"

Your JSON output:
"""

DEFAULT_GENERATE_CODE_SYSTEM_PROMPT_TEMPLATE = """
You are an expert AEC/GIS software automation assistant.
Based on the following structured task (JSON), generate the corresponding {language_or_sdk_name} code snippet.
The code should be a functional snippet that can be executed within the target application's environment or by its Python client.

Task Details (JSON):
{task_json}

Constraints for {target_app}:
- {app_specific_constraints}
- Assume necessary imports are handled by the execution environment or provide them if they are standard and essential.
- Focus on the core logic to accomplish the task described in the JSON.
- The output should be ONLY the code snippet, without any surrounding text, explanations, or markdown.

Generated {language_or_sdk_name} Code:
"""

# --- Authentication ---
def authenticate(api_key: str = None, use_oauth: bool = False, oauth_credentials_path: str = None) -> bool:
    """
    Authenticates with the AI service (Google Gemini in this implementation).
    Supports API Key (default) or OAuth2.

    Args:
        api_key (str, optional): The API key. Defaults to GEMINI_API_KEY from .env.
        use_oauth (bool, optional): If True, attempts OAuth2 authentication. Defaults to False.
        oauth_credentials_path (str, optional): Path to OAuth2 client secrets JSON file or service account JSON.
                                                (This part is conceptual for Gemini's typical client library usage;
                                                 direct credential object passing might be more common for some OAuth libs).

    Returns:
        bool: True if authentication was successful or already authenticated, False otherwise.
    """
    global _ai_model_client, _is_authenticated, GEMINI_API_KEY

    if _is_authenticated and _ai_model_client:
        print("AI Service already authenticated.")
        return True

    if not genai:
        print("Error: Google Generative AI library (google-generativeai) is not installed. Cannot authenticate.")
        return False

    current_api_key = api_key if api_key is not None else GEMINI_API_KEY

    if use_oauth:
        print("Attempting OAuth2 authentication with AI Service...")
        # OAuth2 for Gemini typically involves user credentials flow or service accounts.
        # The `genai.configure()` might not directly take client_id/secret for user flows.
        # This section is a placeholder and needs to be adapted based on the specific OAuth library
        # and flow you intend to use (e.g., `google-auth` library for user or service account credentials).
        #
        # Example using google-auth (conceptual, needs `google-auth` library):
        # from google.oauth2 import service_account
        # from google.auth.transport.requests import Request
        #
        # if oauth_credentials_path:
        #     try:
        #         # For service account:
        #         # credentials = service_account.Credentials.from_service_account_file(
        #         #     oauth_credentials_path, scopes=[OAUTH_SCOPES] if OAUTH_SCOPES else None)
        #         # For user credentials (after consent flow, not shown here):
        #         # credentials = Credentials.from_authorized_user_file(oauth_credentials_path, scopes)
        #
        #         # if not credentials.valid:
        #         #     if credentials.expired and credentials.refresh_token:
        #         #         credentials.refresh(Request())
        #         #     else: # Needs user interaction for consent
        #         #        raise Exception("OAuth credentials need authorization/refresh.")
        #
        #         # genai.configure(credentials=credentials) # This is hypothetical for genai
        #         # _ai_model_client = genai.GenerativeModel('gemini-pro') # Or preferred model
        #         # _is_authenticated = True
        #         # print("AI Service configured successfully with OAuth2 credentials.")
        #         # return True
        #         print("Placeholder: OAuth2 authentication logic needs to be implemented using a suitable library like 'google-auth'.")
        #         return False # Placeholder failure for OAuth
        #     except Exception as e:
        #         print(f"Error during OAuth2 configuration: {e}")
        #         _ai_model_client = None
        #         _is_authenticated = False
        #         return False
        # else:
        #     print("OAuth2 requested but no credentials path provided.")
        #     return False
        print("Placeholder: OAuth2 authentication not fully implemented in this version.")
        return False # Placeholder until OAuth is fully fleshed out

    elif current_api_key:
        print("Authenticating with AI Service using API Key...")
        try:
            genai.configure(api_key=current_api_key)
            # Initialize the model client (e.g., Gemini Pro)
            _ai_model_client = genai.GenerativeModel('gemini-pro') # Adjust model as needed
            _is_authenticated = True
            print("AI Service (Gemini) configured successfully with API Key.")
            return True
        except Exception as e:
            print(f"Error configuring Gemini API with API Key: {e}")
            _ai_model_client = None
            _is_authenticated = False
            return False
    else:
        print("AI Service authentication failed: No API Key provided or found in .env, and OAuth not selected/configured.")
        return False

# --- Core Functions ---
def interpret(prompt: str, system_prompt_template: str = DEFAULT_INTERPRET_SYSTEM_PROMPT) -> dict:
    """
    Translates a natural language prompt into a structured instruction dictionary using the AI model.

    Args:
        prompt (str): The natural language prompt from the user or FastMCP.
        system_prompt_template (str, optional): A template for the system prompt.
                                                Must include "{user_prompt}" placeholder.

    Returns:
        dict: A structured dictionary (JSON) representing the AI's interpretation.
              Returns a dict with an "error" key if interpretation fails or AI is not available.
    """
    global _ai_model_client
    if not _is_authenticated or not _ai_model_client:
        if not authenticate(): # Try to auto-authenticate if not done
            return {"error": "AI model not authenticated or available."}

    print(f"Interpreting prompt: '{prompt}'")

    full_prompt_for_ai = system_prompt_template.format(user_prompt=prompt)

    try:
        # For Gemini, ensure the response is configured for JSON output if possible,
        # or parse the text response carefully. Some models have specific JSON modes.
        # generation_config = genai.types.GenerationConfig(
        #     response_mime_type="application/json" # If supported
        # )
        # response = _ai_model_client.generate_content(full_prompt_for_ai, generation_config=generation_config)

        response = _ai_model_client.generate_content(full_prompt_for_ai) # Standard text generation

        if response.candidates and response.candidates[0].content.parts:
            # Assuming the AI returns a JSON string as requested by the prompt
            json_output_string = response.candidates[0].content.parts[0].text
            # Clean the output if it includes markdown like ```json ... ```
            if json_output_string.strip().startswith("```json"):
                json_output_string = json_output_string.strip()[7:-3].strip()
            elif json_output_string.strip().startswith("```"): # More generic markdown removal
                 json_output_string = json_output_string.strip()[3:-3].strip()


            interpreted_instruction = json.loads(json_output_string)
            return interpreted_instruction
        else:
            error_detail = f"AI did not return a valid response structure. Response: {response}"
            print(error_detail)
            return {"error": "AI response format error.", "details": str(response.prompt_feedback or "No feedback")}

    except json.JSONDecodeError as e:
        error_detail = f"Failed to decode AI response as JSON: {e}. Response text: '{json_output_string if 'json_output_string' in locals() else 'N/A'}'"
        print(error_detail)
        return {"error": "AI response JSON parsing error.", "details": error_detail}
    except Exception as e:
        # Catch more general API errors (e.g., quota, inappropriate content)
        error_detail = f"Error during AI interpretation: {e}"
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
             error_detail += f" Prompt Feedback: {response.prompt_feedback}"
        print(error_detail)
        return {"error": "AI interpretation failed.", "details": error_detail}


def generate_code(task: dict, system_prompt_template: str = DEFAULT_GENERATE_CODE_SYSTEM_PROMPT_TEMPLATE) -> str:
    """
    Generates a code snippet or a sequence of commands based on a structured task.

    Args:
        task (dict): A structured dictionary, typically the output of `interpret()`.
                     Expected to have 'target_app' and 'parameters'.
        system_prompt_template (str, optional): Template for the system prompt for code generation.
                                                Must include "{language_or_sdk_name}", "{task_json}",
                                                "{target_app}", and "{app_specific_constraints}".

    Returns:
        str: A string containing the generated code or commands.
             Returns an error message string if generation fails or AI is not available.
    """
    global _ai_model_client
    if not _is_authenticated or not _ai_model_client:
        if not authenticate(): # Try to auto-authenticate
            return "Error: AI model not authenticated or available for code generation."

    if not isinstance(task, dict) or "target_app" not in task:
        return "Error: Invalid task dictionary provided for code generation (missing 'target_app')."

    print(f"Generating code for task related to '{task.get('target_app', 'unknown app')}'...")
    if task.get("error"): # If interpret() returned an error dict
        return f"Error: Cannot generate code from an erroneous task interpretation: {task.get('error')}"

    target_app = task.get("target_app")

    # --- Language/SDK and Constraints Mapping ---
    # This mapping is crucial for guiding the AI correctly.
    app_details_map = {
        "revit": {
            "lang_sdk": "Python with Revit API (pyRevit/IronPython context)",
            "constraints": "Use `doc` for `__revit__.ActiveUIDocument.Document` and `uidoc` for `__revit__.ActiveUIDocument`. Wrap modifications in a `Transaction`. Import from `Autodesk.Revit.DB` and `Autodesk.Revit.UI` as needed."
        },
        "autocad": {
            "lang_sdk": "Python with pyautocad library or AutoLISP",
            "constraints": "For pyautocad, assume `acad = Autocad()` is available. For AutoLISP, provide complete, runnable expressions. Prefer pyautocad if Python is viable for the task."
        },
        "civil3d": {
            "lang_sdk": "Python with Civil 3D API (via pyautocad for COM or pythonnet for .NET)",
            "constraints": "Access Civil 3D objects via the COM interface (e.g., `acad.doc.AeccApplication.ActiveDocument...`) or assume .NET context if generating C#-like Python for pythonnet. Be specific about Civil 3D object types."
        },
        "robot": {
            "lang_sdk": "Python with Robot Structural Analysis API (COM)",
            "constraints": "Assume `robot_app = comtypes.client.CreateObject(\"Robot.Application\")` is available. Use Robot API object model, e.g., `robot_app.Project.Structure.Nodes`."
        },
        "dynamo": {
            "lang_sdk": "Python script for a Dynamo node (IronPython)",
            "constraints": "Provide Python code suitable for a script node in Dynamo. Use `IN` for inputs and assign outputs to `OUT`. Import common libraries like `math`, `sys`, `clr` if needed. For Revit-hosted Dynamo, Revit API access is possible."
        },
        "arcgis": {
            "lang_sdk": "Python with arcgis-python-api",
            "constraints": "Assume `gis = GIS(...)` connection object is available. Use `gis.content`, `gis.features`, `gis.geoprocessing` modules. Specify item IDs or service URLs clearly in parameters."
        },
        "qgis": {
            "lang_sdk": "Python with PyQGIS (qgis.core, qgis.gui, qgis.analysis, processing)",
            "constraints": "Assume QGIS environment is active (e.g., `qgis.utils.iface` available if GUI context, or `QgsApplication` initialized for standalone). Use `processing.run()` for algorithms. Specify layer names or IDs."
        },
        "unknown": { # Fallback for unmapped apps
            "lang_sdk": "a generic script or command sequence",
            "constraints": "Provide commands or a script in a common language like Python or shell script if appropriate. Be very explicit about the expected execution environment."
        }
    }

    app_info = app_details_map.get(target_app, app_details_map["unknown"])
    language_or_sdk_name = app_info["lang_sdk"]
    app_specific_constraints = app_info["constraints"]

    try:
        task_json_string = json.dumps(task, indent=2)
        full_prompt_for_ai = system_prompt_template.format(
            language_or_sdk_name=language_or_sdk_name,
            task_json=task_json_string,
            target_app=target_app,
            app_specific_constraints=app_specific_constraints
        )

        response = _ai_model_client.generate_content(full_prompt_for_ai)

        if response.candidates and response.candidates[0].content.parts:
            generated_code_snippet = response.candidates[0].content.parts[0].text
            # Clean markdown if present (common for code blocks)
            if generated_code_snippet.strip().startswith("```"):
                # Remove the first line (e.g., ```python) and last line (```)
                lines = generated_code_snippet.strip().splitlines()
                if len(lines) > 1:
                    generated_code_snippet = "\n".join(lines[1:-1]) if len(lines) > 2 else lines[0] # Handle single line in backticks too
                else: # Only ``` was returned, or empty ``` ```
                    generated_code_snippet = ""

            return generated_code_snippet.strip() # Remove leading/trailing whitespace
        else:
            error_detail = f"AI did not return valid code. Response: {response}"
            print(error_detail)
            return f"Error: AI code generation response format error. Details: {str(response.prompt_feedback or 'No feedback')}"

    except Exception as e:
        error_detail = f"Error during AI code generation: {e}"
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
             error_detail += f" Prompt Feedback: {response.prompt_feedback}"
        print(error_detail)
        return f"Error: AI code generation failed. Details: {error_detail}"


# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    print("AI Controller Module - Direct Test Mode")

    # Ensure API key is available in .env or pass it directly
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found in environment. Please set it for testing.")

    # --- Test Authentication ---
    print("\n--- Testing Authentication ---")
    auth_success = authenticate() # Uses API Key from .env by default
    if not auth_success:
        print("Authentication failed. Cannot proceed with further tests.")
        exit()

    # --- Test Interpretation ---
    print("\n--- Testing Interpretation ---")
    # sample_prompt_revit = "In Revit, please open the project 'Building_Model_Central.rvt'. After that, find all concrete walls on Level 1 and export their total volume to a text file at 'C:/Exports/concrete_volumes.txt'."
    sample_prompt_revit = "Abre el proyecto de Revit 'ProjectX.rvt', filtra muros de concreto y exporta cubos de carga a CSV en 'C:/Exports/'."

    interpreted_task_revit = interpret(sample_prompt_revit)
    print(f"\nInterpreted Task (Revit) from '{sample_prompt_revit}':")
    print(json.dumps(interpreted_task_revit, indent=2))

    sample_prompt_autocad = "For AutoCAD, draw a red circle with center 50,50 and radius 20. Then, add a text label 'Center Point' at 50,45."
    interpreted_task_autocad = interpret(sample_prompt_autocad)
    print(f"\nInterpreted Task (AutoCAD) from '{sample_prompt_autocad}':")
    print(json.dumps(interpreted_task_autocad, indent=2))

    # --- Test Code Generation ---
    print("\n--- Testing Code Generation (Revit) ---")
    if interpreted_task_revit and not interpreted_task_revit.get("error"):
        generated_revit_code = generate_code(interpreted_task_revit)
        print(f"Generated Revit Code/Instructions:\n```python\n{generated_revit_code}\n```")
    else:
        print("Skipping Revit code generation due to interpretation error or no task.")

    print("\n--- Testing Code Generation (AutoCAD) ---")
    if interpreted_task_autocad and not interpreted_task_autocad.get("error"):
        generated_autocad_code = generate_code(interpreted_task_autocad)
        # Assuming pyautocad or LISP
        print(f"Generated AutoCAD Code/Instructions:\n```python\n{generated_autocad_code}\n```")
    else:
        print("Skipping AutoCAD code generation due to interpretation error or no task.")

    print("\n--- Ambiguous Prompt Test ---")
    ambiguous_prompt = "Process the data."
    interpreted_ambiguous = interpret(ambiguous_prompt)
    print(f"\nInterpreted Task (Ambiguous) from '{ambiguous_prompt}':")
    print(json.dumps(interpreted_ambiguous, indent=2))
    if interpreted_ambiguous and not interpreted_ambiguous.get("error"):
        generated_ambiguous_code = generate_code(interpreted_ambiguous)
        print(f"Generated Code (Ambiguous):\n{generated_ambiguous_code}")

    print("\nAI Controller direct test finished.")
