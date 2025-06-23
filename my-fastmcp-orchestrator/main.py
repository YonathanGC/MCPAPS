# main.py
# This script will orchestrate the different modules to connect to FastMCP,
# interpret user commands via an AI model, and control various CAD/GIS applications.

import os
import time # For sleep
import threading # For graceful shutdown
from dotenv import load_dotenv

# Import custom modules
import fastmcp_client
import ai_controller
from apps import (
    revit_client,
    autocad_client,
    civil3d_client,
    robot_client,
    dynamo_client,
    arcgis_client,
    qgis_client
)

# --- Configuration & State ---
# Load environment variables from .env file
load_dotenv()

# Application clients mapping
APP_CLIENTS = {
    "revit": revit_client,
    "autocad": autocad_client,
    "civil3d": civil3d_client,
    "robot": robot_client,
    "dynamo": dynamo_client,
    "arcgis": arcgis_client,
    "qgis": qgis_client,
}

# Event to signal shutdown
shutdown_event = threading.Event()

# --- Core Functions ---

def select_app_client(app_name: str):
    """
    Selects the appropriate application client based on the app name.
    Logs a warning if the client is not found.

    Args:
        app_name (str): The name of the target application (e.g., "revit", "autocad").

    Returns:
        module or None: The client module if found, otherwise None.
    """
    app_name_lower = app_name.lower() if app_name else None
    client = APP_CLIENTS.get(app_name_lower)
    if not client:
        print(f"Warning: No application client found for '{app_name}'. Available clients: {list(APP_CLIENTS.keys())}")
    return client

def process_task(instruction: dict):
    """
    Processes a structured instruction from the AI controller to interact with an application.

    Args:
        instruction (dict): The structured task from `ai_controller.interpret()`.
                            Expected to contain 'target_app', 'action', and 'parameters'.
    """
    if not isinstance(instruction, dict) or instruction.get("error"):
        print(f"Error in instruction: {instruction.get('error', 'Invalid instruction format.')}")
        fastmcp_client.send({
            "status": "error",
            "original_instruction": instruction,
            "error_message": instruction.get('error', 'Invalid instruction format from AI.')
        })
        return

    target_app_name = instruction.get("target_app")
    action_details = instruction # The whole instruction dict can be useful for the client
                                  # or just instruction.get("parameters")

    print(f"Processing task for target application: {target_app_name}")
    fastmcp_client.send({"status": "processing_started", "target_app": target_app_name, "instruction": instruction})


    app_client = select_app_client(target_app_name)
    if not app_client:
        error_msg = f"Application client for '{target_app_name}' not found."
        print(error_msg)
        fastmcp_client.send({"status": "error", "original_instruction": instruction, "error_message": error_msg})
        return

    try:
        # --- Application Interaction Workflow ---
        # 1. Connect to the application (idempotent or actual connection)
        #    Specific connection parameters might come from instruction['parameters'] or be predefined.
        print(f"Connecting to {target_app_name} via client...")
        if not app_client.connect(): # Assuming connect returns True on success
            error_msg = f"Failed to connect to {target_app_name}."
            print(error_msg)
            fastmcp_client.send({"status": "error", "original_instruction": instruction, "error_message": error_msg})
            return
        print(f"Successfully connected to {target_app_name}.")

        # 2. Load project (if specified in parameters)
        project_path = instruction.get("parameters", {}).get("project_path") # Standardized parameter name
        if project_path:
            print(f"Loading project '{project_path}' in {target_app_name}...")
            if not app_client.load_project(project_path):
                error_msg = f"Failed to load project '{project_path}' in {target_app_name}."
                print(error_msg)
                fastmcp_client.send({"status": "error", "original_instruction": instruction, "error_message": error_msg})
                return
            print(f"Project '{project_path}' loaded successfully.")

        # 3. Generate code/commands (if needed, or if AI provides direct commands)
        #    The AI might provide a high-level task that the client interprets,
        #    or the AI might provide specific code/commands.
        #    For this example, we assume `ai_controller.generate_code` provides the executable part.

        # Pass the full interpreted instruction to generate_code, as it might contain all necessary details
        code_or_command_sequence = ai_controller.generate_code(instruction)
        if "Error:" in code_or_command_sequence : # Check if generation failed
             error_msg = f"AI code generation failed: {code_or_command_sequence}"
             print(error_msg)
             fastmcp_client.send({"status": "error", "original_instruction": instruction, "error_message": error_msg})
             return

        print(f"AI generated code/commands for {target_app_name}:\n---\n{code_or_command_sequence}\n---")

        # 4. Apply changes / execute commands
        #    The `apply_changes` function in the client needs to know how to handle
        #    the output of `generate_code` or the structured `action_details`.
        #    We'll pass a dictionary that includes the generated code and the original instruction.
        changes_payload = {
            "generated_code": code_or_command_sequence,
            "original_instruction": instruction # Client might need more context from the original interpretation
        }
        print(f"Applying changes to {target_app_name}...")
        apply_result = app_client.apply_changes(changes_payload) # apply_changes should return a dict

        if not apply_result or apply_result.get("status") == "failed":
            error_msg = f"Failed to apply changes in {target_app_name}. Details: {apply_result.get('error', 'Unknown error')}"
            print(error_msg)
            fastmcp_client.send({
                "status": "error",
                "original_instruction": instruction,
                "error_message": error_msg,
                "app_client_response": apply_result
            })
            return
        print(f"Changes applied successfully in {target_app_name}.")

        # 5. Export data (if specified)
        export_params = instruction.get("parameters", {}).get("export_details") # e.g., {"output_dir": "...", "format": "..."}
        if export_params and isinstance(export_params, dict) and "output_dir" in export_params:
            print(f"Exporting from {target_app_name} to '{export_params['output_dir']}'...")
            # Pass all export_params to the client's export function
            export_result = app_client.export(**export_params)

            if not export_result or export_result.get("status") == "failed":
                error_msg = f"Export failed from {target_app_name}. Details: {export_result.get('error', 'Unknown error')}"
                print(error_msg)
                fastmcp_client.send({
                    "status": "error",
                    "original_instruction": instruction,
                    "error_message": error_msg,
                    "app_client_response": export_result
                })
                return # Or decide if partial success is okay
            print(f"Export successful: {export_result.get('exported_files', 'No files listed')}")
            fastmcp_client.send({
                "status": "export_completed",
                "details": export_result,
                "original_instruction": instruction
            })


        # 6. Get final status from the application
        final_status = app_client.get_status()
        print(f"Final status from {target_app_name}: {final_status}")
        fastmcp_client.send({
            "status": "task_completed",
            "target_app_status": final_status,
            "original_instruction": instruction,
            "app_client_apply_response": apply_result
        })

    except Exception as e:
        error_msg = f"An unexpected error occurred while processing task for {target_app_name}: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        fastmcp_client.send({"status": "error", "original_instruction": instruction, "error_message": error_msg})


