# APS Gemini Workflow Orchestrator

This project provides a skeleton framework for orchestrating a workflow involving Autodesk Platform Services (APS) for Revit automation, local Dynamo script execution, and interaction with a Model Context Protocol (MCP) server, potentially driven by Google Gemini.

The components are primarily conceptual skeletons and simulations, designed to map out the structure described by the user. Actual interaction with cloud services (APS) and local applications (Revit, Dynamo via a real Revit MCP Plugin) would require further implementation and real credentials/software.

## 🚀 Project Overview

The goal is to create an automated workflow that can:
1.  Process Revit models in the cloud using APS Design Automation.
2.  Execute Dynamo graphs locally using `DynamoCLI.exe`.
3.  Enable interaction with design applications (like Revit) through an MCP server, which can be connected to Gemini for AI-driven commands.

## ✅ Prerequisites

1.  **Python:** Version 3.8+ recommended.
2.  **Autodesk Platform Services (APS) Account:**
    *   You'll need an APS account with a Client ID and Client Secret for Design Automation.
    *   Familiarity with creating AppBundles and Activities for Revit Design Automation.
3.  **Dynamo:**
    *   A local installation of Dynamo that includes `DynamoCLI.exe`.
    *   The path to `DynamoCLI.exe` needs to be correctly configured in `workflow_orchestrator.py` or provided as a command-line argument.
4.  **Google Gemini API Key:**
    *   If you intend to use the `fastmcp_controller`'s `GeminiClient` or integrate Gemini further, you'll need an API key.
5.  **(Optional) Revit MCP Package:** The `rsa_gemini_mcp_server.py` is designed to conceptually integrate with a Revit MCP package that would allow controlling Revit via MCP. This package is not included.
6.  **(Optional) `gemini-mcp-client`:** The user's workflow description mentioned this package. The `workflow_orchestrator.py` currently uses a simple built-in client; if you have `gemini-mcp-client`, you can integrate it.

## 🛠️ Setup Instructions

1.  **Clone/Download:**
    *   If this project is in a Git repository, clone it. Otherwise, ensure all files are in the `aps_gemini_workflow` directory.

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    cd aps_gemini_workflow
    python -m venv venv
    ```
    Activate it:
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure APS Credentials:**
    *   Open `auth_config.py`.
    *   Replace `"YOUR_APS_CLIENT_ID_HERE"` and `"YOUR_APS_CLIENT_SECRET_HERE"` with your actual APS credentials.

5.  **Configure Paths:**
    *   Review `workflow_orchestrator.py` and update placeholder paths:
        *   `DYNAMO_CLI_PATH`: Set to your local `DynamoCLI.exe` path.
        *   `DEFAULT_DYNAMO_SCRIPT`: Update to the path of a Dynamo script you want to test with.
        *   Paths for `DEFAULT_ACTIVITY_JSON`, `DEFAULT_INPUT_RVT`, `DEFAULT_OUTPUT_RVT` are used for simulation; ensure any dummy files exist if you want the simulation to find them, or provide paths via CLI.

6.  **(For `fastmcp_controller` usage) Configure Gemini and MCP Server URL:**
    *   If you plan to use the `fastmcp_controller` (see its [README](./fastmcp_controller/README.md)), copy `fastmcp_controller/.env.example` to `fastmcp_controller/.env`.
    *   Edit `fastmcp_controller/.env` to add your `GEMINI_API_KEY` and the URL of the MCP server it should connect to (this could be the `rsa_gemini_mcp_server.py` or another).

## 📁 Project Structure

```
aps_gemini_workflow/
├── auth_config.py                # APS credentials (needs user input)
├── autodesk_api_client.py        # Skeleton APS Design Automation client
├── rsa_gemini_mcp_server.py      # Conceptual MCP server (FastAPI based)
├── workflow_orchestrator.py      # Main script to run the entire workflow
├── requirements.txt              # Python dependencies for the whole project
├── README.md                     # This file
│
└── fastmcp_controller/           # Sub-module: Client for an MCP server & Gemini (see its own README)
    ├── app_controller.py
    ├── gemini_client.py
    ├── main.py                   # Interactive CLI for this controller
    ├── requirements.txt          # Dependencies for this sub-module
    ├── .env.example
    └── README.md
