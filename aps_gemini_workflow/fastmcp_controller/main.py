import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

from gemini_client import GeminiClient
from app_controller import AppController

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file at the start
load_dotenv()

async def show_menu():
    """Displays the interactive menu to the user."""
    print("\n--- FastMCP Controller Menu ---")
    print("1. List Connected Applications")
    print("2. Send Command to Application (via direct input)")
    print("3. Send Command to Application (via Gemini)")
    print("4. Monitor Application Status (WebSocket - if configured)")
    print("5. Get Application Status (REST - if configured)")
    print("0. Exit")
    return input("Choose an option: ")

async def handle_list_apps(controller: AppController):
    """Handles listing connected applications."""
    logging.info("Fetching connected applications...")
    apps = controller.get_connected_apps() # This is synchronous in the current AppController for REST
    if apps:
        logging.info("Connected Applications:")
        for i, app in enumerate(apps):
            # The structure of 'app' depends on your FastMCP API
            if isinstance(app, dict):
                print(f"  {i+1}. ID: {app.get('id', 'N/A')}, Name: {app.get('name', 'N/A')}, Status: {app.get('status', 'N/A')}")
            else:
                print(f"  {i+1}. App Data: {app}") # Fallback for non-dict app items
    else:
        logging.warning("No applications found or failed to retrieve list.")

async def handle_send_command_direct(controller: AppController):
    """Handles sending a command directly to an application."""
    app_id = input("Enter Application ID: ")
    command = input("Enter Command: ")
    payload_str = input("Enter Payload (JSON string, e.g., {\"key\": \"value\"}, or leave blank): ")
    payload = None
    if payload_str:
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            logging.error("Invalid JSON payload. Sending command without payload.")

    logging.info(f"Sending command '{command}' to app '{app_id}' with payload: {payload}")
    response = controller.send_command(app_id, command, payload) # Synchronous in current AppController
    logging.info(f"Server Response: {response}")

async def handle_send_command_gemini(gemini: GeminiClient, controller: AppController):
    """Handles sending a command formulated by Gemini."""
    user_instruction = input("Describe the action you want to perform (Gemini will formulate the command): ")

    # This is a simplified example. You might need a more sophisticated prompt
    # engineering approach to get reliable JSON commands from Gemini.
    # Consider providing Gemini with a schema of possible commands and app IDs.
    prompt = f"""
    You are an assistant that translates natural language instructions into JSON commands for a FastMCP server.
    The user wants to perform an action on a connected application.
    Your task is to determine the application ID, the command name, and any necessary payload.

    Available applications (example, actual list might differ):
    - {{ id: "app_heater_001", name: "Living Room Heater", capabilities: ["set_temp", "get_status", "toggle_power"] }}
    - {{ id: "app_light_002", name: "Kitchen Light", capabilities: ["toggle_power", "set_brightness"] }}
    - {{ id: "app_robot_003", name: "Vacuum Robot", capabilities: ["start_cleaning", "dock", "get_battery"] }}

    User instruction: "{user_instruction}"

    Based on the instruction, generate a JSON object with the following fields:
    - "target_app_id": string (The ID of the application to command)
    - "command": string (The command to execute, e.g., "set_temp", "toggle_power")
    - "payload": object (A JSON object containing parameters for the command, e.g., {{"temperature": 22}}, {{"brightness": 75}}. Use an empty object {{}} if no payload is needed.)

    If you cannot determine the necessary information or if the instruction is unclear, respond with:
    {{"error": "Could not determine command from instruction. Please be more specific or provide app ID and command directly."}}

    Generate ONLY the JSON object.
    """

    logging.info("Sending instruction to Gemini for command formulation...")
    try:
        gemini_response_str = gemini.send_instruction(prompt)
        logging.info(f"Gemini Raw Response: {gemini_response_str}")

        # Attempt to parse the Gemini response as JSON
        # Gemini might sometimes add markdown backticks around JSON, try to strip them.
        if gemini_response_str.startswith("```json"):
            gemini_response_str = gemini_response_str.replace("```json", "").replace("```", "").strip()

        command_data = json.loads(gemini_response_str)

        if "error" in command_data:
            logging.error(f"Gemini Error: {command_data['error']}")
            return

        app_id = command_data.get("target_app_id")
        command = command_data.get("command")
        payload = command_data.get("payload", {})

        if not app_id or not command:
            logging.error("Gemini response did not include 'target_app_id' or 'command'.")
            print(f"Received from Gemini: app_id='{app_id}', command='{command}'")
            return

        logging.info(f"Gemini formulated: App ID='{app_id}', Command='{command}', Payload='{payload}'")
        confirmation = input(f"Send this command? (yes/no): ").lower()
        if confirmation == 'yes':
            response = controller.send_command(app_id, command, payload) # Synchronous
            logging.info(f"Server Response: {response}")
        else:
            logging.info("Command cancelled by user.")

    except json.JSONDecodeError:
        logging.error(f"Failed to parse Gemini response as JSON. Response was: {gemini_response_str}")
    except Exception as e:
        logging.error(f"Error processing Gemini command: {e}")


