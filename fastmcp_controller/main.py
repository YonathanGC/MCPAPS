import os
import sys
import asyncio
import logging
import json # For parsing Claude's potential JSON responses
from dotenv import load_dotenv

from claude_client import ClaudeClient # Updated
from dlubal_controller import DlubalController # Updated

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file at the start
load_dotenv()

# --- Globals for clients ---
claude_ai_client: ClaudeClient = None
dlubal_app_controller: DlubalController = None

async def show_menu():
    """Displays the interactive menu to the user."""
    print("\n--- Dlubal API Controller Menu ---")
    print("1. Get Active Dlubal Model Info")
    print("2. Create New Dlubal Model")
    # print("3. Open Dlubal Model (Path input needed)") # Requires careful path handling
    print("4. Send Instruction to Dlubal (via Claude)")
    print("0. Exit")
    return input("Choose an option: ")

async def handle_get_model_info(controller: DlubalController):
    """Handles getting active Dlubal model information."""
    if not controller:
        logging.warning("Dlubal controller not initialized.")
        return
    try:
        info = controller.get_active_model_info()
        logging.info("Active Model Information:")
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        else:
            print(f"  Info: {info}")
    except Exception as e:
        logging.error(f"Error getting model info: {e}", exc_info=True)

async def handle_create_new_model(controller: DlubalController):
    """Handles creating a new Dlubal model."""
    if not controller:
        logging.warning("Dlubal controller not initialized.")
        return
    try:
        model_name = input("Enter name for the new model (e.g., MyTestStructure): ")
        if not model_name:
            model_name = "Default_Claude_Model"
        app_type_choice = input(f"Enter application type ({controller.app_type} is current default, or specify RFEM/RSTAB): ").upper()
        if app_type_choice and app_type_choice in ["RFEM", "RSTAB"] and app_type_choice != controller.app_type:
            logging.info(f"Switching controller to {app_type_choice} is not directly supported post-initialization in this version. Model will be created in current app: {controller.app_type}")
            # For a real switch, controller would need to be re-initialized or support internal switching.

        status = controller.create_new_model(model_name)
        logging.info(f"Create new model status: {status}")
    except Exception as e:
        logging.error(f"Error creating new model: {e}", exc_info=True)

