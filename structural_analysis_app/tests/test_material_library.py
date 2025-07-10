import unittest
import os
import sys
import json

# Add src directory to Python path to import material_library
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from material_library import MaterialLibrary

class TestMaterialLibrary(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up for all tests. Create dummy data files for isolated testing."""
        cls.test_data_path = os.path.join(os.path.dirname(__file__), '..', 'data_test_temp')
        os.makedirs(cls.test_data_path, exist_ok=True)

        cls.test_materials_file = os.path.join(cls.test_data_path, 'materials_test.json')
        cls.test_profiles_file = os.path.join(cls.test_data_path, 'profiles_test.json')

        # Sample data for testing
        cls.sample_materials = [
            {"id": "TEST_CONC", "type": "concreto", "properties": {"fc_mpa": 20, "E_mpa": 20000}},
            {"id": "TEST_STEEL", "type": "acero", "properties": {"fy_mpa": 300, "E_mpa": 210000}}
        ]
        cls.sample_profiles = [
            {"id": "TEST_IPR", "type": "IPR", "properties": {"A_cm2": 50, "Ix_cm4": 5000}},
            {"id": "TEST_CE", "type": "CE", "properties": {"A_cm2": 20, "Ix_cm4": 700}}
        ]

        with open(cls.test_materials_file, 'w') as f:
            json.dump(cls.sample_materials, f)
        with open(cls.test_profiles_file, 'w') as f:
            json.dump(cls.sample_profiles, f)

        # Monkey patch the file paths in MaterialLibrary to use test files
        cls.original_materials_file = MaterialLibrary.MATERIALS_FILE
        cls.original_profiles_file = MaterialLibrary.PROFILES_FILE
        MaterialLibrary.MATERIALS_FILE = cls.test_materials_file
        MaterialLibrary.PROFILES_FILE = cls.test_profiles_file

        cls.library = MaterialLibrary()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests. Remove dummy data files."""
        os.remove(cls.test_materials_file)
        os.remove(cls.test_profiles_file)
        os.rmdir(cls.test_data_path)
        # Restore original file paths
        MaterialLibrary.MATERIALS_FILE = cls.original_materials_file
        MaterialLibrary.PROFILES_FILE = cls.original_profiles_file


    def test_load_materials(self):
        self.assertIsNotNone(self.library._materials)
        self.assertEqual(len(self.library._materials), 2)
        self.assertEqual(self.library._materials[0]['id'], "TEST_CONC")

    def test_load_profiles(self):
        self.assertIsNotNone(self.library._profiles)
        self.assertEqual(len(self.library._profiles), 2)
        self.assertEqual(self.library._profiles[0]['id'], "TEST_IPR")

    def test_get_material(self):
        material = self.library.get_material("TEST_STEEL")
        self.assertIsNotNone(material)
        self.assertEqual(material['properties']['fy_mpa'], 300)

        non_existent_material = self.library.get_material("FAKE_MAT")
        self.assertIsNone(non_existent_material)

    def test_get_profile(self):
        profile = self.library.get_profile("TEST_CE")
        self.assertIsNotNone(profile)
        self.assertEqual(profile['properties']['A_cm2'], 20)

        non_existent_profile = self.library.get_profile("FAKE_PROFILE")
        self.assertIsNone(non_existent_profile)

    def test_list_material_ids(self):
        ids = self.library.list_material_ids()
        self.assertIn("TEST_CONC", ids)
        self.assertIn("TEST_STEEL", ids)
        self.assertEqual(len(ids), 2)

    def test_list_profile_ids(self):
        ids = self.library.list_profile_ids()
        self.assertIn("TEST_IPR", ids)
        self.assertIn("TEST_CE", ids)
        self.assertEqual(len(ids), 2)

    def test_list_materials_by_type(self):
        concrete_materials = self.library.list_materials_by_type("concreto")
        self.assertEqual(len(concrete_materials), 1)
        self.assertEqual(concrete_materials[0]['id'], "TEST_CONC")

        steel_materials = self.library.list_materials_by_type("acero")
        self.assertEqual(len(steel_materials), 1)
        self.assertEqual(steel_materials[0]['id'], "TEST_STEEL")

        non_existent_type = self.library.list_materials_by_type("madera")
        self.assertEqual(len(non_existent_type), 0)

    def test_list_profiles_by_type(self):
        ipr_profiles = self.library.list_profiles_by_type("IPR")
        self.assertEqual(len(ipr_profiles), 1)
        self.assertEqual(ipr_profiles[0]['id'], "TEST_IPR")

        ce_profiles = self.library.list_profiles_by_type("CE")
        self.assertEqual(len(ce_profiles), 1)
        self.assertEqual(ce_profiles[0]['id'], "TEST_CE")

        non_existent_type = self.library.list_profiles_by_type("L")
        self.assertEqual(len(non_existent_type), 0)

    def test_file_not_found(self):
        # Temporarily point to non-existent files
        MaterialLibrary.MATERIALS_FILE = "non_existent_materials.json"
        MaterialLibrary.PROFILES_FILE = "non_existent_profiles.json"

        # Suppress print statements during this specific test for cleaner output
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

        temp_library = MaterialLibrary()

        sys.stdout.close() # Close the devnull stream
        sys.stdout = original_stdout # Restore stdout

        self.assertEqual(len(temp_library.list_material_ids()), 0)
        self.assertEqual(len(temp_library.list_profile_ids()), 0)

        # Restore original (test) file paths for other tests
        MaterialLibrary.MATERIALS_FILE = self.test_materials_file
        MaterialLibrary.PROFILES_FILE = self.test_profiles_file


if __name__ == '__main__':
    unittest.main()