def handle_fastmcp_message(message: dict):
    """
    Callback function to process messages received from FastMCP.
    This is where the orchestration logic begins for incoming commands.
    """
    print(f"\nReceived message from FastMCP: {message}")

    prompt = message.get("prompt") # Assuming FastMCP sends prompts in this format
    if not prompt:
        # Handle other message types from FastMCP if necessary
        print(f"Received non-prompt message or invalid format: {message}")
        fastmcp_client.send({"status": "received_unknown_message", "original_message": message})
        return

    print(f"Interpreting prompt: '{prompt}'")
    fastmcp_client.send({"status": "interpreting_prompt", "prompt": prompt})

    # 1. Interpret the prompt using AI Controller
    instruction = ai_controller.interpret(prompt)
    print(f"AI Interpreted Instruction: {instruction}")

    if instruction.get("error"):
        print(f"AI interpretation failed: {instruction.get('details', instruction['error'])}")
        fastmcp_client.send({
            "status": "interpretation_failed",
            "prompt": prompt,
            "error_details": instruction
        })
        return

    fastmcp_client.send({
        "status": "interpretation_successful",
        "prompt": prompt,
        "instruction": instruction
    })

    # 2. Process the interpreted task
    process_task(instruction)


def main():
    """
    Main function to run the FastMCP Orchestrator.
    Initializes modules, connects to FastMCP, and enters a loop (or waits for events).
    """
    print("🚀 FastMCP Orchestrator Initializing...")

    # 1. Initialize AI Controller
    print("Authenticating AI Controller...")
    if not ai_controller.authenticate(): # Uses GEMINI_API_KEY from .env by default
        print("❌ AI Controller authentication failed. Please check API key and configuration.")
        # Decide if the application should exit or run with limited capabilities
        # For now, we'll let it continue, but AI features will fail.
    else:
        print("✅ AI Controller authenticated successfully.")

    # 2. Configure and Connect to FastMCP
    # URL, Port, Token can be overridden here if not using .env defaults
    # e.g., fastmcp_client.connect(url="ws://custom.server:8000", token="mysecrettoken")
    print("Connecting to FastMCP server...")
    fastmcp_client.on_message(handle_fastmcp_message) # Register callback before connecting
    fastmcp_client.connect()

    # Check if connection was successful (this is a bit tricky with the async client)
    # We'll rely on logs from fastmcp_client for now, or add a status check if client supports it.
    # A small delay to allow connection attempt.
    print("Allowing time for FastMCP connection...")
    time.sleep(3) # Adjust as needed, or implement a more robust check

    if not fastmcp_client._websocket_connection or not fastmcp_client._websocket_connection.open:
         print("❌ Failed to connect to FastMCP server. Check server status and .env configuration.")
         print("   Ensure FASTMCP_URL is correct (e.g., ws://localhost:8765).")
         # No point in continuing if FastMCP connection fails and it's essential.
         # return # Uncomment to exit if FastMCP is crucial
    else:
        print("✅ FastMCP client initiated connection (check logs for actual connection status).")


    # 3. Main loop / Keep alive
    # The FastMCP client runs its WebSocket listener in a background thread.
    # This main thread can do other work or simply wait for a shutdown signal.
    print("\nOrchestrator is running. Waiting for FastMCP messages or shutdown signal (Ctrl+C)...")
    try:
        while not shutdown_event.is_set():
            # Keep the main thread alive.
            # Could perform periodic checks or tasks here if needed.
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🚨 KeyboardInterrupt received. Shutting down...")
    finally:
        print("Initiating shutdown sequence...")
        shutdown_event.set() # Signal other parts of the app if necessary

        # Disconnect from FastMCP
        print("Disconnecting from FastMCP server...")
        fastmcp_client.disconnect()

        # Stop the asyncio event loop if it was started by fastmcp_client
        # This assumes fastmcp_client exposes a way to stop its loop or does it on disconnect.
        if hasattr(fastmcp_client, '_stop_async_loop'):
             print("Stopping FastMCP client's async loop...")
             fastmcp_client._stop_async_loop()

        print("🔌 FastMCP Orchestrator shut down successfully.")


if __name__ == "__main__":
    main()
