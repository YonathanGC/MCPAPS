import os
import logging
from dotenv import load_dotenv
try:
    import anthropic
except ImportError:
    logging.error("Anthropic library not found. Please install it using 'pip install anthropic'")
    anthropic = None

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default Claude model - Sonnet is a good balance of performance and cost.
# Opus is more powerful but slower and more expensive. Haiku is fastest but less powerful.
DEFAULT_CLAUDE_MODEL = "claude-3-sonnet-20240229"
MAX_TOKENS_DEFAULT = 2048 # Default max tokens for the response

class ClaudeClient:
    """
    A client for interacting with the Anthropic Claude API.
    """

    def __init__(self, api_key: str = None, model_name: str = DEFAULT_CLAUDE_MODEL):
        """
        Initializes the ClaudeClient.
        Loads the API key from environment variables if not provided directly,
        and configures the Claude client.

        Args:
            api_key (str, optional): Anthropic API key. Defaults to None (loads from .env).
            model_name (str, optional): The Claude model to use.
                                       Defaults to DEFAULT_CLAUDE_MODEL.
        """
        load_dotenv()  # Load environment variables from .env file

        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("CLAUDE_API_KEY")

        if not self.api_key:
            logging.error("CLAUDE_API_KEY not found in environment variables or direct input. Please set it.")
            raise ValueError("CLAUDE_API_KEY not found.")

        if anthropic is None:
            raise ImportError("Anthropic library is not installed.")

        self.model_name = model_name
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logging.info(f"ClaudeClient initialized with model: {self.model_name}")
        except Exception as e:
            logging.error(f"Failed to initialize Anthropic client: {e}", exc_info=True)
            raise

    def send_instruction(self, prompt: str, system_prompt: str = None, max_tokens: int = MAX_TOKENS_DEFAULT) -> str:
        """
        Sends a prompt (instruction) to the Claude API and returns the text response.

        Args:
            prompt (str): The user's text prompt to send to the Claude API.
            system_prompt (str, optional): A system prompt to guide the model's behavior.
            max_tokens (int, optional): The maximum number of tokens to generate in the response.
                                       Defaults to MAX_TOKENS_DEFAULT.

        Returns:
            The text response from the Claude API.

        Raises:
            ValueError: If the prompt is empty.
            Exception: If there's an error during API communication or response generation.
        """
        if not prompt:
            logging.error("Prompt cannot be empty.")
            raise ValueError("Prompt cannot be empty.")

        messages = [{"role": "user", "content": prompt}]

        try:
            logging.info(f"Sending prompt to Claude ({self.model_name}): \"{prompt[:100]}...\"")

            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None, # System prompt is optional
                messages=messages
            )

            # The response object structure for claude.messages.create
            # has the content in response.content, which is a list of blocks.
            # We expect a single text block for this usage.
            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                text_response = ""
                for block in response.content:
                    if block.type == "text":
                        text_response += block.text

                if text_response:
                    logging.info("Received response from Claude.")
                    return text_response.strip()
                else:
                    logging.warning("Claude response content was empty or not text.")
                    return "No text content received from Claude or content was not text."
            else:
                logging.warning(f"Claude response structure not as expected or empty. Full response: {response}")
                return "No parsable content received from Claude."

        except anthropic.APIConnectionError as e:
            logging.error(f"Claude API connection error: {e}", exc_info=True)
            raise
        except anthropic.RateLimitError as e:
            logging.error(f"Claude API rate limit exceeded: {e}", exc_info=True)
            raise
        except anthropic.APIStatusError as e:
            logging.error(f"Claude API status error (status code {e.status_code}): {e.message}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Error sending instruction to Claude: {e}", exc_info=True)
            raise

# Example Usage (for testing this module directly)
if __name__ == "__main__":
    # Ensure CLAUDE_API_KEY is set in your .env file or pass it directly for testing
    if not os.getenv("CLAUDE_API_KEY"):
        print("CLAUDE_API_KEY not set in .env for testing. You can set it or modify this test.")
    else:
        try:
            client = ClaudeClient() # Uses default model

            # Test with a simple prompt
            test_prompt_simple = "Hello Claude, how are you today?"
            print(f"\n--- Sending Simple Prompt to Claude ({client.model_name}) ---")
            response_simple = client.send_instruction(test_prompt_simple)
            print(f"Claude's Response:\n{response_simple}")
            print("------------------------------------")

            # Test with a more complex prompt and a system prompt
            system_message = "You are a helpful assistant that provides concise answers."
            test_prompt_complex = "Explain the concept of a Large Language Model in one sentence."
            print(f"\n--- Sending Complex Prompt to Claude ({client.model_name}) with System Prompt ---")
            response_complex = client.send_instruction(test_prompt_complex, system_prompt=system_message)
            print(f"Claude's Response:\n{response_complex}")
            print("---------------------------------------------")

            # Example of a prompt that might require specific formatting if Claude is to generate JSON
            # This will be important for the main application.
            json_example_prompt = """
            Given the user wants to turn on a light, what would be the JSON command?
            The command should have an "action" field set to "set_device_state"
            and a "payload" field with "device_id" and "state". The light's ID is "light001".
            Provide only the JSON object.
            """
            print(f"\n--- Sending JSON Example Prompt to Claude ({client.model_name}) ---")
            response_json = client.send_instruction(json_example_prompt)
            print(f"Claude's Potentially JSON Response:\n{response_json}")
            print("-----------------------------------------------------")


        except ValueError as ve:
            print(f"Configuration Error: {ve}")
        except ImportError as ie:
            print(f"Import Error: {ie}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
