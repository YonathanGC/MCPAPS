import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from input.data import get_arch_truss_data
import openseespy.opensees as ops
import numpy as np

def plot_model(show_deformed=False, scale_factor=1.0):
    """
    Plots the 3D model of the structure.
    """
    input_data = get_arch_truss_data()
    nodes = input_data["nodes"]
    elements = input_data["elements"]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Get element forces for color-coding
    forces = []
    for element in elements:
        force = ops.eleForce(element["id"])
        forces.append(np.linalg.norm(force))

    norm = plt.Normalize(min(forces), max(forces))
    cmap = plt.get_cmap('jet')

    # Plot elements
    for i, element in enumerate(elements):
        node1_id = element["nodes"][0]
        node2_id = element["nodes"][1]

        node1 = next((n for n in nodes if n["id"] == node1_id), None)
        node2 = next((n for n in nodes if n["id"] == node2_id), None)

        if node1 and node2:
            ax.plot([node1["coordinates"][0], node2["coordinates"][0]],
                    [node1["coordinates"][1], node2["coordinates"][1]],
                    [node1["coordinates"][2], node2["coordinates"][2]],
                    color=cmap(norm(forces[i])))

    # Plot deformed shape
    if show_deformed:
        for element in elements:
            node1_id = element["nodes"][0]
            node2_id = element["nodes"][1]

            node1 = next((n for n in nodes if n["id"] == node1_id), None)
            node2 = next((n for n in nodes if n["id"] == node2_id), None)

            if node1 and node2:
                disp1 = ops.nodeDisp(node1_id)
                disp2 = ops.nodeDisp(node2_id)

                ax.plot([node1["coordinates"][0] + disp1[0] * scale_factor, node2["coordinates"][0] + disp2[0] * scale_factor],
                        [node1["coordinates"][1] + disp1[1] * scale_factor, node2["coordinates"][1] + disp2[1] * scale_factor],
                        [node1["coordinates"][2] + disp1[2] * scale_factor, node2["coordinates"][2] + disp2[2] * scale_factor], 'g--')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax)

    plt.savefig('model.png')

def plot_diagrams():
    """
    Plots the shear and moment diagrams for the upper chord of the first truss.
    """
    input_data = get_arch_truss_data()
    elements = input_data["elements"]
    nodes = input_data["nodes"]
    num_sections = 22

    # Get upper chord elements of the first truss
    upper_chord_elements = []
    for i in range(num_sections):
        element_id = 2 * i + 1
        upper_chord_elements.append(element_id)

    # Get forces
    shear_forces = []
    moment_forces = []
    x_coords = []

    for element_id in upper_chord_elements:
        forces = ops.eleForce(element_id)
        shear_forces.append(forces[2])
        moment_forces.append(forces[4])

        element = next((e for e in elements if e["id"] == element_id), None)
        if element:
            node1_id = element["nodes"][0]
            node1 = next((n for n in nodes if n["id"] == node1_id), None)
            if node1:
                x_coords.append(node1["coordinates"][0])

    # Plot shear diagram
    plt.figure()
    plt.plot(x_coords, shear_forces, 'b-')
    plt.xlabel('X coordinate (m)')
    plt.ylabel('Shear Force (N)')
    plt.title('Shear Force Diagram - Upper Chord')
    plt.grid(True)
    plt.savefig('shear_diagram.png')

    # Plot moment diagram
    plt.figure()
    plt.plot(x_coords, moment_forces, 'r-')
    plt.xlabel('X coordinate (m)')
    plt.ylabel('Moment (Nm)')
    plt.title('Moment Diagram - Upper Chord')
    plt.grid(True)
    plt.savefig('moment_diagram.png')
