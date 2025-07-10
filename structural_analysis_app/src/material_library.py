import json
import os
import sys # Necesario para resource_path

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not running in a PyInstaller bundle, so use path relative to this script's parent
        # This script (material_library.py) is in 'src/'. Data is in 'data/' (sibling to 'src').
        # So, base_path should be the parent of 'src/', which is 'structural_analysis_app/'.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

# Usar resource_path para definir las rutas a los archivos de datos
# 'data/materials_mx.json' es la ruta relativa desde la raíz del proyecto (o _MEIPASS)
MATERIALS_FILE = resource_path(os.path.join('data', 'materials_mx.json'))
PROFILES_FILE = resource_path(os.path.join('data', 'profiles_ansi_mx.json'))

class MaterialLibrary:
    def __init__(self):
        # Print para depuración de rutas, especialmente útil al empaquetar
        # print(f"DEBUG: Attempting to load materials from: {MATERIALS_FILE}")
        # print(f"DEBUG: Attempting to load profiles from: {PROFILES_FILE}")
        self._materials = self._load_data(MATERIALS_FILE)
        self._profiles = self._load_data(PROFILES_FILE)

        if self._materials is None:
            self._materials = []
            print("Warning: Could not load materials file or file is empty.")
        if self._profiles is None:
            self._profiles = []
            print("Warning: Could not load profiles file or file is empty.")

        self._materials_dict = {mat['id']: mat for mat in self._materials}
        self._profiles_dict = {prof['id']: prof for prof in self._profiles}

    def _load_data(self, file_path):
        """Loads data from a JSON file."""
        if not os.path.exists(file_path):
            print(f"Error: Data file not found at {file_path}")
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while loading {file_path}: {e}")
            return None

    def get_material(self, material_id):
        """Retrieves a material by its ID."""
        return self._materials_dict.get(material_id)

    def get_profile(self, profile_id):
        """Retrieves a profile by its ID."""
        return self._profiles_dict.get(profile_id)

    def list_material_ids(self):
        """Returns a list of all material IDs."""
        return list(self._materials_dict.keys())

    def list_profile_ids(self):
        """Returns a list of all profile IDs."""
        return list(self._profiles_dict.keys())

    def list_materials_by_type(self, material_type):
        """Returns a list of materials of a specific type."""
        return [mat for mat in self._materials if mat.get('type') == material_type]

    def list_profiles_by_type(self, profile_type):
        """Returns a list of profiles of a specific type."""
        return [prof for prof in self._profiles if prof.get('type') == profile_type]

if __name__ == '__main__':
    # Example Usage
    library = MaterialLibrary()

    print("Available Material IDs:")
    for mat_id in library.list_material_ids():
        print(f"- {mat_id}")

    print("\nAvailable Profile IDs:")
    for prof_id in library.list_profile_ids():
        print(f"- {prof_id}")

    print("\nDetails for CONC_NTC_250:")
    conc_250 = library.get_material("CONC_NTC_250")
    if conc_250:
        print(json.dumps(conc_250, indent=2))
    else:
        print("Material CONC_NTC_250 not found.")

    print("\nDetails for IR254x32.8:")
    profile_ir = library.get_profile("IR254x32.8")
    if profile_ir:
        print(json.dumps(profile_ir, indent=2))
    else:
        print("Profile IR254x32.8 not found.")

    print("\nSteel Materials:")
    steel_materials = library.list_materials_by_type("acero")
    for mat in steel_materials:
        print(f"- {mat['id']}")

    print("\nIPR Profiles:")
    ipr_profiles = library.list_profiles_by_type("IPR")
    for prof in ipr_profiles:
        print(f"- {prof['id']}")
