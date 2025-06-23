# FastMCP Controller with Gemini Integration

## 🚀 Project Overview

This script provides a base for connecting to a FastMCP server and leveraging the Google Gemini API to automate actions on connected applications. It allows sending commands, reading real-time status, and managing application modules.

The project is structured to be compatible with GitHub Copilot and code suggestion tools like Roo Code.

## ✅ Requirements

- Python 3.7+
- pip (Python package installer)
- A Google Gemini API Key
- Access to a FastMCP server (with its URL and any necessary authentication tokens)

## 🔑 How to Generate Your Gemini API Key

1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey) (or the relevant Google Cloud Console page for Gemini API).
2.  Sign in with your Google account.
3.  Create a new API key.
4.  **Important**: Copy this key and keep it secure. You will need it for the `.env` file.

## 🛠️ Setup Instructions

1.  **Clone the repository (if applicable) or download the files:**
    ```bash
    # If it's a git repository
    git clone <repository-url>
    cd <repository-directory>

    # If you downloaded files, navigate to the main project directory (e.g., fastmcp_controller)
    cd fastmcp_controller
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    Activate it:
    -   Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    -   macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment file:**
    -   Rename `.env.example` to `.env`.
        ```bash
        # In the fastmcp_controller directory
        cp .env.example .env
        ```
    -   Open the `.env` file and fill in your details:
        ```env
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
        FASTMCP_SERVER_URL="YOUR_FASTMCP_SERVER_URL_HERE" # e.g., ws://localhost:8080 or http://localhost:8080/api
        FASTMCP_AUTH_TOKEN="YOUR_FASTMCP_AUTH_TOKEN_HERE" # Optional, if your server requires it
        ```

## ▶️ How to Run the Script

1.  Ensure your virtual environment is activated and your `.env` file is correctly configured.
2.  Navigate to the `fastmcp_controller` directory if you are not already there.
3.  Run the main script:
    ```bash
    python main.py
    ```
4.  Follow the on-screen prompts or interact with the application as designed.

## ⚙️ Project Structure

-   `main.py`: Main script to initialize connections and orchestrate operations.
-   `gemini_client.py`: Module for interacting with the Google Gemini API.
-   `app_controller.py`: Module for managing and interacting with applications via FastMCP.
-   `requirements.txt`: Lists Python dependencies.
-   `.env.example`: Template for environment variables.
-   `README.md`: This file.

## 💡 Compatibility

This project is designed with GitHub Copilot and Roo Code compatibility in mind, featuring:
- Clear, commented code.
- Modular structure.
- Type hinting (to be added progressively).

---

*This is a base script. You will need to implement the specific API calls and logic for your FastMCP server.*
