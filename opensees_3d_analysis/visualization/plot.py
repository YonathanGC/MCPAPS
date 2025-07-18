import plotly.graph_objects as go
from input.data import get_arch_truss_data
import openseespy.opensees as ops
import numpy as np

def plot_model(show_deformed=False, scale_factor=1.0):
    """
    Plots the 3D model of the structure using Plotly.
    """
    input_data = get_arch_truss_data()
    nodes = input_data["nodes"]
    elements = input_data["elements"]

    fig = go.Figure()

    # Original structure
    for element in elements:
        node1_id = element["nodes"][0]
        node2_id = element["nodes"][1]

        node1 = next((n for n in nodes if n["id"] == node1_id), None)
        node2 = next((n for n in nodes if n["id"] == node2_id), None)

        if node1 and node2:
            fig.add_trace(go.Scatter3d(
                x=[node1["coordinates"][0], node2["coordinates"][0]],
                y=[node1["coordinates"][1], node2["coordinates"][1]],
                z=[node1["coordinates"][2], node2["coordinates"][2]],
                mode='lines',
                line=dict(color='blue', width=2),
                name='Original'
            ))

    # Deformed shape
    if show_deformed:
        for element in elements:
            node1_id = element["nodes"][0]
            node2_id = element["nodes"][1]

            node1 = next((n for n in nodes if n["id"] == node1_id), None)
            node2 = next((n for n in nodes if n["id"] == node2_id), None)

            if node1 and node2:
                disp1 = ops.nodeDisp(node1_id)
                disp2 = ops.nodeDisp(node2_id)

                fig.add_trace(go.Scatter3d(
                    x=[node1["coordinates"][0] + disp1[0] * scale_factor, node2["coordinates"][0] + disp2[0] * scale_factor],
                    y=[node1["coordinates"][1] + disp1[1] * scale_factor, node2["coordinates"][1] + disp2[1] * scale_factor],
                    z=[node1["coordinates"][2] + disp1[2] * scale_factor, node2["coordinates"][2] * scale_factor],
                    mode='lines',
                    line=dict(color='red', width=2, dash='dash'),
                    name='Deformed'
                ))

    return fig.to_json()

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
    axial_forces = []
    shear_forces = []
    moment_forces = []
    x_coords = []

    for element_id in upper_chord_elements:
        forces = ops.eleForce(element_id)
        axial_forces.append(forces[0])
        shear_forces.append(forces[2])
        moment_forces.append(forces[4])

        element = next((e for e in elements if e["id"] == element_id), None)
        if element:
            node1_id = element["nodes"][0]
            node1 = next((n for n in nodes if n["id"] == node1_id), None)
            if node1:
                x_coords.append(node1["coordinates"][0])

    # Axial Force Diagram
    fig_axial = go.Figure()
    fig_axial.add_trace(go.Scatter(x=x_coords, y=axial_forces, mode='lines+markers', name='Axial Force'))
    fig_axial.update_layout(title='Axial Force Diagram', xaxis_title='X Coordinate (m)', yaxis_title='Axial Force (N)')

    # Shear Force Diagram
    fig_shear = go.Figure()
    fig_shear.add_trace(go.Scatter(x=x_coords, y=shear_forces, mode='lines+markers', name='Shear Force'))
    fig_shear.update_layout(title='Shear Force Diagram', xaxis_title='X Coordinate (m)', yaxis_title='Shear Force (N)')

    # Moment Diagram
    fig_moment = go.Figure()
    fig_moment.add_trace(go.Scatter(x=x_coords, y=moment_forces, mode='lines+markers', name='Moment'))
    fig_moment.update_layout(title='Moment Diagram', xaxis_title='X Coordinate (m)', yaxis_title='Moment (Nm)')

    return fig_axial.to_json(), fig_shear.to_json(), fig_moment.to_json()
