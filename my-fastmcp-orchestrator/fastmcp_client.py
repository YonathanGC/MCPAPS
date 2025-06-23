# fastmcp_client.py
# This module handles the connection and communication with the FastMCP server.

import os
import asyncio
import websockets
import json
import threading
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

# Load environment variables
load_dotenv()

# --- Module-level globals ---
# Configuration (can be overridden by connect parameters)
DEFAULT_FASTMCP_URL = os.getenv("FASTMCP_URL", "ws://localhost:8765")
DEFAULT_FASTMCP_TOKEN = os.getenv("FASTMCP_TOKEN")

# State
_websocket_connection = None
_message_callback = None
_connection_task = None # Holds the asyncio task for the connection loop
_event_loop_thread = None # Thread to run asyncio event loop if needed
_async_loop = None # The asyncio event loop instance
_is_connecting = False # Flag to prevent multiple concurrent connection attempts

# --- Helper to manage asyncio loop in a separate thread ---
def _start_async_loop():
    """Starts the asyncio event loop in a separate thread if not already running."""
    global _async_loop, _event_loop_thread
    if _event_loop_thread is None or not _event_loop_thread.is_alive():
        _async_loop = asyncio.new_event_loop()
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                # Clean up tasks before closing the loop
                pending = asyncio.all_tasks(loop=loop)
                for task in pending:
                    task.cancel()
                group = asyncio.gather(*pending, return_exceptions=True)
                loop.run_until_complete(group)
                loop.close()
            print("Asyncio event loop finished.")

        _event_loop_thread = threading.Thread(target=run_loop, args=(_async_loop,), daemon=True)
        _event_loop_thread.start()
        print("Asyncio event loop started in a new thread.")

def _stop_async_loop():
    """Stops the asyncio event loop if it's running in our dedicated thread."""
    global _async_loop, _event_loop_thread
    if _async_loop and _async_loop.is_running():
        print("Stopping asyncio event loop...")
        _async_loop.call_soon_threadsafe(_async_loop.stop)
        if _event_loop_thread and _event_loop_thread.is_alive():
            _event_loop_thread.join(timeout=5) # Wait for thread to finish
            if _event_loop_thread.is_alive():
                print("Warning: Event loop thread did not stop gracefully.")
        _async_loop = None
        _event_loop_thread = None
        print("Asyncio event loop stopped.")


# --- Core WebSocket Logic (async) ---
async def _websocket_listener(uri: str, token: str or None):
    """The core asyncio task that connects and listens to the WebSocket."""
    global _websocket_connection, _message_callback, _is_connecting
    _is_connecting = True
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}" # Common auth, adjust if needed

    try:
        async with websockets.connect(uri, extra_headers=headers, ping_interval=20, ping_timeout=20) as ws:
            _websocket_connection = ws
            _is_connecting = False
            print(f"Successfully connected to FastMCP: {uri}")

            if _message_callback:
                print("Listening for messages from FastMCP...")
                async for message_str in _websocket_connection:
                    try:
                        data = json.loads(message_str)
                        _message_callback(data)
                    except json.JSONDecodeError:
                        print(f"Warning: Received non-JSON message: {message_str}")
                        _message_callback(message_str)
                    except Exception as e:
                        print(f"Error processing message in callback: {e}")
            else:
                print("No message callback registered. Connection open but not actively processing messages.")
                while _websocket_connection and _websocket_connection.open:
                    await asyncio.sleep(0.1) # Keep alive, check state

    except websockets.exceptions.InvalidURI:
        print(f"Connection to FastMCP failed: Invalid URI '{uri}'")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"FastMCP connection closed: {e}")
    except ConnectionRefusedError:
        print(f"Connection to FastMCP refused at {uri}.")
    except asyncio.CancelledError:
        print("FastMCP connection task cancelled.")
    except Exception as e:
        print(f"Failed to connect or unexpected error in listener for FastMCP: {e}")
    finally:
        _is_connecting = False
        if _websocket_connection:
            if not _websocket_connection.closed:
                await _websocket_connection.close()
        _websocket_connection = None
        print("FastMCP WebSocket listener stopped.")


