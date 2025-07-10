import ezdxf
import os

def export_model_to_dxf(model_data, output_filename="structural_model.dxf"):
    """
    Exporta la geometría del modelo estructural a un archivo DXF.

    Args:
        model_data (dict): Diccionario que contiene la geometría del modelo.
                           Debe tener una clave 'visualization_data' con:
                           'nodes': {tag: [x, y, z], ...}
                           'elements': [(n_tag1, n_tag2), ...]
        output_filename (str): Nombre del archivo DXF de salida.

    Returns:
        str: Ruta al archivo DXF generado, o None si falla.
    """
    if not model_data or "visualization_data" not in model_data:
        print("Error: No hay datos de modelo válidos para exportar a DXF.")
        return None

    vis_data = model_data.get("visualization_data", {}) # Usar .get para evitar KeyError
    nodes_dict = vis_data.get("nodes")
    elements_conn = vis_data.get("elements")

    if not nodes_dict or not elements_conn:
        print("Error: Faltan datos de nodos o elementos en los datos de visualización.")
        return None

    try:
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()

        doc.layers.add(name="NODES", color=1)
        doc.layers.add(name="ELEMENTS_LINES", color=5)

        # Convertir nodos a un formato que ezdxf espera y mapear tags a coordenadas
        node_coords_map = {}
        for node_tag, coords in nodes_dict.items():
            if isinstance(coords, list) and len(coords) >= 2:
                # Asegurar que Z sea 0.0 si solo se proporcionan X, Y
                x, y = coords[0], coords[1]
                z = coords[2] if len(coords) > 2 else 0.0
                node_coords_map[node_tag] = (float(x), float(y), float(z))
            else:
                print(f"Advertencia: Coordenadas inválidas para nodo {node_tag}: {coords}. Se omitirá.")

        # Opcional: Añadir nodos como puntos DXF (POINTS)
        # for node_tag in node_coords_map:
        #     msp.add_point(location=node_coords_map[node_tag], dxfattribs={'layer': 'NODES'})


        for elem in elements_conn:
            if isinstance(elem, (list, tuple)) and len(elem) == 2:
                node_tag_i, node_tag_j = elem

                coord_i = node_coords_map.get(node_tag_i)
                coord_j = node_coords_map.get(node_tag_j)

                if coord_i and coord_j:
                    msp.add_line(start=coord_i, end=coord_j, dxfattribs={'layer': 'ELEMENTS_LINES'})
                else:
                    missing_nodes_info = []
                    if not coord_i: missing_nodes_info.append(f"nodo {node_tag_i}")
                    if not coord_j: missing_nodes_info.append(f"nodo {node_tag_j}")
                    print(f"Advertencia: Coordenadas no encontradas para {', '.join(missing_nodes_info)} en elemento {elem}.")
            else:
                print(f"Advertencia: Elemento {elem} no es una línea simple de 2 nodos, no se exportará como línea.")

        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Directorio creado: {output_dir}")
            except OSError as e:
                print(f"Error al crear directorio {output_dir}: {e}")
                # Podríamos decidir no continuar si no se puede crear el directorio.
                # Por ahora, ezdxf podría fallar al guardar si el path es inválido.

        doc.saveas(output_filename)
        abs_output_path = os.path.abspath(output_filename)
        print(f"Modelo exportado a DXF exitosamente: {abs_output_path}")
        return abs_output_path

    except Exception as e:
        print(f"Error al generar el archivo DXF: {type(e).__name__} - {e}")
        return None

if __name__ == '__main__':
    sample_model_data_for_dxf = {
        "visualization_data": {
            "nodes": {
                1: [0.0, 0.0, 0.0], 2: [5000.0, 0.0, 0.0],
                3: [5000.0, 3000.0, 0.0], 4: [0.0, 3000.0, 0.0]
            },
            "elements": [ (1, 2), (2, 3), (3, 4), (4, 1) ]
        }
    }

    # Determinar el directorio 'exports' relativo al directorio raíz del proyecto
    # structural_analysis_app/
    # |- src/
    #    |- export_dxf.py  <-- current_script_dir
    # |- exports/           <-- target_exports_dir
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, os.pardir))
    target_exports_dir = os.path.join(project_root, 'exports')

    if not os.path.exists(target_exports_dir):
        os.makedirs(target_exports_dir, exist_ok=True)
        print(f"Directorio de prueba para exportación creado: {target_exports_dir}")

    dxf_file_path = os.path.join(target_exports_dir, "sample_model_export.dxf")

    generated_dxf = export_model_to_dxf(sample_model_data_for_dxf, output_filename=dxf_file_path)
    if generated_dxf:
        print(f"Archivo DXF de ejemplo generado en: {generated_dxf}")
    else:
        print("Fallo al generar el archivo DXF de ejemplo.")

    # Ejemplo con datos incompletos
    print("\nProbando con datos incompletos:")
    export_model_to_dxf({"visualization_data": {"nodes": {1: [0,0,0]}}}, "exports_test/incomplete.dxf")
    export_model_to_dxf(None, "exports_test/none_data.dxf")
