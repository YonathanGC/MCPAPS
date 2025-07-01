import unittest
import os
from unittest.mock import patch, MagicMock

# Ensure tests can find the app_controller and other modules
import sys
import os # Ensure os is imported
# Add the parent directory of fastmcp_controller to sys.path
# This allows 'from fastmcp_controller.app_controller import AppController'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastmcp_controller.app_controller import AppController
# DlubalClient is imported by AppController, so we might need to mock its methods if AppController calls them directly upon init or in tested methods.

# Mock environment variables for AppController tests
@patch('fastmcp_controller.gemini_client.load_dotenv', MagicMock()) # Patch gemini's load_dotenv
@patch('fastmcp_controller.main.load_dotenv', MagicMock()) # Patch main's load_dotenv
@patch('fastmcp_controller.dlubal_client.load_dotenv', MagicMock()) # Patch Dlubal's load_dotenv
@patch('fastmcp_controller.app_controller.load_dotenv', MagicMock()) # Patch AppController's load_dotenv
@patch.dict(os.environ, {
    "FASTMCP_SERVER_URL": "http://mockserver.com/api",
    "FASTMCP_AUTH_TOKEN": "mocktoken",
    "GEMINI_API_KEY": "mockgeminikey",
    "DLUBAL_API_KEY": "mockdlubalkey"
}, clear=True)
class TestAppController(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        # The class-level patches for load_dotenv are already active.
        # The os.environ is also set by the class-level patch.

        # Patch DlubalClient where AppController imports it.
        # AppController uses 'from .dlubal_client import DlubalClient', so the path is relative to app_controller
        self.dlubal_patcher = patch('fastmcp_controller.app_controller.DlubalClient')
        self.MockDlubalClientClass = self.dlubal_patcher.start()
        self.mock_dlubal_instance = self.MockDlubalClientClass.return_value

        self.controller = AppController()

    def tearDown(self):
        """Clean up after each test."""
        self.dlubal_patcher.stop()

    def test_app_controller_initialization(self): # mock_load_dotenv_app is injected by class decorator if not also mocked in the method
        """Test AppController initializes correctly."""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.server_url, "http://mockserver.com/api")
        self.assertIn("Authorization", self.controller.headers)
        self.assertEqual(self.controller.headers["Authorization"], "Bearer mocktoken")
        self.assertFalse(self.controller.is_websocket_url)
        self.MockDlubalClientClass.assert_called_once() # Check DlubalClient was instantiated
        self.assertIsNotNone(self.controller.dlubal_client)

    @patch('app_controller.requests.get')
    def test_get_connected_apps_rest(self, mock_requests_get):
        """Test getting connected apps via REST."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"apps": [{"id": "app1", "name": "Test App"}]}
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        apps = self.controller.get_connected_apps()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]['name'], "Test App")
        mock_requests_get.assert_called_once_with("http://mockserver.com/api/apps", headers=self.controller.headers)

    @patch('app_controller.requests.post')
    def test_send_command_rest(self, mock_requests_post):
        """Test sending a command via REST."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "message": "Command received"}
        mock_response.raise_for_status = MagicMock()
        mock_requests_post.return_value = mock_response

        response = self.controller.send_command("app1", "do_something", {"param": "value"})
        self.assertEqual(response["status"], "success")
        expected_payload = {
            "command": "do_something",
            "target_app_id": "app1",
            "payload": {"param": "value"}
        }
        mock_requests_post.assert_called_once_with(
            "http://mockserver.com/api/apps/app1/command",
            json=expected_payload,
            headers=self.controller.headers
        )

    # --- Test Dlubal Integration Methods in AppController ---

    def test_get_dlubal_rfem_model_info_delegation(self):
        """Test that AppController correctly delegates to DlubalClient for RFEM model info."""
        self.mock_dlubal_instance.get_rfem_model_info.return_value = {"name": "RFEM_Model_Test", "info": "Mocked RFEM data"}

        result = self.controller.get_dlubal_rfem_model_info("RFEM_Model_Test")

        self.mock_dlubal_instance.get_rfem_model_info.assert_called_once_with("RFEM_Model_Test")
        self.assertEqual(result, {"name": "RFEM_Model_Test", "info": "Mocked RFEM data"})

    def test_get_dlubal_rstab_model_info_delegation(self):
        """Test that AppController correctly delegates to DlubalClient for RSTAB model info."""
        self.mock_dlubal_instance.get_rstab_model_info.return_value = {"name": "RSTAB_Model_Test", "info": "Mocked RSTAB data"}

        result = self.controller.get_dlubal_rstab_model_info("RSTAB_Model_Test")

        self.mock_dlubal_instance.get_rstab_model_info.assert_called_once_with("RSTAB_Model_Test")
        self.assertEqual(result, {"name": "RSTAB_Model_Test", "info": "Mocked RSTAB data"})

    def test_run_dlubal_rfem_analysis_delegation(self):
        """Test that AppController correctly delegates to DlubalClient for RFEM analysis."""
        self.mock_dlubal_instance.run_rfem_analysis.return_value = {"status": "success", "analysis": "Static RFEM complete"}

        result = self.controller.run_dlubal_rfem_analysis("RFEM_Model_Test", "Static")

        self.mock_dlubal_instance.run_rfem_analysis.assert_called_once_with("RFEM_Model_Test", "Static")
        self.assertEqual(result, {"status": "success", "analysis": "Static RFEM complete"})

    def test_run_dlubal_rstab_analysis_delegation(self):
        """Test that AppController correctly delegates to DlubalClient for RSTAB analysis."""
        self.mock_dlubal_instance.run_rstab_analysis.return_value = {"status": "success", "analysis": "LC1 RSTAB complete"}

        result = self.controller.run_dlubal_rstab_analysis("RSTAB_Model_Test", "LC1")

        self.mock_dlubal_instance.run_rstab_analysis.assert_called_once_with("RSTAB_Model_Test", "LC1")
        self.assertEqual(result, {"status": "success", "analysis": "LC1 RSTAB complete"})

    def test_dlubal_client_not_initialized_gracefully(self):
        """Test AppController handles DlubalClient initialization failure."""
        self.patcher.stop() # Stop the existing patcher

        # Patch DlubalClient to raise an error during instantiation
        with patch('app_controller.DlubalClient', side_effect=ValueError("Dlubal init failed")):
            controller_with_failed_dlubal = AppController()
            self.assertIsNone(controller_with_failed_dlubal.dlubal_client)

            # Verify methods return an error
            result = controller_with_failed_dlubal.get_dlubal_rfem_model_info("any_model")
            self.assertIn("error", result)
            self.assertEqual(result["error"], "DlubalClient not initialized.")

        self.patcher.start() # Restart the patcher for other tests if any follow in a more complex setup


if __name__ == '__main__':
    unittest.main()
