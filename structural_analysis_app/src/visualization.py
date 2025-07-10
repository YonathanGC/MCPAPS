import pyvista as pv
import numpy as np

def plot_structure_pyvista(vis_data, show_deformed=True, deformation_scale=50.0,
                           show_plotter_window=True, screenshot_filename=None):
    """
    Genera una visualización 3D de la estructura usando PyVista.

    Args:
        vis_data (dict): Diccionario con 'nodes', 'elements', y 'displacements'.
            nodes (dict): {tag: [x, y, z], ...}
            elements (list): [(n_tag1, n_tag2), ...]
            displacements (dict): {tag: [dx, dy, dz], ...}
        show_deformed (bool): Si es True, muestra también la estructura deformada.
        deformation_scale (float): Factor de escala para la visualización de la deformada.
        show_plotter_window (bool): Si es True, muestra la ventana interactiva de PyVista.
        screenshot_filename (str, optional): Si se proporciona, guarda una captura de pantalla
                                             en esta ruta y no muestra la ventana.
    """
    if not vis_data:
        print("Error: No hay datos de visualización para graficar.")
        return

    nodes_orig_dict = vis_data.get("nodes", {})
    elements_conn = vis_data.get("elements", [])
    displacements_dict = vis_data.get("displacements", {})

    if not nodes_orig_dict or not elements_conn:
        print("Error: Faltan datos de nodos o elementos para la visualización.")
        return

    node_tags_ordered = sorted(nodes_orig_dict.keys())
    if not node_tags_ordered:
        print("Error: No hay nodos en los datos de visualización.")
        return

    points_orig = np.array([nodes_orig_dict[tag] for tag in node_tags_ordered])

    node_tag_to_idx = {tag: i for i, tag in enumerate(node_tags_ordered)}

    lines = []
    for elem_nodes_tags in elements_conn:
        if len(elem_nodes_tags) >= 2: # Considerar elementos de línea (2 nodos) o más
            try:
                # Para elementos con más de 2 nodos (ej. quads), PyVista los maneja si se dan en orden.
                # Aquí nos enfocamos en líneas simples entre nodos consecutivos del elemento.
                # Para una viga simple, cada elemento tiene 2 nodos.
                # Si fuera un elemento más complejo (ej. shell con 4 nodos),
                # la forma de crear 'lines' podría necesitar ser más específica
                # o usar directamente tipos de celda de PyVista.
                # Por ahora, asumimos que son segmentos de línea.
                idx1 = node_tag_to_idx[elem_nodes_tags[0]]
                idx2 = node_tag_to_idx[elem_nodes_tags[1]]
                lines.extend([2, idx1, idx2])
            except KeyError:
                print(f"Advertencia: Tag de nodo en elemento {elem_nodes_tags} no encontrado.")
                continue
        else:
            print(f"Advertencia: Elemento con {len(elem_nodes_tags)} nodos no soportado para visualización simple.")

    if not lines:
        print("Error: No se pudieron crear líneas para la visualización (verificar conectividad de elementos).")
        return

    lines_np = np.array(lines)

    grid_orig = pv.PolyData(points_orig, lines=lines_np)
    # Placeholder para consistencia de la barra de escalar si solo se muestra la original
    grid_orig['DisplacementMagnitude'] = np.zeros(len(points_orig))

    plotter = pv.Plotter(off_screen=bool(screenshot_filename), window_size=[800,600])
    plotter.add_mesh(grid_orig, style='wireframe', color='blue', line_width=3, label='Original')

    max_disp_magnitude = 0.0
    actual_displacements_magnitudes = []

    if show_deformed and displacements_dict:
        points_deformed_list = []

        for tag in node_tags_ordered:
            orig_coord = np.array(nodes_orig_dict[tag])
            # Desplazamientos vienen como [dx, dy, dz=0 para 2D]
            disp_vector = np.array(displacements_dict.get(tag, [0.0, 0.0, 0.0]))
            points_deformed_list.append(orig_coord + disp_vector * deformation_scale)
            actual_displacements_magnitudes.append(np.linalg.norm(disp_vector))

        if points_deformed_list:
            points_deformed = np.array(points_deformed_list)
            max_disp_magnitude = np.max(actual_displacements_magnitudes) if actual_displacements_magnitudes else 0.0

            grid_deformed = pv.PolyData(points_deformed, lines=lines_np)
            grid_deformed['DisplacementMagnitude'] = np.array(actual_displacements_magnitudes)

            plotter.add_mesh(grid_deformed, style='wireframe', color='red', line_width=3,
                             label=f'Deformada (x{deformation_scale:.0f})',
                             scalars='DisplacementMagnitude', cmap='viridis',
                             scalar_bar_args={'title': 'Magnitud Despl. (mm)'})
        else:
            print("Advertencia: No se pudieron calcular puntos deformados.")

    plotter.add_text(f"Max. Despl. Real: {max_disp_magnitude:.4f} mm (Deformada escalada x{deformation_scale:.0f})",
                     position='lower_left', font_size=10, color='black')
    plotter.add_legend(bcolor=None, border=True) # bcolor=None para fondo transparente
    plotter.view_xy()
    plotter.enable_zoom_scaling()
    # plotter.show_grid() # Puede ser muy denso, opcional

    if screenshot_filename:
        plotter.screenshot(screenshot_filename, return_img=False)
        print(f"Visualización guardada en: {screenshot_filename}")

    if show_plotter_window and not screenshot_filename:
        plotter.show()

    plotter.close()


