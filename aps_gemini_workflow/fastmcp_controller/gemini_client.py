import os
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiClient:
    """
    A client for interacting with the Google Gemini API.

    This class handles the configuration and communication with the Gemini API
    to send prompts and receive generated content.
    """

    def __init__(self):
        """
        Initializes the GeminiClient.
        Loads the API key from environment variables and configures the Gemini client.
        """
        load_dotenv()  # Load environment variables from .env file
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

        genai.configure(api_key=self.api_key)
        # Initialize the GenerativeModel. You might need to specify a model name,
        # e.g., "gemini-pro" or "gemini-1.5-flash" etc.
        # For this example, we'll use a common default if available, or you can specify one.
        # Check the documentation for available models: https://ai.google.dev/models/gemini
        self.model = genai.GenerativeModel(model_name="gemini-pro") # Or use a newer/specific model
        print("GeminiClient initialized.")

    def send_instruction(self, prompt: str) -> str:
        """
        Sends a prompt (instruction) to the Gemini API and returns the response.

        Args:
            prompt: The text prompt to send to the Gemini API.

        Returns:
            The text response from the Gemini API.

        Raises:
            Exception: If there's an error during API communication or response generation.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty.")

        try:
            print(f"Sending prompt to Gemini: \"{prompt[:50]}...\"")
            # Generate content using the model
            response = self.model.generate_content(prompt)

            # Accessing the text part of the response
            # The exact way to access text might vary slightly based on API version or response structure.
            # Typically, it's response.text or iterating through response.parts
            if response.text:
                print("Received response from Gemini.")
                return response.text
            else:
                # Handle cases where response might not have direct .text or is blocked
                # For more complex scenarios, inspect response.parts and response.prompt_feedback
                print("Gemini response might be empty or blocked. Full response:", response)
                # Check for safety ratings or finish reasons
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    return f"Prompt was blocked. Reason: {response.prompt_feedback.block_reason_message}"
                return "No text content received from Gemini or content was filtered."

        except Exception as e:
            print(f"Error sending instruction to Gemini: {e}")
            # It's good practice to raise the exception or handle it more gracefully
            # depending on the application's needs.
            raise

# Example Usage (for testing this module directly)
if __name__ == "__main__":
    try:
        client = GeminiClient()
        # Example prompt
        test_prompt = "Explain the concept of a Large Language Model in simple terms."
        response_text = client.send_instruction(test_prompt)
        print("\n--- Gemini Response ---")
        print(response_text)
        print("-----------------------")

        # Example of a potentially problematic prompt (to test error handling or filters)
        # test_blocked_prompt = "this is an unsafe prompt"
        # response_blocked_text = client.send_instruction(test_blocked_prompt)
        # print("\n--- Gemini Blocked Response ---")
        # print(response_blocked_text)
        # print("-----------------------------")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
