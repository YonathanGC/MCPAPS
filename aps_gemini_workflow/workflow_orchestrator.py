import os
import subprocess
import time
import json
import argparse
import requests # For the simple MCPClient

# Attempt to import from local packages
try:
    from .autodesk_api_client import DesignAutomationClient, WorkItem
    # If running this script directly from within aps_gemini_workflow,
    # Python might need .. to be in PYTHONPATH or use `python -m aps_gemini_workflow.workflow_orchestrator`
except ImportError:
    # Fallback for direct execution (e.g. python workflow_orchestrator.py)
    # This assumes autodesk_api_client.py is in the same directory.
    from autodesk_api_client import DesignAutomationClient, WorkItem


# --- Configuration ---
# These should ideally be configurable via a config file, env variables, or CLI args
DYNAMO_CLI_PATH = r"C:\Program Files\Dynamo\Dynamo Core\2.0\DynamoCLI.exe" # User's example path
DEFAULT_ACTIVITY_JSON = "activity.json" # Assumed to be in the same dir or path provided
DEFAULT_INPUT_RVT = "input.rvt"
DEFAULT_OUTPUT_RVT = "result.rvt"
DEFAULT_DYNAMO_SCRIPT = r"C:\ruta\mi_script.dyn" # User's example path

# MCP Server details (points to our rsa_gemini_mcp_server.py)
MCP_SERVER_BASE_URL = "http://localhost:8000" # Default from rsa_gemini_mcp_server.py


