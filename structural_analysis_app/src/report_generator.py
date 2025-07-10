from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import sys # Para sys.path en el __main__
import datetime

# Asumimos que visualization.py está en el mismo directorio (src)
try:
    from .visualization import plot_structure_pyvista
except ImportError:
    # Fallback para ejecución directa del script
    if __name__ == '__main__': # Solo ajustar path si se ejecuta directamente
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
    from visualization import plot_structure_pyvista


def generate_analysis_report(report_data, output_filename="structural_analysis_report.pdf"):
    """
    Genera un reporte PDF del análisis estructural.

    Args:
        report_data (dict): Contiene todos los datos necesarios para el reporte.
        output_filename (str): Nombre del archivo PDF de salida.

    Returns:
        str: Ruta al archivo PDF generado, o None si falla.
    """
    if not report_data or report_data.get("status") != "success":
        print("Error: Datos insuficientes o análisis no exitoso para generar reporte.")
        return None

    # Crear directorio del reporte si no existe (basado en output_filename)
    output_dir = os.path.dirname(output_filename)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"Error al crear directorio para el reporte {output_dir}: {e}")
            return None # No se puede guardar el reporte si el directorio no se puede crear

    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("Reporte de Análisis Estructural de Viga", styles['h1'])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    now = datetime.datetime.now()
    story.append(Paragraph(f"Fecha de Generación: {now.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>Parámetros de Entrada:</b>", styles['h2']))
    input_params_data = [
        ["Longitud de Viga:", f"{report_data.get('beam_length_mm', 'N/A'):.2f} mm"],
        ["Perfil Estructural:", f"{report_data.get('profile_id', 'N/A')}"],
        ["Material:", f"{report_data.get('material_id', 'N/A')}"],
        ["Carga Puntual Central:", f"{report_data.get('applied_load_N', 'N/A'):.2f} N"],
    ]
    input_table = Table(input_params_data, colWidths=[2.5 * inch, 3.5 * inch])
    input_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(input_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>Resultados del Análisis:</b>", styles['h2']))
    results_data = [
        ["Deflexión Máxima (centro):", f"{report_data.get('mid_span_deflection_mm', 'N/A'):.4f} mm"],
        ["Reacción en Apoyo 1 (Y):", f"{report_data.get('reaction_node1_y_N', 'N/A'):.2f} N"],
        ["Reacción en Apoyo 2 (Y):", f"{report_data.get('reaction_node3_y_N', 'N/A'):.2f} N"],
    ]
    results_table = Table(results_data, colWidths=[2.5 * inch, 3.5 * inch])
    results_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>Visualización del Modelo:</b>", styles['h2']))

    vis_data = report_data.get("visualization_data")
    deformation_scale = report_data.get("deformation_scale", 50.0)

    # Usar un path temporal dentro del directorio del script o un directorio temporal del sistema
    # Para este ejemplo, lo guardaremos donde se ejecuta el script, pero podría ser 'reports/'
    temp_image_dir = os.path.dirname(output_filename) if os.path.dirname(output_filename) else "."
    temp_image_path = os.path.join(temp_image_dir, "temp_visualization_report.png")

    if vis_data:
        try:
            plot_structure_pyvista(vis_data,
                                   show_deformed=True,
                                   deformation_scale=deformation_scale,
                                   show_plotter_window=False,
                                   screenshot_filename=temp_image_path)

            if os.path.exists(temp_image_path):
                img = Image(temp_image_path, width=5.5*inch, height=3.67*inch, hAlign='CENTER')
                story.append(img)
                # No eliminar la imagen aquí si la GUI la va a referenciar.
                # La GUI podría manejar la limpieza o usar un path más persistente.
            else:
                story.append(Paragraph("No se pudo generar la imagen de visualización (archivo no encontrado).", styles['Normal']))
        except Exception as e:
            story.append(Paragraph(f"Error al generar imagen de visualización: {e}", styles['Normal']))
            print(f"Error en plot_structure_pyvista para reporte: {e}")
    else:
        story.append(Paragraph("No hay datos de visualización disponibles para la imagen.", styles['Normal']))

    story.append(Spacer(1, 0.2 * inch))

    E = report_data.get('E_n_mm2')
    I = report_data.get('Iz_mm4')
    P_abs = abs(report_data.get('applied_load_N', 0))
    L_beam = report_data.get('beam_length_mm')

    if E and I and P_abs and L_beam and E > 0 and I > 0:
        deflexion_teorica = (P_abs * (L_beam**3)) / (48 * E * I)
        reaccion_teorica = P_abs / 2
        story.append(Paragraph("<b>Verificación Teórica (Viga Simplemente Apoyada, Carga Central):</b>", styles['h3']))
        theory_data = [
            ["Deflexión Teórica (PL³/48EI):", f"{deflexion_teorica:.4f} mm"],
            ["Reacción Teórica (P/2):", f"{reaccion_teorica:.2f} N"],
        ]
        theory_table = Table(theory_data, colWidths=[3 * inch, 3 * inch])
        theory_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ]))
        story.append(theory_table)
        story.append(Spacer(1, 0.2 * inch))

    try:
        doc.build(story)
        abs_output_path = os.path.abspath(output_filename)
        print(f"Reporte generado exitosamente: {abs_output_path}")
        if os.path.exists(temp_image_path): # Limpiar imagen temporal ahora que el PDF está construido
             try:
                 os.remove(temp_image_path)
             except Exception as e_rem:
                 print(f"Advertencia: No se pudo eliminar la imagen temporal {temp_image_path}: {e_rem}")
        return abs_output_path
    except Exception as e:
        print(f"Error al construir el PDF: {e}")
        if os.path.exists(temp_image_path): # Intentar limpiar incluso si falla la construcción del PDF
             try:
                 os.remove(temp_image_path)
             except Exception as e_rem:
                 print(f"Advertencia: No se pudo eliminar la imagen temporal {temp_image_path}: {e_rem}")
        return None

