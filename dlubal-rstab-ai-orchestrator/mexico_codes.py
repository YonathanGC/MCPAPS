# Módulo para definir reglas de diseño estructural mexicano (NTC, CFE, AISC-LRFD, ACI 318)

# Este archivo contendrá la lógica, parámetros y datos relevantes
# de las normativas de diseño estructural utilizadas en México.
# La idea es que DeepSeek pueda consultar esta información o que
# este módulo pueda validar/complementar las sugerencias de la IA.

# TODO: Poblar este módulo con datos y funciones específicas de las normativas.
# Esto es una tarea compleja que requiere conocimiento experto en ingeniería estructural
# y las normativas mencionadas.

# --- Ejemplos de Estructuras de Datos ---

NTC_CONCRETO_DF_2017_EJEMPLO = {
    "nombre": "Normas Técnicas Complementarias para Diseño y Construcción de Estructuras de Concreto (CDMX 2017)",
    "requisitos_minimos": {
        "concreto_clase_1": {
            "resistencia_compresion_fc_min_mpa": 25, # MPa (equivale a ~250 kg/cm^2)
            "modulo_elasticidad_mpa_formula": "14000 * sqrt(fc_mpa)", # Ejemplo
        },
        "acero_refuerzo": {
            "grado_42": {"fy_mpa": 420}, # Límite de fluencia
            "grado_52": {"fy_mpa": 520}, # No tan común para corrugado estándar
            "recubrimiento_minimo_mm": {
                "losas_trabes_columnas_interior": 20,
                "elementos_expuestos_intemperie_suelo": 40,
                "cimentaciones_contacto_suelo": 75,
            }
        },
        "factores_resistencia_flexion": 0.90,
        "factores_resistencia_cortante": 0.75, # Varía según el caso
    },
    "referencia": "Gaceta Oficial de la Ciudad de México"
}

NTC_ACERO_DF_2017_EJEMPLO = {
    "nombre": "Normas Técnicas Complementarias para Diseño y Construcción de Estructuras de Acero (CDMX 2017)",
    "perfiles_comunes": ["IPR", "OC", "CE", "TR"],
    "aceros_estructurales": {
        "ASTM_A36": {"fy_mpa": 250, "fu_mpa": 400},
        "ASTM_A572_Gr50": {"fy_mpa": 345, "fu_mpa": 450}, # A992 es similar a A572 Gr 50 en EEUU
        "ASTM_A992": {"fy_mpa": 345, "fu_mpa": 450} # fy entre 345 y 448 MPa (50-65 ksi)
    },
    "metodo_diseño_predeterminado": "LRFD", # Puede ser ASD también
    "factores_resistencia_lrfd": {
        "flexion": 0.90,
        "compresion": 0.90,
        "tension_fluencia": 0.90,
        "tension_fractura": 0.75,
        "cortante": 0.90, # O 1.0 dependiendo de la sección
    },
    "referencia": "Gaceta Oficial de la Ciudad de México"
}

AISC_LRFD_2016_EJEMPLO = { # (AISC 360-16 es una referencia común para LRFD)
    "nombre": "AISC Specification for Structural Steel Buildings (ANSI/AISC 360-16) - LRFD",
    "general": {
        "phi_b": 0.90, # Factor de resistencia para flexión
        "phi_c": 0.90, # Factor de resistencia para compresión
        "phi_t_yield": 0.90, # Factor de resistencia para tensión (fluencia)
        "phi_t_rupture": 0.75, # Factor de resistencia para tensión (fractura)
        "phi_v": 0.90, # Factor de resistencia para cortante (generalmente)
    },
    "materiales_acero": {
        "A992": {"Fy_ksi": 50, "Fu_ksi": 65} # Fy en ksi
    }
}

ACI_318_19_EJEMPLO = { # (ACI 318-19 es una referencia común para concreto)
    "nombre": "Building Code Requirements for Structural Concrete (ACI 318-19)",
    "general": {
        "phi_flexion": 0.90, # Para secciones controladas por tensión
        "phi_cortante": 0.75,
        "phi_compresion_axial_espirales": 0.75,
        "phi_compresion_axial_estribos": 0.65,
    },
    "concreto": {
        "fc_min_psi": 3000, # Resistencia mínima a la compresión en psi
    },
    "acero_refuerzo": {
        "Grade_60": {"fy_ksi": 60} # Límite de fluencia en ksi
    }
}


