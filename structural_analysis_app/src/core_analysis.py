import openseespy.opensees as ops
# Ensure this relative import works when core_analysis is part of the package
try:
    from .material_library import MaterialLibrary
except ImportError:
    # Fallback for direct script execution (e.g., during development/testing)
    # This assumes material_library.py is in the same directory or PYTHONPATH is set up
    from material_library import MaterialLibrary


# Helper para conversiones (provisional, podría mejorarse)
def N_mm_units_from_json(profile_props, material_props):
    """Converts profile and material properties to N, mm, MPa system."""
    # Perfil:
    # A_cm2 -> A_mm2 (1 cm^2 = 100 mm^2)
    # Ix_cm4 -> Ix_mm4 (1 cm^4 = 10000 mm^4) (OpenSees usa Iz para flexión principal)
    # Iy_cm4 -> Iy_mm4 (1 cm^4 = 10000 mm^4) (OpenSees usa Iy para flexión secundaria)

    # Material:
    # E_mpa -> E_n_mm2 (MPa = N/mm^2, ya está en las unidades correctas)

    conv_profile = {}
    if profile_props:
        conv_profile['A_mm2'] = profile_props.get('A_cm2', 0) * 100
        conv_profile['Iz_mm4'] = profile_props.get('Ix_cm4', 0) * 10000
        conv_profile['Iy_mm4'] = profile_props.get('Iy_cm4', 0) * 10000

    conv_material = {}
    if material_props:
        conv_material['E_n_mm2'] = material_props.get('E_mpa')

    return conv_profile, conv_material