# --- Minimal MCP Client (Placeholder) ---
# This is a placeholder for the user's "gemini-mcp-client".
# A real client would be more robust, handle discovery, authentication, etc.
class MCPClient:
    """
    A minimal placeholder client to interact with the conceptual MCP server
    (rsa_gemini_mcp_server.py).
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.invoke_url = f"{self.base_url}/invoke_tool"
        self.tools_url = f"{self.base_url}/tools"
        print(f"MCPClient initialized for server: {self.base_url}")

    def list_tools(self) -> list:
        """Lists available tools from the MCP server."""
        try:
            response = requests.get(self.tools_url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"MCPClient Error: Could not list tools from {self.tools_url}. {e}")
            return []
        except json.JSONDecodeError:
            print(f"MCPClient Error: Could not parse JSON response from {self.tools_url}.")
            return []


    def invoke(self, tool_name: str, tool_input: dict) -> dict:
        """
        Invokes a tool on the MCP server.

        Args:
            tool_name (str): The name of the tool to invoke.
            tool_input (dict): The input payload for the tool.

        Returns:
            dict: The response from the MCP server.
        """
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input
        }
        print(f"MCPClient: Invoking tool '{tool_name}' at {self.invoke_url} with input: {tool_input}")
        try:
            response = requests.post(self.invoke_url, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"MCPClient Error: Failed to invoke tool '{tool_name}'. {e}")
            return {"tool_name": tool_name, "status": "error", "error_message": str(e)}
        except json.JSONDecodeError:
            print(f"MCPClient Error: Could not parse JSON response when invoking '{tool_name}'.")
            return {"tool_name": tool_name, "status": "error", "error_message": "Invalid JSON response from server"}


def run_aps_design_automation(client: DesignAutomationClient, activity_json: str, input_rvt: str, output_rvt: str):
    """
    Handles the APS Design Automation part of the workflow.
    """
    print("\n--- Starting APS Design Automation Step ---")
    if not os.path.exists(activity_json):
        print(f"WARNING: Activity JSON '{activity_json}' not found. APS DA step might behave unexpectedly.")
        # Create a dummy one for simulation if autodesk_api_client also does this
        if not os.path.exists(DEFAULT_ACTIVITY_JSON) and activity_json == DEFAULT_ACTIVITY_JSON:
             print(f"INFO: Creating dummy '{DEFAULT_ACTIVITY_JSON}' for simulation based on default name.")
             dummy_activity_content = {
                "id": "OrchestratorSimulatedActivity",
                "commandLine": "$(engine.path)\\\\revitcoreconsole.exe /i $(args[InputRvt].path) /al $(appbundles[MyApp].path)",
                "parameters": { "InputRvt": {"verb": "get"}, "OutputRvt": {"verb": "put"}},
                "engine": "Autodesk.Revit+2024", "appbundles": ["MyCompany.MyApp+label"]
            }
             with open(DEFAULT_ACTIVITY_JSON, 'w') as f:
                json.dump(dummy_activity_content, f, indent=2)


    # Ensure client has a token (simulated auth if needed)
    if not client.token:
        print("Orchestrator: APS client has no token, attempting simulated authentication...")
        client._get_oauth_token()
        if not client.token:
            print("Orchestrator: ERROR - Could not obtain APS token. Skipping Design Automation.")
            return None # Indicate failure or inability to proceed

    if not client.token: # Check again
        print("Orchestrator: ERROR - APS Token still missing after attempt. Skipping Design Automation.")
        return None

    print(f"Orchestrator: Submitting WorkItem with Activity: '{activity_json}', Input: '{input_rvt}', Output: '{output_rvt}'")
    workitem = client.create_workitem(activity_json, input_rvt, output_rvt)

    if workitem and workitem.id != "error_no_token":
        print(f"Orchestrator: WorkItem submitted (simulated): ID '{workitem.id}'")
        final_status = client.wait_for_completion(workitem.id, interval=1) # Short interval for demo
        print(f"Orchestrator: APS Design Automation processing finished. Final status: '{final_status}'")
        if final_status == "success":
            print(f"Orchestrator: Revit model processed (simulated). Expected output at '{output_rvt}' (simulated download/availability).")
            return output_rvt # Path to the (simulated) processed file
        else:
            print(f"Orchestrator: APS Design Automation failed or ended with status: {final_status}.")
            return None
    else:
        print("Orchestrator: Failed to submit APS WorkItem (simulated).")
        return None

def run_dynamo_local(dynamo_cli_path: str, dynamo_script_path: str):
    """
    Handles the local Dynamo execution part of the workflow.
    """
    print("\n--- Starting Local Dynamo Execution Step ---")
    if not os.path.exists(dynamo_cli_path):
        print(f"ERROR: DynamoCLI.exe not found at '{dynamo_cli_path}'. Skipping Dynamo execution.")
        print("Please configure DYNAMO_CLI_PATH in the script or provide it via CLI.")
        return False

    if not os.path.exists(dynamo_script_path):
        print(f"ERROR: Dynamo script '.dyn' not found at '{dynamo_script_path}'. Skipping Dynamo execution.")
        return False

    command = [dynamo_cli_path, "-o", dynamo_script_path] # User's example command structure
    # For more complex DynamoCLI usage, you might need:
    # - "-vm": to specify the Revit version model view
    # - "-gp": to specify geometry partitioning
    # - "-ipar": to pass input parameters (if DynamoCLI supports this directly, often handled within the .dyn)

    print(f"Orchestrator: Executing Dynamo script: {' '.join(command)}")
    try:
        # Using shell=True can be a security risk if paths are user-supplied directly without sanitization.
        # For fixed paths or controlled inputs, it can be okay. For robustness, avoid if possible.
        # Here, paths are defined or CLI-arg-parsed, so less risk than raw user input mid-script.
        result = subprocess.run(command, check=True, capture_output=True, text=True, shell=False)
        print(f"Orchestrator: Dynamo script '{dynamo_script_path}' executed successfully (simulated).")
        print(f"  Dynamo Output (stdout):\n{result.stdout}")
        if result.stderr:
            print(f"  Dynamo Output (stderr):\n{result.stderr}")
        return True
    except FileNotFoundError:
        print(f"ERROR: DynamoCLI.exe not found at path '{dynamo_cli_path}'. Make sure it's correct and in PATH or use full path.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Orchestrator: Dynamo script execution failed for '{dynamo_script_path}'.")
        print(f"  Return code: {e.returncode}")
        print(f"  Stdout:\n{e.stdout}")
        print(f"  Stderr:\n{e.stderr}")
        return False
    except Exception as e:
        print(f"Orchestrator: An unexpected error occurred while running Dynamo script: {e}")
        return False

def interact_with_mcp_server(mcp_client: MCPClient, processed_revit_file_path: str = None):
    """
    Handles the interaction with the MCP server.
    """
    print("\n--- Starting MCP Server Interaction Step ---")

    print("Orchestrator: Listing tools from MCP server...")
    tools = mcp_client.list_tools()
    if tools:
        print(f"Orchestrator: Available MCP tools: {[tool.get('name') for tool in tools]}")
    else:
        print("Orchestrator: WARNING - Could not retrieve tools from MCP server, or no tools available.")

    # Example: Invoke a tool on the MCP server, potentially using the output from APS
    # This matches the user's Step 6 example: mcp.invoke("open_revit_model", {"path": "result.rvt"})
    tool_to_invoke = "open_revit_model" # From rsa_gemini_mcp_server.py
    payload = {}

    if processed_revit_file_path:
        payload["path"] = processed_revit_file_path
        print(f"Orchestrator: Attempting to invoke '{tool_to_invoke}' on MCP server with path: '{processed_revit_file_path}'")
    else:
        # Fallback if previous step failed or didn't produce a file path
        default_model_for_mcp = "dummy_model.rvt" # A placeholder
        payload["path"] = default_model_for_mcp
        print(f"Orchestrator: No processed Revit file path from APS. Attempting to invoke '{tool_to_invoke}' on MCP server with DUMMY path: '{default_model_for_mcp}'")

    response = mcp_client.invoke(tool_to_invoke, payload)
    print(f"Orchestrator: MCP server response for '{tool_to_invoke}':")
    print(json.dumps(response, indent=2))

    if response.get("status") == "success":
        print(f"Orchestrator: MCP tool '{tool_to_invoke}' invoked successfully.")
    else:
        print(f"Orchestrator: MCP tool '{tool_to_invoke}' invocation failed or reported an error.")
        print(f"  Details: {response.get('error_message', 'No error message provided.')}")


def main(args):
    """
    Main orchestration logic.
    """
    print("--- Workflow Orchestrator Started ---")
    print(f"  APS Activity JSON: {args.activity_json}")
    print(f"  APS Input RVT: {args.input_rvt}")
    print(f"  APS Output RVT: {args.output_rvt}")
    print(f"  Dynamo CLI: {args.dynamo_cli}")
    print(f"  Dynamo Script: {args.dynamo_script}")
    print(f"  MCP Server URL: {args.mcp_url}")

    # 1. APS Design Automation
    aps_client = DesignAutomationClient() # Uses auth_config.py implicitly
    processed_revit_file = run_aps_design_automation(aps_client, args.activity_json, args.input_rvt, args.output_rvt)

    # 2. Local Dynamo Execution
    # This could run in parallel or conditionally based on APS step, depending on workflow needs.
    # For this example, running it sequentially.
    dynamo_success = run_dynamo_local(args.dynamo_cli, args.dynamo_script)
    if dynamo_success:
        print("Orchestrator: Dynamo execution step completed.")
    else:
        print("Orchestrator: Dynamo execution step encountered errors or was skipped.")

    # 3. MCP Server Interaction (via Gemini or direct commands)
    # The user's example shows direct MCP client usage.
    # The `fastmcp_controller` in this repo shows how Gemini could be used to *formulate* commands for an MCP server.
    # Here, we'll use the direct MCPClient placeholder.
    mcp_client = MCPClient(base_url=args.mcp_url)

    # Pass the output of the APS step (if successful) to the MCP interaction
    interact_with_mcp_server(mcp_client, processed_revit_file_path=processed_revit_file)

    print("\n--- Workflow Orchestrator Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrates APS, Dynamo, and MCP interactions.")
    parser.add_argument("--activity-json", type=str, default=DEFAULT_ACTIVITY_JSON, help="Path to APS activity JSON file.")
    parser.add_argument("--input-rvt", type=str, default=DEFAULT_INPUT_RVT, help="Path to input RVT file for APS.")
    parser.add_argument("--output-rvt", type=str, default=DEFAULT_OUTPUT_RVT, help="Path for output RVT file from APS.")

    parser.add_argument("--dynamo-cli", type=str, default=DYNAMO_CLI_PATH, help="Path to DynamoCLI.exe.")
    parser.add_argument("--dynamo-script", type=str, default=DEFAULT_DYNAMO_SCRIPT, help="Path to the .dyn script to execute.")

    parser.add_argument("--mcp-url", type=str, default=MCP_SERVER_BASE_URL, help="Base URL of the MCP Server.")

    cli_args = parser.parse_args()

    # Basic check for critical paths before starting
    if cli_args.dynamo_cli == DYNAMO_CLI_PATH and not os.path.exists(DYNAMO_CLI_PATH):
        print(f"WARNING: Default DynamoCLI path '{DYNAMO_CLI_PATH}' does not exist. "
              "The Dynamo step will likely fail unless a valid path is provided via --dynamo-cli.")
    if cli_args.dynamo_script == DEFAULT_DYNAMO_SCRIPT and not os.path.exists(DEFAULT_DYNAMO_SCRIPT):
         print(f"WARNING: Default Dynamo script path '{DEFAULT_DYNAMO_SCRIPT}' does not exist. "
              "The Dynamo step will likely fail unless a valid path is provided via --dynamo-script.")


    main(cli_args)

    # Example of how to run this:
    # Assuming rsa_gemini_mcp_server.py is running on localhost:8000
    # And assuming dummy files input.rvt, activity.json, and C:\ruta\mi_script.dyn exist (or paths are overridden)
    #
    # python workflow_orchestrator.py
    #   --activity-json "path/to/my_activity.json"
    #   --input-rvt "path/to/my_input.rvt"
    #   --output-rvt "path/to/my_output.rvt"
    #   --dynamo-cli "C:/Program Files/Dynamo/Dynamo Core/version/DynamoCLI.exe"
    #   --dynamo-script "path/to/my_script.dyn"
    #   --mcp-url "http://localhost:8000"
    #
    # Since many paths are placeholders, it will show warnings or errors for missing files,
    # but the simulation logic for APS and MCP should still run.
    # The Dynamo step will likely fail if the paths are not valid on your system.