async def handle_send_instruction_claude(claude: ClaudeClient, dlubal: DlubalController):
    """Handles sending an instruction to Dlubal, formulated by Claude."""
    if not claude or not dlubal:
        logging.warning("Claude client or Dlubal controller not initialized.")
        return

    user_instruction = input("Describe the Dlubal action (e.g., 'create a 5m steel beam IPE300 from 0,0,0 to 5,0,0'): ")
    if not user_instruction:
        logging.warning("Instruction cannot be empty.")
        return

    # Basic prompt engineering for Claude. This needs significant refinement.
    # We should provide Claude with a schema of available dlubal_controller methods.
    # For now, a simple instruction.
    # System prompt for Claude, detailing available DlubalController actions.
    # This is crucial for Claude to generate correct JSON commands.
    # It should be updated whenever DlubalController methods change.
    system_prompt = f"""
    You are an expert Dlubal RFEM/RSTAB API assistant. Your primary function is to translate the user's natural language
    instructions into a sequence of one or more JSON objects. Each JSON object represents a specific command (an 'action')
    to be executed by a Python-based DlubalController, along with its 'params' (parameters).

    Your goal is to interpret the user's request and map it to the available actions in the DlubalController.
    If a request requires multiple operations (e.g., creating nodes before creating a member),
    you MUST return a JSON array of action objects, ordered correctly for execution.
    If a single operation suffices, return a single JSON object.

    IMPORTANT: Only generate the JSON output. Do not include any additional text, explanations, or markdown formatting outside the JSON structure.

    Available DlubalController Actions and Parameters:
    (Assume 'model_index: 0' refers to the currently active or first model if not specified by the user)

    1.  `get_active_model_info`: Get information about the currently active Dlubal model.
        - Params: {{}} (no parameters)

    2.  `create_new_model`: Creates a new model in the Dlubal application.
        - Params: {{
            "model_name": "string (e.g., 'MyTrussStructure')",
            "description": "string (optional, e.g., '2D Truss Example')"
          }}
        - Note: The Dlubal application type (RFEM/RSTAB) is set when the controller initializes.

    3.  `define_material`: Defines a material in the Dlubal model.
        - Params: {{
            "name": "string (e.g., 'S235JR', 'Concrete C25/30')",
            "properties": "object (Dlubal specific material properties, consult Dlubal API for exact structure for each material type. For S235 steel, typical properties might include: {{ 'E_module': 210e9, 'poisson_ratio': 0.3, 'yield_strength': 235e6, 'ultimate_strength': 360e6, 'density': 7850 }} )",
            "model_index": "int (optional, default: 0)"
          }}
        - Note: If user mentions a standard material like 'S235' or 'C25/30', you can use the name. The controller might have a way to look up standard materials or create them with default properties if the `dlubal.api` supports it. If detailed properties are given, include them.

    4.  `define_section`: Defines a cross-section in the Dlubal model.
        - Params: {{
            "name": "string (e.g., 'IPE300', 'Rectangle_300x500')",
            "material_name_or_id": "string_or_int (name or ID of a pre-defined material, e.g., 'S235JR' or 1)",
            "properties": "object (Dlubal specific section properties. For a parametric rectangle: {{ 'type': 'PARAMETRIC_RECT', 'depth': 0.5, 'width': 0.3 }}. For standard profiles like 'IPE300', the name might be sufficient if the Dlubal API handles library lookups, or specific library profile parameters might be needed.)",
            "model_index": "int (optional, default: 0)"
          }}
        - Note: For standard sections like 'IPE300', 'HEA200', state the name. The controller will attempt to use Dlubal's library. If parametric, provide dimensions.

    5.  `create_node`: Creates a node at specified coordinates.
        - Params: {{
            "x": "float (X-coordinate in meters)",
            "y": "float (Y-coordinate in meters)",
            "z": "float (Z-coordinate in meters)",
            "comment": "string (optional)",
            "model_index": "int (optional, default: 0)"
          }}

    6.  `create_member`: Creates a member between two existing nodes.
        - Params: {{
            "start_node_id": "int (ID of the start node)",
            "end_node_id": "int (ID of the end node)",
            "section_name_or_id": "string_or_int (name or ID of a pre-defined section, e.g., 'IPE300' or 1)",
            "material_name_or_id": "string_or_int (name or ID of a pre-defined material, e.g., 'S235' or 1 - often inferred from section, but can be specified)",
            "member_type": "string (optional, e.g., 'BEAM', 'TRUSS', 'COLUMN', default: 'BEAM')",
            "model_index": "int (optional, default: 0)"
          }}
        - Note: Ensure nodes are defined before creating a member that uses them. If a user says "create a beam from (0,0,0) to (5,0,0)", you must generate actions to create node1, then node2, then the member. Assume node IDs will be returned by `create_node` and can be referenced conceptually (e.g., if DlubalController handles ID management or if user implies sequential default IDs). For now, assume sequential node IDs starting from 1 if not specified.

    7.  `apply_nodal_load`: Applies a concentrated load to a node in a specific load case.
        - Params: {{
            "node_id": "int (ID of the node)",
            "load_case_no": "int (Load case number, e.g., 1 for LC1)",
            "Fx": "float (Force in X-direction in Newtons)",
            "Fy": "float (Force in Y-direction in Newtons)",
            "Fz": "float (Force in Z-direction in Newtons. Gravity is typically negative Z.)",
            "comment": "string (optional)",
            "model_index": "int (optional, default: 0)"
          }}
        - Note: Assume load case 1 if not specified.

    8.  `run_calculation`: Initiates a calculation for specified load cases or all.
        - Params: {{
            "load_case_numbers": "array_of_int (optional, e.g., [1, 2] or null/empty for all applicable static cases)",
            "calculation_type": "string (optional, default: 'STATIC_ANALYSIS')",
            "model_index": "int (optional, default: 0)"
          }}

    9.  `get_results`: Retrieves results of a specific type.
        - Params: {{
            "result_type": "string (e.g., 'nodal_displacements', 'member_forces', 'support_reactions')",
            "element_id": "int (optional, ID of the element if getting specific element results)",
            "load_case_no": "int (optional, load case number for which to get results)",
            "model_index": "int (optional, default: 0)"
          }}

    General Interpretation Rules:
    - Assume SI units (meters, Newtons, Pascals) if not specified by the user. The controller expects these.
    - If a user mentions a standard steel profile (e.g., IPE300, HEA240) or material (S235, S355), use the name directly. The DlubalController should handle looking these up or creating them.
    - If a multi-step process is implied (e.g., "model a simple steel frame with two columns and a beam, then apply a load"), break it down into sequential `create_node`, `define_material` (if not already defined), `define_section` (if not already defined), `create_member`, and `apply_nodal_load` actions.
    - If absolutely essential information is missing and cannot be reasonably defaulted (e.g., coordinates for a node when no context is given), return:
      `{{"error": "Instruction is unclear or lacks critical details (e.g., coordinates, dimensions, identifiers). Please be more specific."}}`
    - Be conservative: if a standard profile or material is mentioned, assume it needs to be defined first if it's the first time it's mentioned in a session, or if the user implies a new setup.

    User instruction: "{user_instruction}"

    Generate ONLY the JSON output.
    """

    logging.info("Sending instruction to Claude for Dlubal command formulation...")
    try:
        claude_response_str = claude.send_instruction(user_instruction, system_prompt=system_prompt)
        logging.info(f"Claude Raw Response: {claude_response_str}")

        # Attempt to parse Claude's response as JSON
        # Claude might sometimes add markdown backticks around JSON, try to strip them.
        if claude_response_str.startswith("```json"):
            claude_response_str = claude_response_str.replace("```json", "").replace("```", "").strip()

        actions_data = json.loads(claude_response_str)

        if isinstance(actions_data, dict) and "error" in actions_data:
            logging.error(f"Claude Error: {actions_data['error']}")
            return

        # Standardize to a list of actions
        if isinstance(actions_data, dict):
            actions_list = [actions_data]
        elif isinstance(actions_data, list):
            actions_list = actions_data
        else:
            logging.error(f"Claude response was not a valid JSON object or array of objects. Response: {claude_response_str}")
            return

        for action_data in actions_list:
            action_name = action_data.get("action")
            params = action_data.get("params", {})

            if not action_name:
                logging.error(f"Claude response item did not include 'action'. Item: {action_data}")
                continue # or return

            if hasattr(dlubal, action_name) and callable(getattr(dlubal, action_name)):
                logging.info(f"Claude formulated: Action='{action_name}', Params='{params}'")
                method_to_call = getattr(dlubal, action_name)

                confirmation = input(f"Execute Dlubal action: {action_name} with params {params}? (yes/no): ").lower()
                if confirmation == 'yes':
                    try:
                        # Here we would call the method.
                        # This might need to be async if dlubal methods are async.
                        # For now, assuming synchronous controller methods.
                        result = method_to_call(**params)
                        logging.info(f"Dlubal Action '{action_name}' executed. Result: {result}")
                    except Exception as e_dlubal:
                        logging.error(f"Error executing Dlubal action '{action_name}': {e_dlubal}", exc_info=True)
                else:
                    logging.info(f"Dlubal Action '{action_name}' cancelled by user.")
            else:
                logging.error(f"DlubalController does not have a method named '{action_name}'.")

    except json.JSONDecodeError:
        logging.error(f"Failed to parse Claude response as JSON. Response was: {claude_response_str}")
    except Exception as e:
        logging.error(f"Error processing Claude instruction for Dlubal: {e}", exc_info=True)