# --- Public API ---
def connect(url: str = None, port: int = None, token: str = None):
    """
    Establishes a connection to the FastMCP server using WebSockets.
    Configurable via URL, port, and token (arguments override .env defaults).
    Starts an asyncio event loop in a separate thread if needed.
    """
    global _connection_task, DEFAULT_FASTMCP_URL, DEFAULT_FASTMCP_TOKEN, _is_connecting

    if _is_connecting or (_connection_task and not _connection_task.done()):
        print("Connection attempt ignored: Already connecting or connected.")
        return

    current_url = url if url is not None else DEFAULT_FASTMCP_URL
    current_token = token if token is not None else DEFAULT_FASTMCP_TOKEN

    if port is not None:
        try:
            parsed_url = urlparse(current_url)
            # Replace port, keep other parts like scheme, path, query, fragment
            new_netloc = f"{parsed_url.hostname}:{port}"
            current_url = urlunparse(parsed_url._replace(netloc=new_netloc))
        except ValueError:
            print(f"Warning: Could not parse and override port for URL '{current_url}'. Using as is.")

    print(f"Attempting to connect to FastMCP at {current_url}...")
    if not current_token:
        print("Warning: FastMCP token is not set. Connection might fail if authentication is required.")

    _start_async_loop()

    if _async_loop:
        _is_connecting = True # Set flag before creating task
        _connection_task = asyncio.run_coroutine_threadsafe(
            _websocket_listener(current_url, current_token),
            _async_loop
        )
        print("FastMCP connection process initiated.")
    else:
        print("Error: Asyncio event loop not available. Cannot connect.")


def disconnect():
    """
    Closes the connection to the FastMCP server.
    """
    global _connection_task, _websocket_connection, _is_connecting

    print("Attempting to disconnect from FastMCP...")
    _is_connecting = False # Clear connecting flag

    if _connection_task :
        if not _connection_task.done():
            print("Cancelling active WebSocket listener task...")
            _connection_task.cancel()
            # Note: Actual closing of websocket and task cleanup happens in _websocket_listener's finally block.
        _connection_task = None

    # If connection task is already done or was never set, but websocket object exists (e.g. error state)
    elif _websocket_connection and _websocket_connection.open and _async_loop:
        print("Connection task not active, but WebSocket object exists. Attempting direct close.")
        asyncio.run_coroutine_threadsafe(_websocket_connection.close(), _async_loop)
        _websocket_connection = None

    # Consider stopping the loop if this client is the sole user.
    # _stop_async_loop() # Typically managed by the main application.

    print("FastMCP disconnection process initiated/completed.")


def send(message: dict):
    """
    Sends a message (dictionary, converted to JSON) to the FastMCP server.

    Args:
        message (dict): The message payload to send.
    Returns:
        bool: True if message was scheduled for sending, False otherwise.
    """
    global _websocket_connection
    if not _websocket_connection or not _websocket_connection.open:
        print("Cannot send message: Not connected to FastMCP or connection is closed.")
        return False

    if not _async_loop or not _async_loop.is_running():
        print("Cannot send message: Asyncio loop not running.")
        return False

    try:
        json_message = json.dumps(message)

        async def _do_send():
            if _websocket_connection and _websocket_connection.open:
                await _websocket_connection.send(json_message)
            else:
                print("Send aborted: WebSocket connection closed before send could execute.")

        asyncio.run_coroutine_threadsafe(_do_send(), _async_loop)
        return True
    except Exception as e:
        print(f"Error preparing or queueing message for FastMCP: {e}")
        return False

def on_message(callback):
    """
    Registers a callback function to be invoked when a message is received from FastMCP.

    Args:
        callback (function): A function that takes one argument (the message received).
    """
    global _message_callback
    if not callable(callback):
        print("Error: Provided callback is not callable.")
        _message_callback = None
        return

    print(f"Registering message callback: {callback.__name__ if hasattr(callback, '__name__') else 'unnamed_callback'}")
    _message_callback = callback


# --- Example Usage and Cleanup ---
if __name__ == "__main__":
    print("FastMCP Client Module - Example Usage")

    def my_message_handler(msg_data):
        print(f"--- Example Handler Received: {msg_data} (Type: {type(msg_data)}) ---")
        if isinstance(msg_data, dict) and msg_data.get("content") == "echo: Hello from client example":
             print("Received expected echo back!")


    on_message(my_message_handler)

    # Using a public echo server for testing
    # connect(url="wss://echo.websocket.org/") # Often unreliable
    connect(url="wss://socketsbay.com/wss/v2/1/demo/")


    print("Waiting for connection (5s)...")
    time_to_wait_for_connection = 5
    for i in range(time_to_wait_for_connection * 2): # Check every 0.5s
        if _websocket_connection and _websocket_connection.open:
            break
        threading.Event().wait(0.5)

    if _websocket_connection and _websocket_connection.open:
        print("\nConnection established. Sending a test message...")
        send({"type": "greeting", "content": "Hello from client example"})

        print("\nSent test message. Listening for responses for 10 seconds...")
        threading.Event().wait(10)
        print("\nFinished listening period.")
    else:
        print(f"\nCould not connect to the WebSocket server after {time_to_wait_for_connection}s.")

    print("\nDisconnecting from FastMCP...")
    disconnect()

    print("Stopping the asyncio event loop (if it was started by this client)...")
    _stop_async_loop()

    print("\nFastMCP client example finished.")
