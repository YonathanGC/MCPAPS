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
                    z=[node1["coordinates"][2] + disp1[2] * scale_factor, node2["coordinates"][2] + disp2[2] * scale_factor],
                    mode='lines',
                    line=dict(color='red', width=2, dash='dash'),
                    name='Deformed'
                ))

    return fig.to_json()
