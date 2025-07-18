import openseespy.opensees as ops
from input.data import get_arch_truss_data
from materials.library import get_material_library

def generate_model():
    """
    Generates the OpenSees model from the input data.
    """
    input_data = get_arch_truss_data()
    material_library = get_material_library()

    # Create the model
    ops.model('basic', '-ndm', 3, '-ndf', 6)

    # Add nodes
    for node in input_data["nodes"]:
        ops.node(node["id"], *node["coordinates"])
        if "mass" in node:
            ops.mass(node["id"], *node["mass"])

    # Add materials
    for material in input_data["materials"]:
        if material["type"] == "steel":
            mat_data = material_library["steel"][material["name"]]
            ops.uniaxialMaterial("Elastic", material["id"], mat_data["E"])
        elif material["type"] == "concrete":
            mat_data = material_library["concrete"][material["name"]]
            ops.uniaxialMaterial("Elastic", material["id"], mat_data["E"])
        elif material["type"] == "column_material":
            mat_data = material_library["column_material"][material["name"]]
            ops.uniaxialMaterial("Elastic", material["id"], mat_data["E"])


    # Add geometric transformation
    ops.geomTransf('Linear', 1, 0, 1, 0)

    # Add elements
    for element in input_data["elements"]:
        if element["type"] == "ElasticBeamColumn":
            mat_id = element["material"]
            material_input = next((mat for mat in input_data["materials"] if mat["id"] == mat_id), None)
            if material_input:
                if material_input["type"] == "steel":
                    mat_data = material_library["steel"][material_input["name"]]
                    G = mat_data["E"] / (2 * (1 + mat_data["poisson"]))
                    ops.element("elasticBeamColumn", element["id"], *element["nodes"],
                                material_input["A"], mat_data["E"], G, material_input["J"],
                                material_input["Iy"], material_input["Iz"], 1)
                elif material_input["type"] == "concrete" or material_input["type"] == "column_material":
                    if material_input["type"] == "concrete":
                        mat_data = material_library["concrete"][material_input["name"]]
                    else:
                        mat_data = material_library["column_material"][material_input["name"]]
                    G = mat_data["E"] / (2 * (1 + mat_data["poisson"]))
                    ops.element("elasticBeamColumn", element["id"], *element["nodes"],
                                material_input["A"], mat_data["E"], G, material_input["J"],
                                material_input["Iy"], material_input["Iz"], 1)

    # Add supports
    for support in input_data["supports"]:
        ops.fix(support["node"], *support["dof"])

    # Add loads
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for load in input_data["loads"]:
        if load["type"] == "nodal":
            ops.load(load["node"], *load["values"])

    print("OpenSees model generated successfully.")