async def main_loop():
    """Main application loop."""
    global claude_ai_client, dlubal_app_controller

    while True:
        choice = await show_menu()
        try:
            if choice == '1':
                await handle_get_model_info(dlubal_app_controller)
            elif choice == '2':
                await handle_create_new_model(dlubal_app_controller)
            # elif choice == '3':
                # await handle_open_model(dlubal_app_controller) # Implementation needed
            elif choice == '4':
                await handle_send_instruction_claude(claude_ai_client, dlubal_app_controller)
            elif choice == '0':
                logging.info("Exiting Dlubal API Controller.")
                if dlubal_app_controller:
                    dlubal_app_controller.disconnect() # Gracefully disconnect
                break
            else:
                logging.warning("Invalid option. Please try again.")
        except ConnectionError as ce: # Specific for Dlubal connection issues
            logging.error(f"Dlubal Connection Error: {ce}. Please ensure RFEM/RSTAB is running and WebService is enabled.", exc_info=True)
            # Optionally, try to re-initialize or prompt user to restart Dlubal
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}", exc_info=True)

        if choice != '0':
             input("Press Enter to continue...")


async def initialize_clients():
    """Initializes the Claude and Dlubal clients."""
    global claude_ai_client, dlubal_app_controller
    try:
        claude_ai_client = ClaudeClient()

        # Determine Dlubal app type (e.g., from user or config)
        # For now, defaulting to RFEM, but could be made configurable
        dlubal_app_target = os.getenv("DLUBAL_APP_TYPE", "RFEM").upper()
        dlubal_address = os.getenv("DLUBAL_SERVER_ADDRESS") # Will use default in controller if None

        dlubal_app_controller = DlubalController(address=dlubal_address if dlubal_address else undefined, app_type=dlubal_app_target)

        return True
    except ValueError as e: # For API key issues or init problems
        logging.error(f"Client initialization failed: {e}")
        return False
    except ImportError as e: # For missing libraries
        logging.error(f"Client initialization failed due to missing library: {e}")
        return False
    except ConnectionError as e: # Specifically for Dlubal connection issues
        logging.error(f"Dlubal connection during initialization failed: {e}. Ensure RFEM/RSTAB is running with WebService enabled.")
        # Do not exit here, allow main loop to handle or user to retry.
        # Set dlubal_app_controller to None or handle it so app can start and show error.
        dlubal_app_controller = None # Explicitly set to None if connection fails
        return True # Allow app to start to show error message, or handle differently
    except Exception as e:
        logging.error(f"An unexpected error occurred during client initialization: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if not os.getenv("CLAUDE_API_KEY"):
        logging.error("CLAUDE_API_KEY is not set in the .env file. Please configure it.")
        sys.exit(1)
    # DLUBAL_SERVER_ADDRESS is optional, DlubalController has a default.
    # RFEM/RSTAB application itself must be running.

    # Run client initialization within the asyncio event loop
    init_success = asyncio.run(initialize_clients())

    if not init_success and not dlubal_app_controller : # If claude init failed or both failed
         logging.critical("Core client initialization failed. Exiting.")
         sys.exit(1)

    if not dlubal_app_controller:
        logging.warning("Dlubal Controller could not be initialized. Limited functionality.")
        # Allow the program to continue so user can see menu and potentially exit or get info.

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("\nApplication interrupted by user. Exiting...")
        if dlubal_app_controller:
            dlubal_app_controller.disconnect()
    except Exception as e:
        logging.critical(f"Unhandled exception in main_loop asyncio.run: {e}", exc_info=True)
    finally:
        logging.info("Application shutdown complete.")