if __name__ == '__main__':
    current_dir_report = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.abspath(os.path.join(current_dir_report, os.pardir))

    if project_root_dir not in sys.path: # Añadir 'structural_analysis_app' al path
        sys.path.insert(0, project_root_dir)

    # Re-importar con el path correcto si es necesario para __main__
    try:
        from src.visualization import plot_structure_pyvista
    except ImportError: # Si ya está en 'src' y se ejecuta 'python report_generator.py'
        from visualization import plot_structure_pyvista


    sample_report_data = {
        "beam_length_mm": 5000.0, "profile_id": "IR254x32.8", "material_id": "ACERO_A36",
        "applied_load_N": -10000.0, "mid_span_deflection_mm": -2.6733,
        "reaction_node1_y_N": 5000.0, "reaction_node3_y_N": 5000.0,
        "status": "success", "E_n_mm2": 200000.0, "Iz_mm4": 48700000.0,
        "deformation_scale": 50.0,
        "visualization_data": {
            "nodes": { 1: [0.0,0.0,0.0], 2: [2500.0,0.0,0.0], 3: [5000.0,0.0,0.0] },
            "elements": [ (1,2), (2,3) ],
            "displacements": { 1: [0.0,0.0,0.0], 2: [0.0,-2.6733,0.0], 3: [0.0,0.0,0.0] }
        }
    }

    reports_dir = os.path.join(project_root_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    report_file_path = os.path.join(reports_dir, "sample_structural_report.pdf")

    generated_pdf = generate_analysis_report(sample_report_data, output_filename=report_file_path)
    if generated_pdf:
        print(f"Reporte de ejemplo generado en: {generated_pdf}")
        # import webbrowser
        # webbrowser.open(f"file://{generated_pdf}") # Abrir con file:// para asegurar que funcione en todos los OS
    else:
        print("Fallo al generar el reporte de ejemplo.")
