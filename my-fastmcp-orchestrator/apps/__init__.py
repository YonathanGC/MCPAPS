# apps/__init__.py

# This file makes the 'apps' directory a Python package.
# You can optionally import client modules here to make them available
# when 'from apps import ...' is used, but it's often cleaner to
# let the main application (main.py) import them directly as needed.

# Example:
# from . import revit_client
# from . import autocad_client
# ... and so on for other clients

# This allows for: from apps import revit_client

# Alternatively, if you want to control what is exported when 'from apps import *'
# is used (though 'import *' is generally discouraged):
# __all__ = [
#     "revit_client",
#     "autocad_client",
#     "civil3d_client",
#     "robot_client",
#     "dynamo_client",
#     "arcgis_client",
#     "qgis_client"
# ]

print("Initializing 'apps' package...")
