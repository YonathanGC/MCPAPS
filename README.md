# Dlubal API Controller with Claude Integration

## 🚀 Project Overview

This script provides a controller for Dlubal RFEM/RSTAB applications using the Dlubal gRPC API. It leverages the Anthropic Claude API to translate natural language instructions into Dlubal API commands, enabling automation of structural modeling and analysis tasks.

The project is structured to be compatible with GitHub Copilot and code suggestion tools like Roo Code.

## ✅ Requirements

- Python 3.7+
- pip (Python package installer)
- An Anthropic Claude API Key.
- Dlubal RFEM 6 or RSTAB 9 (or newer) installed and running.
- The Dlubal Web Service (gRPC server) must be enabled in RFEM/RSTAB (typically in Program Options -> Web Services, running on port 8081).
- The Dlubal Python API client library (`dlubal.api`) installed (see `requirements.txt`).

## 🔑 How to Generate Your Anthropic Claude API Key

1.  Go to the [Anthropic Console](https://console.anthropic.com/).
2.  Sign in or create an account.
3.  Navigate to the API Keys section.
4.  Create a new API key.
5.  **Important**: Copy this key and keep it secure. You will need it for the `.env` file.

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
        CLAUDE_API_KEY="YOUR_CLAUDE_API_KEY_HERE"
        # DLUBAL_SERVER_ADDRESS="localhost:8081" # Optional: Override default Dlubal gRPC server address
        ```
    Ensure your Dlubal RFEM/RSTAB application is running and the Web Service (gRPC) is enabled (usually on port 8081).

## ▶️ How to Run the Script

1.  Ensure your virtual environment is activated, your `.env` file is correctly configured with `CLAUDE_API_KEY`, and Dlubal RFEM/RSTAB is running with Web Services enabled.
2.  Navigate to the `fastmcp_controller` directory if you are not already there.
3.  Run the main script:
    ```bash
    python main.py
    ```
4.  Follow the on-screen prompts to interact with your Dlubal application using natural language.

## ⚙️ Project Structure

-   `main.py`: Main script to initialize connections and orchestrate Dlubal operations via Claude.
-   `claude_client.py`: Module for interacting with the Anthropic Claude API.
-   `dlubal_controller.py`: Module for managing and interacting with Dlubal RFEM/RSTAB via its gRPC API.
-   `requirements.txt`: Lists Python dependencies.
-   `.env.example`: Template for environment variables.
-   `README.md`: This file.

## 💡 Compatibility

This project is designed with GitHub Copilot and Roo Code compatibility in mind, featuring:
- Clear, commented code.
- Modular structure.
- Type hinting (progressively added).

---

*This script provides a foundation. The `DlubalController` methods currently contain placeholder logic for actual Dlubal gRPC API calls. These need to be filled in based on the `dlubal.api` library documentation to achieve full functionality.*