if __name__ == '__main__':
    # Ejemplo de uso (requiere datos de ejemplo)
    sample_vis_data_beam = {
        "nodes": {
            1: [0.0, 0.0, 0.0],       # Nodo 1 en el origen
            2: [2500.0, 0.0, 0.0],  # Nodo 2 en el centro de la viga
            3: [5000.0, 0.0, 0.0]   # Nodo 3 al final de la viga
        },
        "elements": [
            (1, 2), (2, 3) # Elemento 1 conecta nodo 1 y 2, Elemento 2 conecta nodo 2 y 3
        ],
        "displacements": {
            1: [0.0, 0.0, 0.0],       # Sin desplazamiento en el apoyo izquierdo
            2: [0.0, -2.673, 0.0], # Desplazamiento dy en el centro (ejemplo)
            3: [0.0, 0.0, 0.0]        # Sin desplazamiento vertical en el apoyo derecho (rodillo)
        }
    }
    print("Mostrando visualización de viga de ejemplo...")
    plot_structure_pyvista(sample_vis_data_beam, deformation_scale=50, show_plotter_window=True)

    # Ejemplo guardando a archivo:
    # print("\nGuardando visualización de viga de ejemplo en 'beam_visualization.png'...")
    # plot_structure_pyvista(sample_vis_data_beam, deformation_scale=50,
    #                        show_plotter_window=False, screenshot_filename="beam_visualization.png")

    # Ejemplo sin deformada
    # print("\nMostrando visualización de viga (solo original)...")
    # plot_structure_pyvista(sample_vis_data_beam, show_deformed=False, show_plotter_window=True)

    # Ejemplo con datos vacíos o incorrectos (debería manejarlo grácilmente)
    # print("\nProbando con datos vacíos...")
    # plot_structure_pyvista(None)
    # plot_structure_pyvista({"nodes": {}, "elements": [], "displacements": {}})
    # plot_structure_pyvista({"nodes": {1:[0,0,0]}, "elements": [], "displacements": {}})
    # plot_structure_pyvista({"nodes": {1:[0,0,0], 2:[1,0,0]}, "elements": [(1,3)], "displacements": {}}) # Nodo 3 no existe
```
Ahora, necesitamos una forma de llamar a esto desde la GUI. Podríamos añadir un botón "Visualizar 3D" o hacerlo automáticamente después de un análisis exitoso. Por ahora, lo más simple es añadir un botón.

**Modificaciones en `gui_app.py`:**
1.  Importar `plot_structure_pyvista`.
2.  Añadir un atributo `self.last_visualization_data` para guardar los datos del último análisis.
3.  Añadir un botón "Visualizar 3D".
4.  La función del botón llamará a `plot_structure_pyvista` con `self.last_visualization_data`.

Voy a aplicar estos cambios a `gui_app.py`.