```

## ▶️ How to Run Components

*Ensure your virtual environment is activated and configurations are set before running.*

1.  **Test APS Authentication (Simulated):**
    *   Navigates to the `aps_gemini_workflow` directory.
    *   This tests if `autodesk_api_client.py` can load credentials from `auth_config.py` and simulates an OAuth token request.
    ```bash
    python autodesk_api_client.py --test-auth
    ```

2.  **Simulate APS Design Automation WorkItem:**
    *   This simulates creating and monitoring an APS Design Automation WorkItem.
    *   It will create a dummy `activity.json` and `input.rvt` if default names are used and files don't exist, for simulation purposes.
    ```bash
    python autodesk_api_client.py --create-item
    # Or with custom files:
    # python autodesk_api_client.py --create-item --activity-json my_activity.json --input-rvt my_model.rvt
    ```

3.  **Start the Conceptual MCP Server:**
    *   This starts the FastAPI-based `rsa_gemini_mcp_server.py`.
    *   By default, it runs on `http://localhost:8000`.
    *   You can access its OpenAPI docs at `http://localhost:8000/docs`.
    *   **Note:** This server has been updated with more detailed (though still simulated) tool definitions and handlers for Revit, Robot Structural Analysis, and Civil 3D.
    ```bash
    python rsa_gemini_mcp_server.py --start-mcp-server
    # To run on a different port:
    # python rsa_gemini_mcp_server.py --start-mcp-server --port 8001
    ```

4.  **Run the Main Workflow Orchestrator:**
    *   This script attempts to run the full workflow: APS DA, Dynamo, and MCP interaction.
    *   Ensure the MCP server (`rsa_gemini_mcp_server.py`) is running in a separate terminal if you want the MCP interaction step to succeed.
    *   It uses many placeholder paths; provide valid paths via CLI arguments for actual testing.
    ```bash
    # Example with default (mostly placeholder) paths:
    python workflow_orchestrator.py

    # Example with specified paths (replace with your actual paths):
    # python workflow_orchestrator.py \
    #   --activity-json "path/to/your/activity.json" \
    #   --input-rvt "path/to/your/input.rvt" \
    #   --output-rvt "path/to/your/result.rvt" \
    #   --dynamo-cli "C:/Program Files/Dynamo/Dynamo Core/2.x/DynamoCLI.exe" \
    #   --dynamo-script "path/to/your/script.dyn" \
    #   --mcp-url "http://localhost:8000"
    ```
    *   The script will output warnings for missing default files but will attempt to proceed with simulations where possible. The Dynamo step requires valid paths to `DynamoCLI.exe` and your `.dyn` file to execute.

5.  **Using `fastmcp_controller`:**
    *   The `fastmcp_controller` is a separate interactive CLI tool to connect to an MCP server (like the one started by `rsa_gemini_mcp_server.py` or any other) and use Gemini to formulate commands.
    *   See its [README.md](./fastmcp_controller/README.md) for setup and usage.

## 📝 Notes and Limitations

*   **Simulations:** Most operations, especially those involving APS and Revit interaction, are simulated. The code provides a structural outline rather than fully functional integrations.
*   **Error Handling:** Basic error handling is included, but robust production-level error management would be needed.
*   **Security:** Paths and commands (like for `subprocess`) should be carefully handled in a production environment to avoid security vulnerabilities. The current scripts assume trusted inputs for paths.
*   **Configuration:** Hardcoded paths and configurations should be moved to dedicated configuration files or environment variables for better management in a real application.

This framework provides a starting point. To make it fully operational, you would need to:
*   Implement the actual APS API calls in `autodesk_api_client.py`.
*   Develop or integrate a real Revit MCP package into `rsa_gemini_mcp_server.py` to control Revit.
*   Flesh out Dynamo script interactions.
*   Potentially replace the placeholder `MCPClient` in `workflow_orchestrator.py` with a more feature-rich client like `gemini-mcp-client` if it fits your needs.
---

This README provides a guide to the conceptual framework. Further development is needed to connect these pieces to live services and applications.
