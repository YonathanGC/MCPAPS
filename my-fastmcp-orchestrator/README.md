# My FastMCP Orchestrator

My FastMCP Orchestrator is a Python-based project designed to bridge the gap between natural language commands and actions within various AEC (Architecture, Engineering, Construction) and GIS software applications. It leverages a FastMCP-compatible server for real-time communication and an AI model (Google's Gemini via its API) to interpret prompts and generate executable instructions or code snippets.

The primary goal is to enable users to issue high-level commands in natural language (e.g., through a FastMCP client interface) which are then translated by this orchestrator into specific actions performed by the target desktop software.

## Project Structure

```
/my-fastmcp-orchestrator
├─ .env.example     # Example environment configuration (copy to .env)
├─ .env             # Local environment variables (API keys, URLs - GIT IGNORED)
├─ main.py          # Main application entry point and orchestration logic
├─ fastmcp_client.py # Client for FastMCP WebSocket communication
├─ ai_controller.py   # Interface for AI model (Gemini API)
├─ /apps/           # Application-specific client modules
│  ├─ __init__.py
│  ├─ revit_client.py
│  ├─ autocad_client.py
│  ├─ civil3d_client.py
│  ├─ robot_client.py
│  ├─ dynamo_client.py
│  ├─ arcgis_client.py
│  └─ qgis_client.py
├─ requirements.txt # Python dependencies
└─ README.md        # This file
```

## Installation

1.  **Clone the repository (if you have one):**
    ```bash
    # git clone <your-repository-url>
    # cd my-fastmcp-orchestrator
    ```
    If you don't have a repository, simply create the project directory.

2.  **Create and activate a Python virtual environment:**
    It's highly recommended to use a virtual environment to manage dependencies and avoid conflicts with other Python projects.
    ```bash
    python -m venv venv
    ```
    Activate the environment:
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    The `requirements.txt` file lists the core dependencies needed to run the orchestrator.
    ```bash
    pip install -r requirements.txt
    ```
    This will install `python-dotenv`, `websockets` (for FastMCP), and `google-generativeai` (for Gemini).

4.  **Install Application-Specific SDKs/APIs (As Needed):**
    The `requirements.txt` file also contains commented-out examples of libraries that might be needed for specific application clients (e.g., `pyautocad`, `arcgis`). You only need to install these if you plan to implement and use those specific clients.
    *   **Consult `requirements.txt`** for more details and examples.
    *   **Important:** Many desktop applications (Revit, AutoCAD, Civil 3D, Robot, QGIS, Dynamo) have APIs that are not simply "pip installable" for external control from a standard CPython environment. They often require:
        *   The host application to be installed on the same machine.
        *   Interaction via COM objects (Windows-specific, e.g., using `pyautocad` or `comtypes`).
        *   Running scripts within the application's own Python environment (often IronPython for Autodesk products).
        *   Custom-built plugins or add-ins within the host application to expose an interface (e.g., an HTTP server) that this orchestrator can talk to.
    *   **Always refer to the official API documentation for each target application.**

## Configuration

1.  **Create `.env` file:**
    Copy the example environment file `.env.example` to a new file named `.env` in the project root:
    ```bash
    cp .env.example .env
    ```
    **Important:** The `.env` file should be added to your `.gitignore` file to prevent committing sensitive credentials to version control.

2.  **Edit `.env` file:**
    Open the `.env` file and fill in the required values:

    *   **`FASTMCP_URL`**: The WebSocket URL of your FastMCP server.
        *   Example: `FASTMCP_URL=ws://localhost:8765`
    *   **`FASTMCP_TOKEN`**: (Optional) An authentication token if your FastMCP server requires it.
        *   Example: `FASTMCP_TOKEN=your_secret_fastmcp_token`
    *   **`GEMINI_API_KEY`**: Your API Key for the Google Gemini service.
        *   **How to get a Gemini API Key:**
            1.  Go to [Google AI Studio](https://aistudio.google.com/).
            2.  Sign in with your Google account.
            3.  If you don't have a project, you might be prompted to create one or agree to terms.
            4.  Navigate to the "API keys" section (often found by clicking "Get API key" or through your project settings).
            5.  Create a new API key.
            6.  Copy the generated API key and paste it as the value for `GEMINI_API_KEY` in your `.env` file.
            7.  **Security Note:** Treat your API key like a password. Do not share it publicly.
        *   Example: `GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXX`
    *   **(Optional) Application-Specific Variables:** The `.env.example` file shows examples of other variables you might want to add for specific application clients (e.g., default project paths, ArcGIS portal URLs).

## Usage

1.  **Ensure all necessary configurations are set** in your `.env` file (especially `GEMINI_API_KEY` and `FASTMCP_URL`).
2.  **Activate your Python virtual environment** (if you created one):
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`
3.  **Run the main application:**
    ```bash
    python main.py
    ```
4.  **Orchestrator Operation:**
    *   The application will start by authenticating the AI Controller (Gemini) and connecting to the FastMCP server.
    *   It will then listen for messages on the FastMCP WebSocket connection.
    *   When a message containing a "prompt" is received (e.g., from a FastMCP client GUI or another service), the orchestrator will:
        1.  Use `ai_controller.interpret()` to send the prompt to Gemini and get a structured JSON interpretation of the task.
        2.  If interpretation is successful, it uses `ai_controller.generate_code()` to ask Gemini to generate a code snippet or command sequence based on the interpreted task and the target application.
        3.  It then calls the appropriate application client from the `/apps/` directory.
        4.  The application client (e.g., `revit_client.py`) executes the generated code or performs actions based on the interpreted task.
        5.  Status updates and results are sent back via FastMCP.
    *   You can stop the orchestrator by pressing `Ctrl+C` in the terminal where it's running. This will trigger a graceful shutdown.

### Example "Indicators" (Prompts) and AI Interaction Flow

The effectiveness of the orchestrator heavily relies on how well the AI can interpret prompts and generate useful code/commands. The system prompts in `ai_controller.py` are designed to guide this.

**Scenario:** User sends a prompt via a FastMCP client:
`"In Revit, open 'ProjectABC.rvt', find all doors on Level 1, and list their Mark and Family type."`

1.  **FastMCP Client (`fastmcp_client.py`)**: Receives this prompt.
2.  **Main Orchestrator (`main.py`)**:
    *   Passes the prompt to `ai_controller.interpret(prompt)`.
3.  **AI Controller (`ai_controller.py`)**:
    *   Sends the prompt to Gemini with a system message asking for JSON output like:
        ```json
        {
          "target_app": "revit",
          "action": "query_and_list_elements",
          "parameters": {
            "project_path": "ProjectABC.rvt",
            "element_type": "doors",
            "filters": {
              "level": "Level 1"
            },
            "properties_to_list": ["Mark", "Family"]
            // AI might name 'Family' differently, e.g. 'Type Name' or 'Family Name'
            // The client code or further AI prompting might be needed to map this correctly.
          }
        }
        ```
    *   Receives this JSON back from Gemini.
4.  **Main Orchestrator (`main.py`)**:
    *   Receives the structured JSON task.
    *   Calls `ai_controller.generate_code(interpreted_task)`.
5.  **AI Controller (`ai_controller.py`)**:
    *   Sends the JSON task to Gemini with a system message asking for Python code for Revit API, like:
        ```python
        # Conceptual Python for Revit API (IronPython context)
        # from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementId, Level
        # from Autodesk.Revit.UI import TaskDialog

        # project_path = "ProjectABC.rvt" # Handled by app_client.load_project()
        # target_level_name = "Level 1"
        # properties_to_list = ["Mark", "Family"] # Client needs to map "Family" to actual API property

        # results = []
        # # Assuming 'doc' is available (current document)
        # level_filter = None
        # levels = FilteredElementCollector(doc).OfClass(Level).ToElements()
        # for lvl in levels:
        #     if lvl.Name == target_level_name:
        #         level_filter = ElementId(lvl.Id)
        #         break

        # if level_filter:
        #     door_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
        #     door_collector.WherePasses(LevelFilter(level_filter)) # This is not a direct API, needs correct filter

        #     for door in door_collector:
        #         door_info = {}
        #         try:
        #             mark_param = door.LookupParameter("Mark")
        #             if mark_param:
        #                 door_info["Mark"] = mark_param.AsString() if mark_param.HasValue else mark_param.AsValueString()

        #             # Getting "Family" usually means getting the FamilyName of the ElementType (FamilySymbol)
        #             door_type = doc.GetElement(door.GetTypeId())
        #             if door_type and hasattr(door_type, "FamilyName"):
        #                  door_info["Family"] = door_type.FamilyName
        #             elif door_type: # Fallback to type name if FamilyName not directly on type
        #                  type_name_param = door_type.LookupParameter("Type Name")
        #                  if type_name_param:
        #                      door_info["Family"] = type_name_param.AsString()
        #             results.append(door_info)
        #         except Exception as e:
        #             results.append({"error_processing_door": str(e)})
        # else:
        #     results.append({"error": f"Level '{target_level_name}' not found."})

        # # The client will decide how to return/display 'results'
        # # For example, converting to a string or structured log
        # output_str = "Doors on Level 1:\n"
        # for r in results:
        #    output_str += f" - Mark: {r.get('Mark', 'N/A')}, Family: {r.get('Family', 'N/A')}\n"
        # print(output_str) # Or send back to orchestrator
        ```
    *   Receives this Python script string back from Gemini.
6.  **Main Orchestrator (`main.py`)**:
    *   Selects `revit_client.py`.
    *   Calls `revit_client.connect()`, then `revit_client.load_project("ProjectABC.rvt")`.
    *   Calls `revit_client.apply_changes({"generated_code": generated_revit_script, "original_instruction": ...})`.
7.  **Revit Client (`revit_client.py`)**:
    *   (Placeholder logic) Executes the `generated_revit_script`. In a real scenario, this would involve complex interaction with Revit, possibly running the script via pyRevit, a Revit add-in, or another RPC mechanism.
    *   Collects results/status.
8.  **Main Orchestrator (`main.py`)**:
    *   Sends results/status back through `fastmcp_client.send()`.

**Note:** The quality and executability of the AI-generated code will vary. The application clients might need to perform pre-processing, error handling, or even further refinement of the code before execution. The system prompts in `ai_controller.py` are critical for guiding the AI.

## Extending the Orchestrator

### Adding New Application Clients

1.  **Create Client File**:
    *   In the `/apps/` directory, create a new Python file (e.g., `newapp_client.py`).
2.  **Implement Client Functions**:
    *   Each client module must implement the following functions (even if some are just placeholders initially):
        ```python
        def connect(**kwargs) -> bool:
            """Connects to NewApp or initializes its API. Returns True on success."""
            print(f"Placeholder: Connecting to NewApp with {kwargs}")
            return True

        def load_project(path: str) -> bool:
            """Loads a project/file into NewApp. Returns True on success."""
            print(f"Placeholder: NewApp loading project '{path}'")
            return True

        def apply_changes(changes: dict) -> dict:
            """
            Applies changes, executes commands/scripts in NewApp.
            'changes' dict will contain 'generated_code' and 'original_instruction'.
            Returns a dict with 'status': 'success'/'failed' and 'details' or 'error'.
            """
            generated_code = changes.get("generated_code")
            original_instruction = changes.get("original_instruction")
            print(f"Placeholder: NewApp applying changes. Code:\n{generated_code}\nOriginal instruction: {original_instruction}")
            # Actual execution logic here
            return {"status": "success", "details": "Changes applied in NewApp (simulated)."}

        def export(output_dir: str, **kwargs) -> dict:
            """
            Exports data from NewApp. kwargs can include format, specific items to export, etc.
            Returns a dict with 'status', and 'exported_files' (list) or 'error'.
            """
            print(f"Placeholder: NewApp exporting to '{output_dir}' with options {kwargs}")
            # Actual export logic here
            return {"status": "success", "exported_files": [f"{output_dir}/newapp_export.dat"]}

        def get_status() -> dict:
            """Gets current status of NewApp. Returns a dict with relevant status info."""
            print("Placeholder: Getting NewApp status")
            return {"app_name": "NewApp", "is_connected": True, "current_project": "None", "version": "1.0"}
        ```
3.  **Register in `main.py`**:
    *   Import your new client at the top of `main.py`:
        ```python
        from apps import newapp_client # Add your new client
        ```
    *   Add it to the `APP_CLIENTS` dictionary in `main.py`:
        ```python
        APP_CLIENTS = {
            # ... existing clients
            "newapp": newapp_client, # Add your new client's name (lowercase)
        }
        ```
4.  **Update AI Controller (`ai_controller.py`)**:
    *   **Interpretation**: Ensure the `DEFAULT_INTERPRET_SYSTEM_PROMPT` (or a custom one you pass to `interpret`) can guide the AI to correctly identify `"target_app": "newapp"` from user prompts. You might need to add "newapp" to the list of example target apps in the prompt.
    *   **Code Generation**: Add an entry for `"newapp"` to the `app_details_map` in `ai_controller.generate_code()`. This entry should specify:
        *   `"lang_sdk"`: The language or SDK name the AI should target (e.g., "NewApp Python SDK", "NewApp CLI Commands").
        *   `"constraints"`: Specific instructions or constraints for the AI when generating code for NewApp (e.g., "All commands must start with `newapp-cli`.", "Use the `newapp_api.v1` module.").
5.  **Dependencies**:
    *   If your `newapp_client.py` requires any new Python libraries, add them to `requirements.txt` and provide installation notes if necessary.
6.  **Testing**:
    *   Thoroughly test the new client with various prompts to ensure the AI interprets them correctly and generates usable code/commands for your new application.

### Defining New AI "Instructions" or Capabilities (Advanced)

This involves refining how the AI interprets prompts and what kind of structured JSON or code it generates.

1.  **Identify the New Capability**: What new type of high-level action or query do you want the AI to understand for an existing or new application?
    *   Example: For Revit, "Perform a clash detection between structural and MEP models, and report clashes above 1 inch."
2.  **Design the Structured JSON Output (`interpret` phase)**:
    *   How should the AI represent this new instruction as a structured dictionary?
    *   Example for clash detection:
        ```json
        {
          "target_app": "revit",
          "action": "perform_clash_detection",
          "parameters": {
            "model_A_path_or_link": "StructuralModel.rvt", // Or how it's identified
            "model_B_path_or_link": "MEPModel.rvt",
            "clash_sets": [
              {"category_A": "Structural Framing", "category_B": "Ducts"},
              {"category_A": "Structural Columns", "category_B": "Pipes"}
            ],
            "tolerance_inches": 1.0,
            "report_output_path": "ClashReport.html"
          }
        }
        ```
3.  **Refine `interpret()` System Prompt**:
    *   In `ai_controller.py`, modify `DEFAULT_INTERPRET_SYSTEM_PROMPT` (or create a custom one).
    *   Add examples of user prompts for this new capability and the corresponding structured JSON you expect the AI to output. This "few-shot" prompting helps the AI learn the desired format.
4.  **Refine `generate_code()` System Prompt and Constraints**:
    *   If the new capability requires specific code generation patterns:
        *   Update the `app_specific_constraints` for the target application in the `app_details_map` within `ai_controller.generate_code()`.
        *   You might need to be very explicit about API calls or script structures.
5.  **Update Application Client (`apps/<client>.py`)**:
    *   The `apply_changes()` function in the relevant application client must be updated to:
        *   Recognize the new `action` (e.g., `"perform_clash_detection"`).
        *   Understand the `parameters` from the interpreted JSON.
        *   Correctly use the `generated_code` (if any) or directly implement the logic for this new action using the application's API.
6.  **Test Thoroughly**: This is an iterative process. Test with various phrasings of the user prompt to see how the AI responds and adjust system prompts and client logic accordingly.

## Module Explanations

*   **`main.py`**: The central nervous system of the orchestrator.
    *   Initializes all other modules.
    *   Handles the primary workflow: receive FastMCP message -> AI interpret -> AI generate code -> dispatch to App Client -> send response via FastMCP.
    *   Manages graceful shutdown.
*   **`fastmcp_client.py`**: Responsible for all WebSocket communication with the FastMCP server.
    *   Uses `asyncio` and `websockets` library, running the event loop in a separate thread to allow the main application to be synchronous.
    *   Handles connection, disconnection, sending JSON messages, and receiving messages via a callback (`handle_fastmcp_message` in `main.py`).
    *   Configurable via `.env` or direct parameters.
*   **`ai_controller.py`**: Interfaces with the Google Gemini AI model.
    *   `authenticate()`: Manages authentication using an API Key (OAuth2 is a placeholder).
    *   `interpret(prompt: str) -> dict`: Takes a natural language prompt, sends it to Gemini with a carefully crafted system prompt, and expects a structured JSON dictionary representing the task.
    *   `generate_code(task: dict) -> str`: Takes the structured JSON task, sends it to Gemini with another system prompt (specific to the target application and desired code type), and expects a code snippet or command sequence as output.
    *   Relies heavily on system prompts and the `app_details_map` to guide the AI's responses.
*   **`/apps/*.py` (Application Clients)**: Each Python file in this directory is a dedicated client for a specific software application (e.g., `revit_client.py`, `autocad_client.py`).
    *   They are expected to expose a common set of functions: `connect`, `load_project`, `apply_changes`, `export`, and `get_status`.
    *   The actual implementation within these functions will use the respective application's API, SDK, COM interface, or other control mechanisms.
    *   Currently, these are placeholders and would require significant development to interact with the actual desktop applications.
*   **`requirements.txt`**: Lists all Python package dependencies for the project.
*   **`.env.example` / `.env`**: Used for managing environment variables, including API keys and server URLs.

---

This project provides a foundational architecture. The actual implementation details, especially within the application clients (`/apps/*.py`) and the continuous refinement of AI system prompts in `ai_controller.py`, will require significant development and testing to achieve robust and reliable automation.
