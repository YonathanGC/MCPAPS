import openseespy.opensees as ops
from input.data import get_arch_truss_data

def extract_nodal_results():
    """
    Extracts and prints the nodal results from the OpenSees analysis.
    """
    input_data = get_arch_truss_data()

    print("Displacements:")
    for node in input_data["nodes"]:
        node_id = node["id"]
        displacement = ops.nodeDisp(node_id)
        print(f"Node {node_id}: {displacement}")

def extract_element_results():
    """
    Extracts and prints the element results from the OpenSees analysis.
    """
    input_data = get_arch_truss_data()

    print("\nElement Forces:")
    for element in input_data["elements"]:
        element_id = element["id"]
        forces = ops.eleForce(element_id)
        print(f"Element {element_id}: {forces}")

def calculate_drifts():
    """
    Calculates and prints the drifts.
    """
    input_data = get_arch_truss_data()
    nodes = input_data["nodes"]

    # Get floor levels
    y_coords = sorted(list(set([node["coordinates"][2] for node in nodes])))

    print("\nDrifts:")
    for i in range(len(y_coords) - 1):
        level_1 = y_coords[i]
        level_2 = y_coords[i+1]

        nodes_level_1 = [n for n in nodes if n["coordinates"][2] == level_1]
        nodes_level_2 = [n for n in nodes if n["coordinates"][2] == level_2]

        if nodes_level_1 and nodes_level_2:
            # For simplicity, we calculate the average displacement at each level
            disp_x_1 = sum([ops.nodeDisp(n["id"])[0] for n in nodes_level_1]) / len(nodes_level_1)
            disp_x_2 = sum([ops.nodeDisp(n["id"])[0] for n in nodes_level_2]) / len(nodes_level_2)

            drift = (disp_x_2 - disp_x_1) / (level_2 - level_1)
            print(f"Drift between level {level_1} and {level_2}: {drift}")