def run_simple_beam_analysis(length_mm, profile_id, material_id, load_n, lib_instance=None, nonlinear_geom=False):
    """
    Realiza un análisis estático de una viga simplemente apoyada
    con una carga puntual en el centro. Puede ser lineal o no lineal geométricamente.

    Args:
        length_mm (float): Longitud de la viga en mm.
        profile_id (str): ID del perfil de la biblioteca.
        material_id (str): ID del material de la biblioteca.
        load_n (float): Carga puntual en el centro en N (negativa si es hacia abajo).
        lib_instance (MaterialLibrary, optional): Instancia de MaterialLibrary.
        nonlinear_geom (bool): True para análisis con no linealidad geométrica (P-Delta).

    Returns:
        dict: Un diccionario con resultados (ej. deflexión máxima, reacciones).
        Retorna None si el análisis falla o hay error en datos.
    """
    ops.wipe()

    library = lib_instance if lib_instance else MaterialLibrary()
    profile_data = library.get_profile(profile_id)
    material_data = library.get_material(material_id)

    if not profile_data or not material_data:
        print(f"Error: Perfil '{profile_id}' o material '{material_id}' no encontrado.")
        return {"status": "error_data_not_found"}

    profile_props = profile_data.get('properties', {})
    material_props = material_data.get('properties', {})

    # Usar el helper de conversión
    # No estamos usando conv_profile y conv_material directamente aún, pero es para el futuro
    # conv_profile_units, conv_material_units = N_mm_units_from_json(profile_props, material_props)

    E_mpa = material_props.get('E_mpa')
    I_cm4 = profile_props.get('Ix_cm4')
    A_cm2 = profile_props.get('A_cm2')

    if E_mpa is None or I_cm4 is None or A_cm2 is None:
        print("Error: Propiedades esenciales (E, Ix, A) no encontradas en JSON.")
        return {"status": "error_missing_properties"}

    E_n_mm2 = E_mpa
    Iz_mm4 = I_cm4 * (10**4) # OpenSees usa Iz para la flexión principal en elementos 2D BeamColumn
    A_mm2 = A_cm2 * (10**2)

    ops.model('basic', '-ndm', 2, '-ndf', 3)

    ops.node(1, 0.0, 0.0)
    ops.node(2, length_mm / 2, 0.0)
    ops.node(3, length_mm, 0.0)

    ops.fix(1, 1, 1, 0)
    ops.fix(3, 0, 1, 0)

    mat_tag = 1
    ops.uniaxialMaterial('Elastic', mat_tag, E_n_mm2) # Material para el comportamiento axial y de flexión

    # --- Transformación Geométrica ---
    # La etiqueta de transformación debe ser única si se definen varias.
    # El tag 1 se usó para el material, así que usamos el tag 2 para la transformación.
    transf_tag_geom = 2
    if nonlinear_geom:
        ops.geomTransf('PDelta', transf_tag_geom)
        # print("Usando transformación PDelta para no linealidad geométrica.")
    else:
        ops.geomTransf('Linear', transf_tag_geom)
        # print("Usando transformación Lineal.")

    # Para 'elasticBeamColumn', las propiedades son A, E, Iz
    # Iz es el momento de inercia para la flexión en el plano xy del elemento.
    ops.element('elasticBeamColumn', 1, 1, 2, A_mm2, E_n_mm2, Iz_mm4, transf_tag_geom)
    ops.element('elasticBeamColumn', 2, 2, 3, A_mm2, E_n_mm2, Iz_mm4, transf_tag_geom)

    pattern_tag = 1
    ops.timeSeries('Linear', pattern_tag)
    ops.pattern('Plain', pattern_tag, pattern_tag)
    ops.load(2, 0.0, load_n, 0.0)

    # --- Configuración del Análisis ---
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0) # Incremento de carga total en un solo paso

    if nonlinear_geom:
        # Para análisis no lineal, Newton es más apropiado.
        ops.algorithm('Newton')
        # Opcional: añadir un test de convergencia si es necesario y el análisis falla
        # ops.test('NormDispIncr', 1.0e-5, 30, 0) # (tol, maxIter, printFlag:0-no, 1-print, 2-print all)
    else:
        ops.algorithm('Linear')

    ops.analysis('Static')

    # Para análisis no lineal, podríamos necesitar múltiples incrementos,
    # pero con LoadControl(1.0) intentamos aplicar toda la carga en un paso.
    # Si falla, se podrían necesitar sub-pasos o ajustes en el test de convergencia.
    analysis_result = ops.analyze(1)

    results = {}
    if analysis_result == 0:
        # --- Obtención de resultados estándar ---
        mid_span_deflection = ops.nodeDisp(2, 2)

        ops.reactions()
        reaction_node1_y = ops.reaction(1, 2)
        reaction_node3_y = ops.reaction(3, 2)

        # --- Recopilar datos para visualización ---
        node_coords_dict = {}
        node_displacements_dict = {}
        # ops.getNodeTags() devuelve una lista de todos los tags de nodos definidos
        all_node_tags = ops.getNodeTags()

        for node_tag in all_node_tags:
            coords = ops.nodeCoord(node_tag)
            node_coords_dict[node_tag] = [coords[0] if len(coords) > 0 else 0.0,
                                          coords[1] if len(coords) > 1 else 0.0,
                                          0.0] # Z=0 para PyVista en 2D

            displacements = ops.nodeDisp(node_tag)
            # Para un modelo 2D ndf=3, displacements es [dx, dy, rz]
            # PyVista espera [dx, dy, dz] para el vector de desplazamiento
            node_displacements_dict[node_tag] = [displacements[0] if len(displacements) > 0 else 0.0,
                                                 displacements[1] if len(displacements) > 1 else 0.0,
                                                 0.0] # dz = 0 para nuestro caso 2D

        element_connectivity_list = []
        # ops.getEleTags() devuelve una lista de todos los tags de elementos definidos
        all_element_tags = ops.getEleTags()
        for ele_tag in all_element_tags:
            ele_nodes = ops.getElementNodes(ele_tag)
            element_connectivity_list.append(tuple(ele_nodes))

        results = {
            "status": "success",
            "analysis_type": "Nonlinear Static (P-Delta)" if nonlinear_geom else "Linear Static",
            "mid_span_deflection_mm": mid_span_deflection,
            "reaction_node1_y_N": reaction_node1_y,
            "reaction_node3_y_N": reaction_node3_y,
            "applied_load_N": load_n,
            "beam_length_mm": length_mm,
            "E_n_mm2": E_n_mm2,
            "Iz_mm4": Iz_mm4,
            "visualization_data": {
                "nodes": node_coords_dict,
                "elements": element_connectivity_list,
                "displacements": node_displacements_dict
            }
        }
    else:
        print(f"Error: Análisis estático ({'No Lineal' if nonlinear_geom else 'Lineal'}) falló.")
        results = {"status": "failure_analysis_failed",
                   "analysis_type": "Nonlinear Static (P-Delta)" if nonlinear_geom else "Linear Static"}

    ops.wipe()
    return results