# --- Funciones de Ejemplo (Conceptuales) ---

def obtener_propiedades_material(normativa: str, tipo_material: str, especificacion: str) -> dict:
    """
    Obtiene propiedades de un material según una normativa específica.
    Ejemplo: obtener_propiedades_material("NTC_ACERO_DF_2017", "acero", "ASTM_A992")
    """
    # TODO: Implementar la lógica para buscar en las estructuras de datos
    if normativa == "NTC_ACERO_DF_2017_EJEMPLO" and tipo_material == "acero":
        return NTC_ACERO_DF_2017_EJEMPLO["aceros_estructurales"].get(especificacion, {})
    elif normativa == "AISC_LRFD_2016_EJEMPLO" and tipo_material == "acero":
        # Convertir ksi a MPa si es necesario para consistencia interna
        props_ksi = AISC_LRFD_2016_EJEMPLO["materiales_acero"].get(especificacion, {})
        if props_ksi:
            return {
                "fy_mpa": props_ksi.get("Fy_ksi", 0) * 6.89476,
                "fu_mpa": props_ksi.get("Fu_ksi", 0) * 6.89476
            }
        return {}
    # Añadir más casos para otras normativas y materiales
    print(f"Advertencia: Normativa '{normativa}' o material '{tipo_material}' no implementado.")
    return {}

def verificar_cumplimiento_seccion_viga_acero(seccion_propiedades: dict, normativa: str, momento_actuante_mu: float, cortante_actuante_vu: float) -> dict:
    """
    Verifica (de forma muy simplificada) si una sección de viga de acero cumple
    con los requisitos de resistencia bajo una normativa dada.
    - seccion_propiedades: dict con {'Zx_cm3': valor, 'Aw_cm2': valor, 'material_fy_mpa': valor}
    - normativa: string identificador de la normativa
    - momento_actuante_mu: Momento flector último (ej. en kN-m)
    - cortante_actuante_vu: Fuerza cortante última (ej. en kN)
    """
    # TODO: Esta es una sobresimplificación extrema. El diseño real es mucho más complejo.
    # Se necesitarían propiedades completas de la sección, consideraciones de pandeo, etc.
    print(f"Verificando cumplimiento para viga de acero bajo {normativa} (simulado)...")

    resultados = {"cumple_flexion": False, "cumple_cortante": False, "detalles": ""}

    material_fy_mpa = seccion_propiedades.get("material_fy_mpa")
    Zx_cm3 = seccion_propiedades.get("Zx_cm3") # Módulo plástico
    Aw_cm2 = seccion_propiedades.get("Aw_cm2") # Área de cortante

    if not all([material_fy_mpa, Zx_cm3, Aw_cm2]):
        resultados["detalles"] = "Propiedades de sección o material incompletas."
        return resultados

    # Conversión de unidades (ejemplo: kN-m a N-mm, kN a N, MPa a N/mm2)
    # 1 MPa = 1 N/mm^2
    # Zx en cm^3 a mm^3: Zx_mm3 = Zx_cm3 * 1000
    # Aw en cm^2 a mm^2: Aw_mm2 = Aw_cm2 * 100
    # Mu en kN-m a N-mm: Mu_Nmm = momento_actuante_mu * 1e6
    # Vu en kN a N: Vu_N = cortante_actuante_vu * 1e3

    Zx_mm3 = Zx_cm3 * 1000
    Aw_mm2 = Aw_cm2 * 100
    Mu_Nmm = momento_actuante_mu * 1e6
    Vu_N = cortante_actuante_vu * 1e3
    fy_N_mm2 = material_fy_mpa

    if normativa == "AISC_LRFD_2016_EJEMPLO" or normativa == "NTC_ACERO_DF_2017_EJEMPLO": # Asumiendo LRFD
        phi_b = AISC_LRFD_2016_EJEMPLO["general"]["phi_b"] # 0.9 para flexión
        # Para cortante, phi_v puede ser 0.9 o 1.0. Usaremos 0.9 como simplificación.
        # 0.6 * Fy * Aw es una fórmula común para Vn nominal en cortante (sin considerar pandeo de alma)
        phi_v = AISC_LRFD_2016_EJEMPLO["general"]["phi_v"]

        # Resistencia a flexión de diseño (phi * Mn)
        # Mn = Fy * Zx (simplificado, no considera pandeo lateral torsional)
        phi_Mn_Nmm = phi_b * fy_N_mm2 * Zx_mm3

        # Resistencia a cortante de diseño (phi * Vn)
        # Vn = 0.6 * Fy * Aw * Cv (Cv es un factor, simplificamos a 1)
        phi_Vn_N = phi_v * 0.6 * fy_N_mm2 * Aw_mm2

        if phi_Mn_Nmm >= Mu_Nmm:
            resultados["cumple_flexion"] = True
        resultados["detalles"] += f"Flexión: Mu={momento_actuante_mu:.2f} kN-m, Phi*Mn={phi_Mn_Nmm/1e6:.2f} kN-m. "

        if phi_Vn_N >= Vu_N:
            resultados["cumple_cortante"] = True
        resultados["detalles"] += f"Cortante: Vu={cortante_actuante_vu:.2f} kN, Phi*Vn={phi_Vn_N/1e3:.2f} kN."

    else:
        resultados["detalles"] = f"Normativa {normativa} no implementada para verificación."

    return resultados


