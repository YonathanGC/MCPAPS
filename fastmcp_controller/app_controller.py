import os
import json
import requests # For RESTful API calls
import asyncio # For WebSocket communication (if needed)
import websockets # For WebSocket communication
from dotenv import load_dotenv

class AppController:
    """
    Controls applications connected to a FastMCP server.

    This class handles communication with the FastMCP server to:
    - Retrieve a list of connected applications.
    - Send commands to specific applications.
    - Monitor the status of applications (can be via REST polling or WebSocket).
    """

    def __init__(self):
        """
        Initializes the AppController.
        Loads FastMCP server URL and authentication token from environment variables.
        """
        load_dotenv()
        self.server_url = os.getenv("FASTMCP_SERVER_URL")
        self.auth_token = os.getenv("FASTMCP_AUTH_TOKEN") # Optional

        if not self.server_url:
            raise ValueError("FASTMCP_SERVER_URL not found in environment variables. Please set it in your .env file.")

        self.headers = {"Content-Type": "application/json"}
        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"

        # Determine if the URL is for WebSocket or HTTP
        self.is_websocket_url = self.server_url.startswith("ws://") or self.server_url.startswith("wss://")

        print(f"AppController initialized for server: {self.server_url}")
        if self.is_websocket_url:
            print("Configured for WebSocket communication.")
        else:
            print("Configured for REST API communication.")

    def get_connected_apps(self) -> list:
        """
        Retrieves a list of applications currently connected to the FastMCP server.

        Returns:
            A list of application identifiers or objects.
            The actual structure depends on the FastMCP API response.

        Note: This is a placeholder. You'll need to adapt the endpoint and response parsing.
        """
        if self.is_websocket_url:
            print("get_connected_apps via WebSocket is not implemented in this example. Requires specific protocol.")
            # Example of how one might structure a WebSocket request/response for this:
            # async def _get_apps_ws():
            #     async with websockets.connect(self.server_url, extra_headers=self.headers if self.auth_token else None) as websocket:
            #         await websocket.send(json.dumps({"action": "list_apps"}))
            #         response = await websocket.recv()
            #         return json.loads(response)
            # return asyncio.run(_get_apps_ws())
            return [{"id": "app_ws_dummy_1", "name": "Dummy WebSocket App 1", "status": "connected"}] # Placeholder
        else:
            # Assuming a REST endpoint like /apps or /connected_devices
            apps_endpoint = f"{self.server_url.rstrip('/')}/apps"
            print(f"Fetching connected apps from REST endpoint: {apps_endpoint}")
            try:
                response = requests.get(apps_endpoint, headers=self.headers)
                response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
                apps_data = response.json()
                # Example: FastMCP might return a list of app objects or a dict with an 'apps' key
                return apps_data.get("apps", apps_data) if isinstance(apps_data, dict) else apps_data
            except requests.exceptions.RequestException as e:
                print(f"Error fetching connected apps: {e}")
                return []
            except json.JSONDecodeError:
                print("Error decoding JSON response from server.")
                return []

    def send_command(self, app_id: str, command: str, payload: dict = None) -> dict:
        """
        Sends a command to a specific application via the FastMCP server.

        Args:
            app_id: The identifier of the application to command.
            command: The command string or identifier.
            payload: An optional dictionary for command parameters.

        Returns:
            A dictionary containing the server's response to the command.

        Note: This is a placeholder. Adapt endpoint, request body, and response parsing.
        """
        if not app_id or not command:
            raise ValueError("app_id and command must be provided.")

        request_body = {
            "command": command,
            "target_app_id": app_id,
            "payload": payload if payload else {}
        }

        if self.is_websocket_url:
            print(f"Sending command to {app_id} via WebSocket is not fully implemented in this example.")
            # async def _send_command_ws():
            #     async with websockets.connect(self.server_url, extra_headers=self.headers if self.auth_token else None) as websocket:
            #         await websocket.send(json.dumps({"action": "send_command", "data": request_body}))
            #         response = await websocket.recv()
            #         return json.loads(response)
            # return asyncio.run(_send_command_ws())
            print(f"Simulating WebSocket command: App: {app_id}, Command: {command}, Payload: {payload}")
            return {"status": "success", "message": f"Command '{command}' hypothetically sent to {app_id} via WebSocket."} # Placeholder
        else:
            # Assuming a REST endpoint like /apps/{app_id}/command
            command_endpoint = f"{self.server_url.rstrip('/')}/apps/{app_id}/command"
            print(f"Sending command to REST endpoint: {command_endpoint} with payload: {request_body}")
            try:
                response = requests.post(command_endpoint, json=request_body, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error sending command to {app_id}: {e}")
                return {"status": "error", "message": str(e)}
            except json.JSONDecodeError:
                print("Error decoding JSON response from server.")
                return {"status": "error", "message": "Invalid JSON response"}

    async def monitor_status_websocket(self, app_id: str, callback):
        """
        Monitors the status of a specific application in real-time using WebSockets.
        This function is designed to be run with asyncio.

        Args:
            app_id: The identifier of the application to monitor.
            callback: A function to call with each status update received.
                      The callback should accept one argument (the status message/data).
        """
        if not self.is_websocket_url:
            print("Status monitoring is intended for WebSocket URLs. For REST, use periodic polling with get_app_status().")
            return

        # Example: ws://server/status/{app_id} or a general ws endpoint that needs a subscription message
        # This is highly dependent on the FastMCP WebSocket API design.
        # For this example, let's assume the main server URL is the WebSocket endpoint,
        # and we need to send a "subscribe" message.

        status_uri = self.server_url # Or a specific status endpoint if different
        print(f"Attempting to connect to WebSocket for status monitoring: {status_uri} for app {app_id}")

        try:
            async with websockets.connect(status_uri, extra_headers=self.headers if self.auth_token else None) as websocket:
                # Send a subscription message (this is specific to your FastMCP server's protocol)
                subscribe_message = json.dumps({
                    "action": "subscribe_status",
                    "app_id": app_id
                })
                await websocket.send(subscribe_message)
                print(f"Subscribed to status updates for app {app_id}.")

                while True:
                    try:
                        message = await websocket.recv()
                        status_data = json.loads(message)
                        # Filter or check if the message is for the correct app_id if the channel is shared
                        if status_data.get("app_id") == app_id or status_data.get("target_app_id") == app_id or not status_data.get("app_id"):
                             await callback(status_data) # Pass data to callback
                    except websockets.exceptions.ConnectionClosed:
                        print(f"WebSocket connection closed for app {app_id}.")
                        break
                    except json.JSONDecodeError:
                        print(f"Received non-JSON message: {message}")
                    except Exception as e:
                        print(f"Error during WebSocket communication for {app_id}: {e}")
                        break
        except websockets.exceptions.InvalidURI:
            print(f"Invalid WebSocket URI: {status_uri}")
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket connection failed for {app_id}: {e}")
        except ConnectionRefusedError:
            print(f"Connection refused by the server at {status_uri}")


    def get_app_status_rest(self, app_id: str) -> dict:
        """
        Retrieves the current status of a specific application using a REST endpoint.
        This is for polling if WebSockets are not used or not available for status.

        Args:
            app_id: The identifier of the application.

        Returns:
            A dictionary containing the application's status.
        """
        if self.is_websocket_url:
            print("For WebSocket URLs, use monitor_status_websocket for real-time updates.")
            # Fallback or error? Or maybe some apps have REST status even if main is WS?
            return {"status": "info", "message": "Use monitor_status_websocket for WebSocket setups."}

        status_endpoint = f"{self.server_url.rstrip('/')}/apps/{app_id}/status"
        print(f"Fetching status for app {app_id} from REST endpoint: {status_endpoint}")
        try:
            response = requests.get(status_endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching status for {app_id}: {e}")
            return {"status": "error", "message": str(e)}
        except json.JSONDecodeError:
            print("Error decoding JSON response from server.")
            return {"status": "error", "message": "Invalid JSON response"}

# --- Example Usage and Testing ---
async def example_status_callback(status_data):
    """Callback function to print status updates."""
    print(f"[Real-time Status Update]: {status_data}")

async def main_test():
    # This test assumes a mock server or requires a running FastMCP instance.
    # For REST, you can use tools like Mockoon to simulate the API.
    # For WebSockets, it's more complex to mock without a simple echo server.

    print("--- AppController Test ---")
    # Set dummy env vars if .env is not present for testing
    if not os.getenv("FASTMCP_SERVER_URL"):
        print("Mocking FASTMCP_SERVER_URL for test as it's not in .env")
        os.environ["FASTMCP_SERVER_URL"] = "http://localhost:3000/api" # Mock REST server
        # os.environ["FASTMCP_SERVER_URL"] = "ws://localhost:8080" # Mock WebSocket server
    if not os.getenv("FASTMCP_AUTH_TOKEN") and os.environ["FASTMCP_SERVER_URL"] != "ws://localhost:8080": # Don't set for ws example unless needed
         os.environ["FASTMCP_AUTH_TOKEN"] = "test_token"


    try:
        controller = AppController()

        print("\n1. Testing Get Connected Apps (REST):")
        if not controller.is_websocket_url:
            apps = controller.get_connected_apps()
            if apps:
                print(f"Connected Apps: {apps}")
                app_to_test = apps[0]['id'] if isinstance(apps, list) and apps and isinstance(apps[0], dict) and 'id' in apps[0] else "test_app_123"
            else:
                print("No apps found or error occurred. Using dummy app ID for further tests.")
                app_to_test = "test_app_123" # Dummy ID if no apps are returned
        else:
            print("Skipping REST get_connected_apps for WebSocket URL. Using dummy app ID.")
            apps = controller.get_connected_apps() # Will use the WS placeholder
            print(f"Connected Apps (WS Placeholder): {apps}")
            app_to_test = "app_ws_dummy_1"


        print(f"\n2. Testing Send Command (to app: {app_to_test}):")
        command_response = controller.send_command(app_to_test, "start_process", {"param1": "value1"})
        print(f"Command Response: {command_response}")

        command_response_toggle = controller.send_command(app_to_test, "toggle_module", {"module_name": "logging", "state": True})
        print(f"Command Response (Toggle): {command_response_toggle}")


        if controller.is_websocket_url:
            print("\n3. Testing Monitor Status (WebSocket):")
            print("This will try to connect. If no WebSocket server is running at the URL, it will fail.")
            print("To stop monitoring, you'll need to interrupt the script (Ctrl+C).")
            # Create a dummy app_id for WebSocket testing if not available
            ws_app_id_to_monitor = app_to_test if app_to_test else "app_ws_dummy_1"
            try:
                # Run for a short period or until interrupted
                await asyncio.wait_for(controller.monitor_status_websocket(ws_app_id_to_monitor, example_status_callback), timeout=10.0)
            except asyncio.TimeoutError:
                print(f"WebSocket monitoring test for {ws_app_id_to_monitor} timed out after 10s.")
            except Exception as e:
                print(f"WebSocket monitoring test for {ws_app_id_to_monitor} failed: {e}")
        else:
            print("\n3. Testing Get App Status (REST Polling):")
            status_response = controller.get_app_status_rest(app_to_test)
            print(f"App Status Response: {status_response}")


    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred in test: {e}")

if __name__ == "__main__":
    # To run the WebSocket parts, you need an event loop.
    # For simple scripts, asyncio.run() is fine.
    # If integrating into a larger asyncio app, manage the loop externally.
    if any("ws://" in os.getenv("FASTMCP_SERVER_URL", "") or "wss://" in os.getenv("FASTMCP_SERVER_URL", "") for _ in '_'): # Check if WS likely
        asyncio.run(main_test())
    else:
        # If no WS URL, can run synchronously, but main_test is async due to monitor_status_websocket
        # For simplicity, we'll run it with asyncio anyway, REST parts will work.
        asyncio.run(main_test())
