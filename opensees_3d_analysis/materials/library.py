def get_material_library():
    """
    Returns a dictionary of common steel and concrete materials.
    """
    material_library = {
        "steel": {
            "A36": {
                "E": 200e9,
                "fy": 250e6,
                "fu": 400e6,
                "poisson": 0.3
            },
            "A572_Gr50": {
                "E": 200e9,
                "fy": 345e6,
                "fu": 450e6,
                "poisson": 0.3
            }
        },
        "concrete": {
            "C25": {
                "fpc": 25e6,
                "E": 22e9,
                "poisson": 0.2
            },
            "C30": {
                "fpc": 30e6,
                "E": 24e9,
                "poisson": 0.2
            }
        }
    }
    return material_library