if __name__ == '__main__':
    print("--- Módulo de Normativas Mexicanas de Diseño Estructural ---")

    # Ejemplo de obtención de propiedades de material
    props_a992_ntc = obtener_propiedades_material("NTC_ACERO_DF_2017_EJEMPLO", "acero", "ASTM_A992")
    print(f"\nPropiedades ASTM A992 (NTC DF 2017): {props_a992_ntc}")

    props_a992_aisc = obtener_propiedades_material("AISC_LRFD_2016_EJEMPLO", "acero", "A992")
    print(f"Propiedades ASTM A992 (AISC LRFD 2016, convertidas a MPa): {props_a992_aisc}")

    # Ejemplo de verificación simplificada de una viga
    # Suponer una viga IPR con Zx=500 cm3, Aw=20 cm2, Acero A992 (Fy=345 MPa)
    # Cargas: Mu = 100 kN-m, Vu = 150 kN
    propiedades_viga_ejemplo = {
        "Zx_cm3": 500,
        "Aw_cm2": 20,
        "material_fy_mpa": props_a992_aisc.get("fy_mpa", 345) # Usar Fy de A992
    }
    momento_ultimo = 100 # kN-m
    cortante_ultimo = 150 # kN

    verificacion_aisc = verificar_cumplimiento_seccion_viga_acero(
        propiedades_viga_ejemplo,
        "AISC_LRFD_2016_EJEMPLO",
        momento_ultimo,
        cortante_ultimo
    )
    print(f"\nVerificación de viga (AISC LRFD 2016): {verificacion_aisc}")

    # Ejemplo con NTC Acero (usará la misma lógica LRFD en esta simulación)
    verificacion_ntc = verificar_cumplimiento_seccion_viga_acero(
        propiedades_viga_ejemplo,
        "NTC_ACERO_DF_2017_EJEMPLO",
        momento_ultimo,
        cortante_ultimo
    )
    print(f"Verificación de viga (NTC Acero DF 2017): {verificacion_ntc}")

    # Ejemplo de un caso que no cumple (aumentando cargas)
    momento_ultimo_alto = 200 # kN-m
    cortante_ultimo_alto = 300 # kN
    verificacion_alto_aisc = verificar_cumplimiento_seccion_viga_acero(
        propiedades_viga_ejemplo,
        "AISC_LRFD_2016_EJEMPLO",
        momento_ultimo_alto,
        cortante_ultimo_alto
    )
    print(f"Verificación de viga con cargas altas (AISC LRFD 2016): {verificacion_alto_aisc}")
