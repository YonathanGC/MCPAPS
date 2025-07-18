import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from input.data import get_arch_truss_data

def plot_model():
    """
    Plots the 3D model of the structure.
    """
    input_data = get_arch_truss_data()
    nodes = input_data["nodes"]
    elements = input_data["elements"]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot nodes
    for node in nodes:
        ax.scatter(node["coordinates"][0], node["coordinates"][1], node["coordinates"][2], c='b', marker='o')

    # Plot elements
    for element in elements:
        node1_id = element["nodes"][0]
        node2_id = element["nodes"][1]

        node1 = next((n for n in nodes if n["id"] == node1_id), None)
        node2 = next((n for n in nodes if n["id"] == node2_id), None)

        if node1 and node2:
            ax.plot([node1["coordinates"][0], node2["coordinates"][0]],
                    [node1["coordinates"][1], node2["coordinates"][1]],
                    [node1["coordinates"][2], node2["coordinates"][2]], 'r')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    plt.savefig('model.png')
