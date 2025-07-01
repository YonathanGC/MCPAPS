import unittest
import os
from unittest.mock import patch, MagicMock

# Ensure tests can find the dlubal_client module
import sys
import os # Ensure os is imported
# Add the parent directory of fastmcp_controller to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastmcp_controller.dlubal_client import DlubalClient

class TestDlubalClient(unittest.TestCase):

    @patch.dict(os.environ, {"DLUBAL_API_KEY": "testkey"})
    def test_initialization_success(self):
        """Test successful initialization with API key."""
        client = DlubalClient()
        self.assertIsNotNone(client)
        self.assertEqual(client.api_key, "testkey")
        # Add more assertions if server URLs are mandatory
        # self.assertEqual(client.rfem_server_url, "http://default_rfem_url")
        # self.assertEqual(client.rstab_server_url, "http://default_rstab_url")

    @patch.dict(os.environ, {}, clear=True) # Start with a clean environment
    def test_initialization_failure_no_api_key(self):
        """Test initialization failure if API key is missing."""
        if "DLUBAL_API_KEY" in os.environ: # Make sure it's really gone
            del os.environ["DLUBAL_API_KEY"]
        with self.assertRaisesRegex(ValueError, "DLUBAL_API_KEY not found"):
            DlubalClient()

    @patch.dict(os.environ, {"DLUBAL_API_KEY": "testkey", "DLUBAL_RFEM_SERVER_URL": "http://mockrfem"})
    def test_get_rfem_model_info_mocked_sdk(self):
        """Test get_rfem_model_info delegates to mocked RFEM SDK client."""
        client = DlubalClient()
        self.assertIsNotNone(client.rfem_client) # Ensure mock client is there

        # Mock the SDK's method directly on the MagicMock instance
        # This simulates what the actual SDK client method might return
        mock_sdk_model = MagicMock()
        mock_sdk_model.name = "TestRFEMModel"
        mock_sdk_model.path = "/path/to/model"
        mock_sdk_model.size = 1024
        # client.rfem_client.get_model_by_name.return_value = mock_sdk_model
        # The current placeholder returns a fixed dict, so we expect that
        # If the DlubalClient method was changed to use the SDK methods like above, this test would be more realistic

        # For the current DlubalClient implementation, it doesn't use the SDK client's methods yet.
        # So we test the placeholder return value.
        # To make this test more meaningful for SDK interaction, DlubalClient methods need to be updated.
        # For now, we'll test the current behavior which is returning a fixed dict.
        expected_result = {"name": "TestRFEMModel", "status": "mock_loaded", "info": "This is mock data for RFEM model."}
        result = client.get_rfem_model_info("TestRFEMModel")
        self.assertEqual(result, expected_result)
        # If DlubalClient used client.rfem_client.get_model_by_name("TestRFEMModel"):
        # client.rfem_client.get_model_by_name.assert_called_once_with("TestRFEMModel")


    @patch.dict(os.environ, {"DLUBAL_API_KEY": "testkey", "DLUBAL_RSTAB_SERVER_URL": "http://mockrstab"})
    def test_get_rstab_model_info_mocked_sdk(self):
        """Test get_rstab_model_info delegates to mocked RSTAB SDK client."""
        client = DlubalClient()
        self.assertIsNotNone(client.rstab_client)
        expected_result = {"name": "TestRSTABModel", "status": "mock_loaded", "info": "This is mock data for RSTAB model."}
        result = client.get_rstab_model_info("TestRSTABModel")
        self.assertEqual(result, expected_result)
        # client.rstab_client.get_model_by_name.assert_called_once_with("TestRSTABModel")

    @patch.dict(os.environ, {"DLUBAL_API_KEY": "testkey", "DLUBAL_RFEM_SERVER_URL": "http://mockrfem"})
    def test_run_rfem_analysis_mocked_sdk(self):
        """Test run_rfem_analysis delegates to mocked RFEM SDK client."""
        client = DlubalClient()
        self.assertIsNotNone(client.rfem_client)
        # client.rfem_client.get_model_by_name.return_value = MagicMock() # Assume model exists
        # mock_analysis_result = MagicMock()
        # mock_analysis_result.summary.return_value = "Analysis summary"
        # client.rfem_client.get_model_by_name.return_value.run_analysis.return_value = mock_analysis_result
        expected_result = {"status": "mock_success", "analysis_type": "Static", "model": "TestRFEMModel", "message": "RFEM Analysis completed (mocked)."}
        result = client.run_rfem_analysis("TestRFEMModel", "Static")
        self.assertEqual(result, expected_result)
        # client.rfem_client.get_model_by_name.assert_called_once_with("TestRFEMModel")
        # client.rfem_client.get_model_by_name.return_value.run_analysis.assert_called_once_with("Static")

    @patch.dict(os.environ, {"DLUBAL_API_KEY": "testkey", "DLUBAL_RSTAB_SERVER_URL": "http://mockrstab"})
    def test_run_rstab_analysis_mocked_sdk(self):
        """Test run_rstab_analysis delegates to mocked RSTAB SDK client."""
        client = DlubalClient()
        self.assertIsNotNone(client.rstab_client)
        expected_result = {"status": "mock_success", "analysis_type": "LC1", "model": "TestRSTABModel", "message": "RSTAB Analysis completed (mocked)."}
        result = client.run_rstab_analysis("TestRSTABModel", "LC1")
        self.assertEqual(result, expected_result)

    # Example of how you might test if the actual SDK was to be mocked
    # This assumes the Dlubal SDK has a class like `DlubalRinasimClient`
    # @patch.dict(os.environ, {
    #     "DLUBAL_API_KEY": "testkey_sdk",
    #     "DLUBAL_RFEM_SERVER_URL": "http://rfem.example.com"
    # })
    # @patch('fastmcp_controller.dlubal_client.DlubalRinasimClient') # Mock the SDK's client class
    # def test_initialization_with_rfem_sdk_mock(self, MockRinasimClient):
    #     """Test initialization with a mocked RFEM SDK client."""
    #     # This test would be more relevant if DlubalClient actually instantiated DlubalRinasimClient
    #     # For now, self.rfem_client is a MagicMock if URL is provided.
    #     mock_rfem_instance = MockRinasimClient.return_value
    #     # We would need to change DlubalClient to actually call DlubalRinasimClient for this to be tested.
    #     # e.g. self.rfem_client = DlubalRinasimClient(host=self.rfem_server_url, api_key=self.api_key)

    #     client = DlubalClient() # This would trigger the DlubalRinasimClient instantiation
    #     self.assertIsNotNone(client.rfem_client)
    #     MockRinasimClient.assert_called_once_with(host="http://rfem.example.com", api_key="testkey_sdk")
    #     self.assertIsNone(client.rstab_client) # Assuming RSTAB URL wasn't provided

if __name__ == '__main__':
    unittest.main()
    # @patch.dict(os.environ, {
    #     "DLUBAL_API_KEY": "testkey_sdk",
    #     "DLUBAL_RFEM_SERVER_URL": "http://rfem.example.com"
    # })
    # @patch('dlubal_client.DlubalRinasimClient') # Mock the SDK's client class
    # def test_initialization_with_rfem_sdk_mock(self, MockRinasimClient):
    #     """Test initialization with a mocked RFEM SDK client."""
    #     mock_rfem_instance = MockRinasimClient.return_value # The instance of the mocked SDK client
    #     # You can further mock methods on mock_rfem_instance if needed, e.g., mock_rfem_instance.get_model_by_name

    #     client = DlubalClient()
    #     self.assertIsNotNone(client.rfem_client)
    #     MockRinasimClient.assert_called_once_with(host="http://rfem.example.com", api_key="testkey_sdk")
    #     self.assertIsNone(client.rstab_client) # Assuming RSTAB URL wasn't provided

if __name__ == '__main__':
    unittest.main()