def run_modal_analysis(length_mm, profile_id, material_id, num_modes, lib_instance=None):
    """
    Realiza un análisis modal de una viga simplemente apoyada.

    Args:
        length_mm (float): Longitud de la viga en mm.
        profile_id (str): ID del perfil de la biblioteca.
        material_id (str): ID del material de la biblioteca.
        num_modes (int): Número de modos a calcular.
        lib_instance (MaterialLibrary, optional): Instancia de MaterialLibrary.

    Returns:
        dict: Un diccionario con los periodos y frecuencias de los modos.
    """
    ops.wipe()
    import numpy as np # Necesario para np.pi y np.sqrt

    library = lib_instance if lib_instance else MaterialLibrary()
    profile_data = library.get_profile(profile_id)
    material_data = library.get_material(material_id)

    if not profile_data or not material_data:
        return {"status": "error_data_not_found", "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

    profile_props = profile_data.get('properties', {})
    material_props = material_data.get('properties', {})

    E_mpa = material_props.get('E_mpa')
    I_cm4 = profile_props.get('Ix_cm4')
    A_cm2 = profile_props.get('A_cm2')
    unit_weight_kn_m3 = material_props.get('unit_weight_kn_m3')

    if E_mpa is None or I_cm4 is None or A_cm2 is None or unit_weight_kn_m3 is None:
        print("Error: Faltan propiedades (E, Ix, A, unit_weight) para análisis modal.")
        return {"status": "error_missing_properties_for_modal", "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

    E_n_mm2 = E_mpa
    Iz_mm4 = I_cm4 * (10**4)
    A_mm2 = A_cm2 * (10**2)

    # Constante gravitacional estándar en mm/s^2 (aprox. 9.80665 m/s^2)
    g_mm_s2 = 9806.65
    # Peso específico en N/mm^3: (kN/m^3) * (1000 N/kN) / (1000 mm/m)^3 = value_kN_m3 * 1e-6 N/mm^3
    gamma_n_mm3 = unit_weight_kn_m3 * 1e-6
    # Densidad de masa en N*s^2/mm^4 (consistente con N, mm, s): (N/mm^3) / (mm/s^2)
    rho_mass_density_consistent = gamma_n_mm3 / g_mm_s2
    # Masa por unidad de longitud para OpenSees (N*s^2/mm): (N*s^2/mm^4) * mm^2
    mass_per_unit_length_ops = rho_mass_density_consistent * A_mm2

    if mass_per_unit_length_ops <= 1e-9: # Evitar masa cero o negativa
        print(f"Error: Masa por unidad de longitud calculada es <= 0 ({mass_per_unit_length_ops}). Verificar propiedades del material (unit_weight_kn_m3).")
        return {"status": "error_non_positive_mass", "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

    ops.model('basic', '-ndm', 2, '-ndf', 3) # Modelo 2D, 3 GDL (dx, dy, rz)

    # Nodos (tag, x, y) - más nodos para mejor representación de modos
    num_nodes_modal = 5 # Aumentar para mejor forma modal (1, centro, final y puntos intermedios)
    node_tags_modal = list(range(1, num_nodes_modal + 1))
    for i, tag in enumerate(node_tags_modal):
        ops.node(tag, (length_mm / (num_nodes_modal - 1)) * i, 0.0)

    ops.fix(node_tags_modal[0], 1, 1, 0)  # Apoyo Articulado en el primer nodo
    ops.fix(node_tags_modal[-1], 0, 1, 0) # Apoyo Rodillo en el último nodo

    mat_tag_modal = 101 # Usar tags diferentes para evitar colisiones con análisis estático
    ops.uniaxialMaterial('Elastic', mat_tag_modal, E_n_mm2)

    transf_tag_modal = 102
    ops.geomTransf('Linear', transf_tag_modal) # Para análisis modal, se usa la rigidez lineal inicial

    # Elementos con masa
    for i in range(num_nodes_modal - 1):
        ele_tag = 101 + i
        node_i = node_tags_modal[i]
        node_j = node_tags_modal[i+1]
        ops.element('elasticBeamColumn', ele_tag, node_i, node_j, A_mm2, E_n_mm2, Iz_mm4, transf_tag_modal, '-mass', mass_per_unit_length_ops)

    try:
        # Calcular eigenvalores (omega^2 en rad^2/s^2)
        # Es importante que num_modes no exceda los GDL libres del sistema.
        # Para una viga 2D con N nodos, GDL totales = N*3. Restricciones reducen esto.
        # GDL libres = (N*3) - num_restricciones. Aquí N=5, GDL=15. Restricciones: 2 en nodo 1, 1 en nodo N => 3 restricciones.
        # GDL libres = 15 - (2+1) = 12.  Así que num_modes <= 12.
        actual_num_modes = min(num_modes, (num_nodes_modal * 3) - 3)
        if actual_num_modes <=0:
             print(f"Error: Número de modos a calcular ({actual_num_modes}) es cero o negativo.")
             ops.wipe()
             return {"status": "failure_eigen_zero_modes", "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

        eigen_values_rad2_s2 = ops.eigen(actual_num_modes)
    except Exception as e:
        print(f"Error durante el cálculo de eigenvalores: {e}")
        ops.wipe()
        return {"status": "failure_eigen_analysis_exception", "error_message": str(e), "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

    if eigen_values_rad2_s2 is None or not isinstance(eigen_values_rad2_s2, list) or not eigen_values_rad2_s2:
        print(f"Error: ops.eigen() no devolvió valores válidos o devolvió: {eigen_values_rad2_s2}")
        ops.wipe()
        return {"status": "failure_eigen_no_values", "periods_s": [], "frequencies_hz": [], "eigen_values_rad2_s2": []}

    periods_s = []
    frequencies_hz = []
    valid_eigen_values = []
    for lambda_val in eigen_values_rad2_s2:
        if lambda_val > 1e-9: # omega^2 debe ser positivo y no numéricamente cero para evitar sqrt(neg) o div by zero
            omega_rad_s = np.sqrt(lambda_val)
            period = (2 * np.pi) / omega_rad_s
            frequency = 1 / period
            periods_s.append(period)
            frequencies_hz.append(frequency)
            valid_eigen_values.append(lambda_val)
        else:
            # Podría indicar un modo de cuerpo rígido si lambda_val es muy cercano a cero
            periods_s.append(float('inf'))
            frequencies_hz.append(0.0)
            valid_eigen_values.append(lambda_val) # Guardar incluso si es problemático

    ops.wipe()
    return {
        "status": "success", "analysis_type": "Modal Analysis",
        "num_modes_requested": num_modes, "num_modes_calculated_actual": actual_num_modes,
        "num_valid_periods_found": len(periods_s),
        "periods_s": periods_s, "frequencies_hz": frequencies_hz,
        "eigen_values_rad2_s2": valid_eigen_values
    }


if __name__ == '__main__':
    import sys
    import os
    # Ajuste para permitir la ejecución directa del script y encontrar material_library
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Re-importar con el path ajustado si es necesario (para el caso de ejecución directa)
    try:
        from src.material_library import MaterialLibrary
    except ModuleNotFoundError:
        from material_library import MaterialLibrary


    # --- Ejemplo de Uso ---
    lib = MaterialLibrary() # Crear instancia de la librería una vez

    # --- Análisis Estático Lineal ---
    print("--- Ejecutando Análisis Estático Lineal ---")
    longitud_viga_mm = 5000.0
    perfil_id_viga = "IR254x32.8"
    material_id_viga = "ACERO_A36" # Asegúrate que este material tenga 'unit_weight_kn_m3'
    # Verificar si ACERO_A36 tiene unit_weight_kn_m3, si no, usar uno que sí lo tenga o añadirlo.
    # Por ejemplo, si ACERO_A36 en tu JSON no tiene unit_weight_kn_m3, el análisis modal fallará.
    # material_data_check = lib.get_material(material_id_viga)
    # if not material_data_check or not material_data_check.get('properties',{}).get('unit_weight_kn_m3'):
    #     print(f"ADVERTENCIA: El material {material_id_viga} no tiene 'unit_weight_kn_m3' definido en JSON. El análisis modal puede fallar o dar resultados incorrectos.")


    carga_viga_n = -10000.0

    resultados_lineal = run_simple_beam_analysis(
        length_mm=longitud_viga_mm,
        profile_id=perfil_id_viga,
        material_id=material_id_viga,
        load_n=carga_viga_n,
        lib_instance=lib,
        nonlinear_geom=False
    )

    if resultados_lineal and resultados_lineal["status"] == "success":
        print("\nResultados del Análisis Estático Lineal:")
        print(f"  Tipo de Análisis: {resultados_lineal['analysis_type']}")
        print(f"  Deflexión máxima (centro): {resultados_lineal['mid_span_deflection_mm']:.4f} mm")
        # ... (imprimir más resultados si se desea)

        # --- Análisis Estático No Lineal (P-Delta) ---
        print("\n--- Ejecutando Análisis Estático No Lineal (P-Delta) ---")
        carga_viga_n_nl = -70000.0 # Carga más alta para intentar ver efectos P-Delta

        resultados_no_lineal = run_simple_beam_analysis(
            length_mm=longitud_viga_mm,
            profile_id=perfil_id_viga,
            material_id=material_id_viga,
            load_n=carga_viga_n_nl,
            lib_instance=lib,
            nonlinear_geom=True
        )

        if resultados_no_lineal and resultados_no_lineal["status"] == "success":
            print("\nResultados del Análisis Estático No Lineal (P-Delta):")
            print(f"  Tipo de Análisis: {resultados_no_lineal['analysis_type']}")
            print(f"  Carga Aplicada: {carga_viga_n_nl} N")
            print(f"  Deflexión máxima (centro): {resultados_no_lineal['mid_span_deflection_mm']:.4f} mm")

            # Comparar con una ejecución lineal con la misma carga alta para ver diferencia P-Delta
            resultados_lineal_cargalta = run_simple_beam_analysis(
                length_mm=longitud_viga_mm, profile_id=perfil_id_viga, material_id=material_id_viga,
                load_n=carga_viga_n_nl, lib_instance=lib, nonlinear_geom=False)
            if resultados_lineal_cargalta["status"] == "success":
                 print(f"  Deflexión (lineal con misma carga): {resultados_lineal_cargalta['mid_span_deflection_mm']:.4f} mm")
                 diff_pct = ((resultados_no_lineal['mid_span_deflection_mm'] - resultados_lineal_cargalta['mid_span_deflection_mm']) / resultados_lineal_cargalta['mid_span_deflection_mm']) * 100
                 print(f"  Diferencia por P-Delta: {diff_pct:.2f}%")
        else:
            print(f"El análisis no lineal no tuvo éxito. Estado: {resultados_no_lineal.get('status', 'desconocido') if resultados_no_lineal else 'Error irrecuperable'}")

    else:
        print(f"El análisis lineal inicial no tuvo éxito. Estado: {resultados_lineal.get('status', 'desconocido') if resultados_lineal else 'Error irrecuperable'}")


    # --- Análisis Modal ---
    print("\n--- Ejecutando Análisis Modal ---")
    num_modos_a_calcular = 5

    # Asegurarse que ACERO_A36 tiene 'unit_weight_kn_m3' en materials_mx.json
    # Si no, el cálculo de masa será incorrecto o fallará.
    # Ejemplo: "ACERO_A36", "properties": { ..., "unit_weight_kn_m3": 77.0 }

    resultados_modal = run_modal_analysis(
        length_mm=longitud_viga_mm,
        profile_id=perfil_id_viga, # Usar el mismo perfil
        material_id=material_id_viga, # Usar el mismo material
        num_modes=num_modos_a_calcular,
        lib_instance=lib
    )

    if resultados_modal and resultados_modal["status"] == "success":
        print("\nResultados del Análisis Modal:")
        print(f"  Tipo de Análisis: {resultados_modal['analysis_type']}")
        print(f"  Modos Solicitados: {resultados_modal['num_modes_requested']}, Modos Calculados: {resultados_modal['num_modes_calculated_actual']}")
        print(f"  Eigenvalues (omega^2): {['{:.2e}'.format(val) for val in resultados_modal.get('eigen_values_rad2_s2', [])]}")
        for i, period_s in enumerate(resultados_modal.get("periods_s", [])):
            freq_hz = resultados_modal.get("frequencies_hz", [])[i]
            print(f"  Modo {i+1}: Periodo = {period_s:.4f} s, Frecuencia = {freq_hz:.2f} Hz")
    else:
        print(f"El análisis modal falló. Estado: {resultados_modal.get('status', 'desconocido') if resultados_modal else 'Error irrecuperable'}")
        if resultados_modal and "error_message" in resultados_modal:
            print(f"  Mensaje de Error: {resultados_modal['error_message']}")
