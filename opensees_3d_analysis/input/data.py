import numpy as np

def get_arch_truss_data():
    """
    Returns a dictionary containing the input data for the arch truss structure.
    """
    # Parameters
    L = 17.50  # m
    f = 1.50  # m
    S = 5.50  # m
    N = 6
    a = 4 * f / (L**2)
    num_sections = 22
    w_total = 1220 # N/m
    col_height = 4.0 # m
    footing_depth = 1.0 # m

    # Nodes
    nodes = []
    node_id = 1
    for i in range(N):
        for j in range(num_sections + 1):
            x = -L/2 + j * L / num_sections
            y = i * S
            z = f - a * x**2
            nodes.append({"id": node_id, "coordinates": [x, y, z + col_height], "mass": [100, 100, 100, 0, 0, 0]})
            node_id += 1
            # Add lower chord node
            nodes.append({"id": node_id, "coordinates": [x, y, z - 0.45 + col_height], "mass": [100, 100, 100, 0, 0, 0]})
            node_id += 1

    # Add column and footing nodes
    for i in range(N):
        for x_coord in [-L/2, L/2]:
            y_coord = i * S
            # Column top
            nodes.append({"id": node_id, "coordinates": [x_coord, y_coord, col_height], "mass": [100, 100, 100, 0, 0, 0]})
            node_id += 1
            # Column base
            nodes.append({"id": node_id, "coordinates": [x_coord, y_coord, 0.0], "mass": [100, 100, 100, 0, 0, 0]})
            node_id += 1
            # Footing base
            nodes.append({"id": node_id, "coordinates": [x_coord, y_coord, -footing_depth], "mass": [100, 100, 100, 0, 0, 0]})
            node_id += 1


    # Elements
    elements = []
    element_id = 1
    # Truss elements
    for i in range(N):
        for j in range(num_sections):
            # Upper chord
            node1_id = 2 * (i * (num_sections + 1) + j) + 1
            node2_id = 2 * (i * (num_sections + 1) + j + 1) + 1
            elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 1})
            element_id += 1
            # Lower chord
            node1_id = 2 * (i * (num_sections + 1) + j) + 2
            node2_id = 2 * (i * (num_sections + 1) + j + 1) + 2
            elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 1})
            element_id += 1

        for j in range(num_sections + 1):
            # Cajon (verticals)
            node1_id = 2 * (i * (num_sections + 1) + j) + 1
            node2_id = 2 * (i * (num_sections + 1) + j) + 2
            elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 1})
            element_id += 1

        for j in range(num_sections):
            # Diagonals
            node1_id = 2 * (i * (num_sections + 1) + j) + 1
            node2_id = 2 * (i * (num_sections + 1) + j + 1) + 2
            elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 1})
            element_id += 1

            node1_id = 2 * (i * (num_sections + 1) + j) + 2
            node2_id = 2 * (i * (num_sections + 1) + j + 1) + 1
            elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 1})
            element_id += 1

    # Column elements
    col_A = 0.3 * 0.3
    col_Iz = (0.3 * 0.3**3) / 12
    col_Iy = (0.3 * 0.3**3) / 12
    col_J = 0.4 * col_A**2 # Approximate

    start_node_id = 2 * N * (num_sections + 1) + 1
    for i in range(N * 2):
        node1_id = start_node_id + i * 3
        node2_id = start_node_id + i * 3 + 1
        elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [node1_id, node2_id], "material": 2})
        element_id += 1
        # Connect truss to column
        truss_node_id = 2 * (i//2 * (num_sections + 1)) + (0 if i%2 == 0 else num_sections) * 2 + 1
        elements.append({"id": element_id, "type": "ElasticBeamColumn", "nodes": [truss_node_id, node1_id], "material": 1})
        element_id += 1


    # Supports
    supports = []
    start_node_id = 2 * N * (num_sections + 1) + 2
    for i in range(N * 2):
        node_id = start_node_id + i * 3 + 1
        supports.append({"node": node_id, "dof": [1, 1, 1, 1, 1, 1]})

    # Loads
    loads = []
    for i in range(N):
        for j in range(num_sections + 1):
            node_id = 2 * (i * (num_sections + 1) + j) + 1
            load_value = w_total * (L / num_sections)
            if j == 0 or j == num_sections:
                load_value /= 2
            loads.append({"node": node_id, "type": "nodal", "values": [0, 0, -load_value, 0, 0, 0]})


    input_data = {
        "nodes": nodes,
        "materials": [
            {"id": 1, "type": "steel", "name": "A36", "A": 0.002258, "Iz": 6.77e-8, "Iy": 6.77e-8, "J": 1.354e-7},
            {"id": 2, "type": "column_material", "name": "concrete", "A": col_A, "Iz": col_Iz, "Iy": col_Iy, "J": col_J}
        ],
        "elements": elements,
        "loads": loads,
        "supports": supports
    }
    return input_data