async def status_update_callback(status_data):
    """Callback function to print status updates from WebSocket."""
    logging.info(f"[WebSocket Status - App: {status_data.get('app_id', 'N/A')}]: {status_data}")

async def handle_monitor_status_ws(controller: AppController):
    """Handles monitoring application status via WebSocket."""
    if not controller.is_websocket_url:
        logging.warning("WebSocket monitoring is only available if FASTMCP_SERVER_URL starts with 'ws://' or 'wss://'.")
        return

    app_id = input("Enter Application ID to monitor (leave blank to attempt monitoring all if supported by server): ")
    if not app_id: # This part is highly server-dependent; some servers might stream all, others need specific subs
        logging.info("Attempting to monitor all application statuses (if server supports).")
    else:
        logging.info(f"Attempting to monitor status for app '{app_id}' via WebSocket...")

    try:
        # The monitor_status_websocket needs to be run and managed.
        # It will run indefinitely until the connection closes or an error occurs.
        await controller.monitor_status_websocket(app_id if app_id else None, status_update_callback)
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"WebSocket connection closed for app '{app_id}'.")
    except Exception as e:
        logging.error(f"Failed to monitor status for app '{app_id}': {e}")
    finally:
        logging.info("Stopped monitoring status.")


async def handle_get_status_rest(controller: AppController):
    """Handles getting application status via REST."""
    if controller.is_websocket_url:
        logging.info("Server is configured for WebSocket. For real-time updates, use option 4. This option is for REST polling.")

    app_id = input("Enter Application ID to get status for: ")
    if not app_id:
        logging.warning("Application ID cannot be empty.")
        return

    logging.info(f"Fetching status for app '{app_id}' via REST...")
    status = controller.get_app_status_rest(app_id) # Synchronous
    logging.info(f"App '{app_id}' Status: {status}")


async def main():
    """Main function to run the FastMCP Controller."""
    # Initialize clients
    try:
        gemini_client = GeminiClient()
        app_controller = AppController()
    except ValueError as e:
        logging.error(f"Initialization failed: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred during initialization: {e}")
        sys.exit(1)

    # Import json here as it's used in some handlers
    # (Could be global but placed here to show it's used after init)
    global json
    import json # Make json available to handlers that might need it.

    # Import websockets here for type checking in handlers
    global websockets
    import websockets


    while True:
        choice = await show_menu()
        try:
            if choice == '1':
                await handle_list_apps(app_controller)
            elif choice == '2':
                await handle_send_command_direct(app_controller)
            elif choice == '3':
                await handle_send_command_gemini(gemini_client, app_controller)
            elif choice == '4':
                await handle_monitor_status_ws(app_controller)
            elif choice == '5':
                await handle_get_status_rest(app_controller)
            elif choice == '0':
                logging.info("Exiting FastMCP Controller.")
                break
            else:
                logging.warning("Invalid option. Please try again.")
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}", exc_info=True) # Log stack trace

        # Add a small delay or prompt to continue, especially after actions
        if choice not in ['0', '4']: # Don't pause if exiting or monitoring
             input("Press Enter to continue...")


if __name__ == "__main__":
    # Check if FASTMCP_SERVER_URL is set, as it's crucial
    if not os.getenv("FASTMCP_SERVER_URL"):
        logging.error("FASTMCP_SERVER_URL is not set in the .env file. Please configure it.")
        sys.exit(1)
    if not os.getenv("GEMINI_API_KEY"):
        logging.error("GEMINI_API_KEY is not set in the .env file. Please configure it.")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nApplication interrupted by user. Exiting...")
    except Exception as e:
        logging.critical(f"Unhandled exception in asyncio.run(main()): {e}", exc_info=True)
    finally:
        logging.info("Application shutdown complete.")
