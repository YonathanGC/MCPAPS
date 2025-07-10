import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
import sys
import datetime # Necesario para generar_report y export_dxf

# Adjust path to import from sibling directories or parent project directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_src_parent = os.path.abspath(os.path.join(current_dir, os.pardir))

if project_root_src_parent not in sys.path:
    sys.path.insert(0, project_root_src_parent)

try:
    from src.material_library import MaterialLibrary
    from src.core_analysis import run_simple_beam_analysis, run_modal_analysis
    from src.visualization import plot_structure_pyvista
    from src.report_generator import generate_analysis_report
    from src.gemini_integration import generate_analysis_summary_prompt, generate_text_with_gemini, configure_gemini_once
    from src.export_dxf import export_model_to_dxf # Nueva importación
except ImportError:
    # Fallback for cases where the script is run directly
    from material_library import MaterialLibrary
    from core_analysis import run_simple_beam_analysis, run_modal_analysis
    from visualization import plot_structure_pyvista
    from report_generator import generate_analysis_report
    from gemini_integration import generate_analysis_summary_prompt, generate_text_with_gemini, configure_gemini_once
    from export_dxf import export_model_to_dxf # Nueva importación


class StructuralAnalysisGUI:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Aplicación de Análisis Estructural")
        self.root.geometry("950x700") # Ampliar para nuevo botón

        self.last_visualization_data = None
        self.last_analysis_full_results = None
        self.current_analysis_type = None


        if not configure_gemini_once():
            messagebox.showwarning("Configuración de Gemini",
                                 "No se pudo configurar la API de Gemini. "
                                 "La funcionalidad de resumen con IA no estará disponible. "
                                 "Asegúrate de que la variable de entorno GOOGLE_API_KEY esté configurada.")

        try:
            self.library = MaterialLibrary()
        except Exception as e:
            messagebox.showerror("Error de Inicialización", f"No se pudo cargar la biblioteca de materiales/perfiles: {e}\nAsegúrese que los archivos JSON están en la carpeta 'data'.")
            self.root.destroy()
            return

        input_frame = ttk.LabelFrame(self.root, text="Parámetros de Entrada", padding="10")
        input_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(input_frame, text="Longitud de la Viga (mm):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.length_var = tk.StringVar(value="5000")
        ttk.Entry(input_frame, textvariable=self.length_var, width=20).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Perfil:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.profile_ids = self.library.list_profile_ids()
        self.profile_var = tk.StringVar(value=self.profile_ids[0] if self.profile_ids else "")
        ttk.Combobox(input_frame, textvariable=self.profile_var, values=self.profile_ids, state="readonly", width=25).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Material:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.material_ids = self.library.list_material_ids()
        self.material_var = tk.StringVar(value=self.material_ids[0] if self.material_ids else "")
        ttk.Combobox(input_frame, textvariable=self.material_var, values=self.material_ids, state="readonly", width=25).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Carga Puntual Central (N, negativa hacia abajo):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.load_var = tk.StringVar(value="-10000")
        ttk.Entry(input_frame, textvariable=self.load_var, width=20).grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Escala Deformación (Visualización):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.deformation_scale_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.deformation_scale_var, width=20).grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        self.nonlinear_geom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="No Linealidad Geométrica (P-Delta)", variable=self.nonlinear_geom_var).grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(input_frame, text="Número de Modos (Análisis Modal):").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.num_modes_var = tk.StringVar(value="3")
        ttk.Entry(input_frame, textvariable=self.num_modes_var, width=20).grid(row=6, column=1, padx=5, pady=5, sticky="ew")

        input_frame.columnconfigure(1, weight=1)

        analysis_buttons_frame = ttk.Frame(self.root)
        analysis_buttons_frame.pack(pady=(10,0))

        self.static_analysis_button = ttk.Button(analysis_buttons_frame, text="Análisis Estático", command=self.perform_static_analysis, style="Accent.TButton")
        self.static_analysis_button.pack(side=tk.LEFT, padx=5)

        self.modal_analysis_button = ttk.Button(analysis_buttons_frame, text="Análisis Modal", command=self.perform_modal_analysis, style="Accent.TButton")
        self.modal_analysis_button.pack(side=tk.LEFT, padx=5)

        post_process_buttons_frame = ttk.Frame(self.root)
        post_process_buttons_frame.pack(pady=(5,10))

        self.visualize_button = ttk.Button(post_process_buttons_frame, text="Visualizar 3D (Estático)", command=self.visualize_results, state=tk.DISABLED)
        self.visualize_button.pack(side=tk.LEFT, padx=5)

        self.report_button = ttk.Button(post_process_buttons_frame, text="Reporte PDF (Estático)", command=self.generate_report, state=tk.DISABLED)
        self.report_button.pack(side=tk.LEFT, padx=5)

        self.gemini_summary_button = ttk.Button(post_process_buttons_frame, text="Resumen IA (Estático)", command=self.generate_ia_summary, state=tk.DISABLED)
        self.gemini_summary_button.pack(side=tk.LEFT, padx=5)

        self.export_dxf_button = ttk.Button(post_process_buttons_frame, text="Exportar DXF (Estático)", command=self.export_to_dxf, state=tk.DISABLED)
        self.export_dxf_button.pack(side=tk.LEFT, padx=5)

        s = ttk.Style()
        s.configure('Accent.TButton', font=('Helvetica', 10, 'bold'), padding=5)

        results_frame = ttk.LabelFrame(self.root, text="Resultados del Análisis", padding="10")
        results_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.results_text = tk.Text(results_frame, wrap="word", height=18, width=90, font=("Courier New", 9))
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.results_text.config(state="disabled")

    def _reset_ui_before_analysis(self):
        self.last_visualization_data = None
        self.last_analysis_full_results = None
        self.current_analysis_type = None
        self.visualize_button.config(state=tk.DISABLED)
        self.report_button.config(state=tk.DISABLED)
        self.gemini_summary_button.config(state=tk.DISABLED)
        self.export_dxf_button.config(state=tk.DISABLED)

        self.results_text.config(state="normal")
        self.results_text.delete(1.0, tk.END)
        self.root.update_idletasks()

    def perform_static_analysis(self):
        self._reset_ui_before_analysis()
        self.current_analysis_type = "static"
        self.results_text.insert(tk.END, "Ejecutando Análisis Estático...\nPor favor, espere.\n\n")
        self.root.update_idletasks()

        try:
            length = float(self.length_var.get())
            profile_id = self.profile_var.get()
            material_id = self.material_var.get()
            load = float(self.load_var.get())
            is_nonlinear_geom = self.nonlinear_geom_var.get()

            if not profile_id or not material_id:
                messagebox.showerror("Error de Entrada", "Debe seleccionar un perfil y un material.")
                self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                return

            if not self.library.get_profile(profile_id) or not self.library.get_material(material_id):
                 messagebox.showerror("Error de Datos", f"Perfil '{profile_id}' o Material '{material_id}' no válido o no encontrado.")
                 self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                 return

            results = run_simple_beam_analysis(
                length_mm=length, profile_id=profile_id, material_id=material_id,
                load_n=load, lib_instance=self.library, nonlinear_geom=is_nonlinear_geom
            )
            self.last_analysis_full_results = results

            self.results_text.delete(1.0, tk.END)
            self.results_text.config(state="normal")

            if results and results.get("status") == "success":
                self.last_visualization_data = results.get("visualization_data")
                if self.last_visualization_data:
                    self.visualize_button.config(state=tk.NORMAL)
                    self.export_dxf_button.config(state=tk.NORMAL)
                self.report_button.config(state=tk.NORMAL)
                if configure_gemini_once(): self.gemini_summary_button.config(state=tk.NORMAL)

                output = f"Análisis Estático ({results.get('analysis_type', '')}) Completado Exitosamente:\n"
                output += f"  Longitud de Viga: {results['beam_length_mm']:.2f} mm\n"
                output += f"  Perfil: {profile_id}\n  Material: {material_id}\n"
                output += f"  Carga Aplicada: {results['applied_load_N']:.2f} N\n"
                output += f"  ---------------------------------------\n"
                output += f"  Deflexión Máxima (centro): {results['mid_span_deflection_mm']:.4f} mm\n"
                output += f"  Reacción en Nodo 1 (Y): {results['reaction_node1_y_N']:.2f} N\n"
                output += f"  Reacción en Nodo 3 (Y): {results['reaction_node3_y_N']:.2f} N\n"

                E = results.get('E_n_mm2'); I = results.get('Iz_mm4')
                P_abs = abs(results.get('applied_load_N', 0)); L_beam = results.get('beam_length_mm')

                if E and I and P_abs and L_beam and E > 0 and I > 0:
                    if not is_nonlinear_geom:
                        deflex_teorica = (P_abs * (L_beam**3)) / (48 * E * I)
                        reac_teorica = P_abs / 2
                        output += f"  ---------------------------------------\n  Verificación Teórica (Lineal - PL^3/48EI):\n"
                        output += f"    E (N/mm^2) : {E:.2f}\n    Iz (mm^4)  : {I:.2f}\n"
                        output += f"    Deflexión  : {deflex_teorica:.4f} mm\n    Reacción   : {reac_teorica:.2f} N\n"
                    else:
                        output += f"  (Verificación teórica lineal no aplica directamente para P-Delta)\n"
                self.results_text.insert(tk.END, output)
            else:
                self.results_text.insert(tk.END, f"Análisis Estático no exitoso.\nEstado: {results.get('status', 'desconocido') if results else 'Error irrecuperable'}")
        except ValueError:
            messagebox.showerror("Error de Entrada", "Valores numéricos inválidos para parámetros de análisis estático.")
            self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.insert(tk.END, "Error en datos de entrada.");
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Error en análisis estático: {type(e).__name__} - {e}")
            self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.insert(tk.END, f"Error inesperado: {e}");
        finally:
            if not (self.results_text.get("1.0",tk.END).strip()):
                self.results_text.config(state="normal"); self.results_text.insert(tk.END, "Análisis estático no completado o error.");
            self.results_text.config(state="disabled")

    def perform_modal_analysis(self):
        self._reset_ui_before_analysis()
        self.current_analysis_type = "modal"
        self.results_text.insert(tk.END, "Ejecutando Análisis Modal...\nPor favor, espere.\n\n")
        self.root.update_idletasks()

        try:
            length = float(self.length_var.get())
            profile_id = self.profile_var.get()
            material_id = self.material_var.get()
            num_modes = int(self.num_modes_var.get())

            if not profile_id or not material_id:
                messagebox.showerror("Error de Entrada", "Debe seleccionar un perfil y un material para el análisis modal.")
                self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                return
            if num_modes <= 0:
                messagebox.showerror("Error de Entrada", "El número de modos debe ser un entero positivo.")
                self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                return

            material_data = self.library.get_material(material_id)
            if not self.library.get_profile(profile_id) or not material_data:
                messagebox.showerror("Error de Datos", f"Perfil '{profile_id}' o Material '{material_id}' no válido.")
                self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                return
            if not material_data.get('properties', {}).get('unit_weight_kn_m3'):
                messagebox.showerror("Error de Material", f"El material '{material_id}' no tiene 'unit_weight_kn_m3', necesario para análisis modal.")
                self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.config(state="disabled")
                return

            results = run_modal_analysis(
                length_mm=length, profile_id=profile_id, material_id=material_id,
                num_modes=num_modes, lib_instance=self.library
            )
            self.last_analysis_full_results = results

            self.results_text.delete(1.0, tk.END)
            self.results_text.config(state="normal")

            if results and results.get("status") == "success":
                output = f"Análisis Modal ({results.get('analysis_type', '')}) Completado Exitosamente:\n"
                output += f"  Longitud de Viga: {length:.2f} mm\n  Perfil: {profile_id}\n  Material: {material_id}\n"
                output += f"  Modos Solicitados: {results.get('num_modes_requested', 'N/A')}, Calculados: {results.get('num_modes_calculated_actual', 'N/A')}\n"
                output += "  ---------------------------------------\n  Resultados Modales:\n"
                periods = results.get("periods_s", []); frequencies = results.get("frequencies_hz", []); eigen_values = results.get("eigen_values_rad2_s2", [])
                for i in range(len(periods)):
                    output += f"    Modo {i+1}: Periodo = {periods[i]:.4f} s, Frecuencia = {frequencies[i]:.2f} Hz (Eigenvalue ω² = {eigen_values[i]:.2e})\n"
                self.results_text.insert(tk.END, output)
            else:
                err_msg = results.get('error_message', results.get('status', 'desconocido')) if results else "Error desconocido"
                self.results_text.insert(tk.END, f"Análisis Modal no exitoso.\nEstado: {err_msg}")
                if any(sub in str(err_msg) for sub in ["error_non_positive_mass", "unit_weight_kn_m3", "failure_eigen"]):
                     self.results_text.insert(tk.END, f"\nVerifique 'unit_weight_kn_m3' en JSON para '{material_id}' o el número de modos.")
        except ValueError:
            messagebox.showerror("Error de Entrada", "Valores numéricos inválidos para parámetros de análisis modal.")
            self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.insert(tk.END, "Error en datos de entrada.");
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Error en análisis modal: {type(e).__name__} - {e}")
            self.results_text.config(state="normal"); self.results_text.delete(1.0, tk.END); self.results_text.insert(tk.END, f"Error inesperado: {e}");
        finally:
            if not (self.results_text.get("1.0",tk.END).strip()):
                 self.results_text.config(state="normal"); self.results_text.insert(tk.END, "Análisis modal no completado o error.");
            self.results_text.config(state="disabled")

    def visualize_results(self):
        if not self.last_visualization_data or self.current_analysis_type != "static":
            messagebox.showinfo("Visualización", "Datos de visualización no disponibles o no es de un análisis estático. Ejecute un análisis estático primero.")
            return
        try: scale = float(self.deformation_scale_var.get())
        except ValueError: messagebox.showerror("Error de Entrada", "Escala de deformación inválida."); scale = 50.0
        try:
            plot_structure_pyvista(self.last_visualization_data, show_deformed=True, deformation_scale=scale, show_plotter_window=True)
        except Exception as e: messagebox.showerror("Error de Visualización", f"No se pudo generar la visualización: {e}"); print(f"Error al llamar a plot_structure_pyvista: {e}")

    def generate_report(self):
        if not self.last_analysis_full_results or self.last_analysis_full_results.get("status") != "success" or self.current_analysis_type != "static":
            messagebox.showinfo("Generar Reporte", "Resultados de análisis estático válidos no disponibles. Ejecute un análisis estático exitoso primero.")
            return
        try: deformation_scale_for_report = float(self.deformation_scale_var.get())
        except ValueError: deformation_scale_for_report = 50.0

        report_data_for_pdf = self.last_analysis_full_results.copy()
        report_data_for_pdf["deformation_scale"] = deformation_scale_for_report
        report_data_for_pdf["profile_id"] = self.profile_var.get()
        report_data_for_pdf["material_id"] = self.material_var.get()

        reports_dir = os.path.join(project_root_src_parent, 'reports')
        if not os.path.exists(reports_dir):
            try: os.makedirs(reports_dir)
            except Exception as e: messagebox.showerror("Error de Reporte", f"No se pudo crear directorio de reportes: {reports_dir}\n{e}"); return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"analysis_report_{timestamp}.pdf"
        full_report_path = os.path.join(reports_dir, report_filename)

        try:
            self.results_text.config(state="normal"); self.results_text.insert(tk.END, f"\n\nGenerando reporte en {full_report_path}..."); self.root.update_idletasks()
            generated_pdf_path = generate_analysis_report(report_data_for_pdf, output_filename=full_report_path)
            if generated_pdf_path:
                messagebox.showinfo("Reporte Generado", f"Reporte PDF generado:\n{generated_pdf_path}")
                self.results_text.insert(tk.END, f"\nReporte generado: {generated_pdf_path}")
            else:
                messagebox.showerror("Error de Reporte", "No se pudo generar el reporte PDF.")
                self.results_text.insert(tk.END, "\nFallo al generar el reporte.")
        except Exception as e:
            messagebox.showerror("Error de Reporte", f"Ocurrió un error al generar el reporte: {e}")
            self.results_text.insert(tk.END, f"\nError al generar reporte: {e}")
        finally: self.results_text.config(state="disabled")

    def generate_ia_summary(self):
        if not self.last_analysis_full_results or self.last_analysis_full_results.get("status") != "success" or self.current_analysis_type != "static":
            messagebox.showinfo("Resumen con IA", "Resultados de análisis estático válidos no disponibles. Ejecute un análisis estático exitoso primero.")
            return
        if not configure_gemini_once():
            messagebox.showerror("Error de Gemini", "API de Gemini no configurada."); return

        self.results_text.config(state="normal"); self.results_text.insert(tk.END, "\n\nGenerando resumen con IA...\n"); self.root.update_idletasks()
        prompt = generate_analysis_summary_prompt(self.last_analysis_full_results)
        if not prompt:
            messagebox.showerror("Error de IA", "No se pudo generar el prompt para el resumen."); self.results_text.insert(tk.END, "Error al crear prompt para IA.\n"); self.results_text.config(state="disabled"); return

        summary = generate_text_with_gemini(prompt, model_name="gemini-1.0-pro")
        if summary and not summary.startswith("Error:"):
            self.results_text.insert(tk.END, "\n--- Resumen generado por IA ---\n"); self.results_text.insert(tk.END, summary); self.results_text.insert(tk.END, "\n--- Fin del Resumen IA ---\n")
        else:
            self.results_text.insert(tk.END, f"\nNo se pudo generar el resumen con IA.\nRespuesta: {summary}\n"); messagebox.showwarning("Resumen con IA", f"No se pudo generar el resumen o hubo un error.\n{summary}")
        self.results_text.config(state="disabled")

    def export_to_dxf(self):
        if not self.last_analysis_full_results or \
           self.last_analysis_full_results.get("status") != "success" or \
           self.current_analysis_type != "static" or \
           "visualization_data" not in self.last_analysis_full_results:
            messagebox.showinfo("Exportar DXF", "No hay datos geométricos de un análisis estático exitoso para exportar.")
            return

        exports_dir = os.path.join(project_root_src_parent, 'exports')
        if not os.path.exists(exports_dir):
            try: os.makedirs(exports_dir)
            except Exception as e:
                messagebox.showerror("Error de Exportación", f"No se pudo crear el directorio de exportaciones: {exports_dir}\n{e}")
                return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dxf_filename = f"structural_model_{timestamp}.dxf"
        full_dxf_path = os.path.join(exports_dir, dxf_filename)

        self.results_text.config(state="normal")
        self.results_text.insert(tk.END, f"\n\nExportando modelo a DXF: {full_dxf_path}...")
        self.root.update_idletasks()

        # Pasar directamente self.last_analysis_full_results ya que contiene 'visualization_data'
        exported_path = export_model_to_dxf(self.last_analysis_full_results, output_filename=full_dxf_path)

        if exported_path:
            messagebox.showinfo("Exportación DXF Exitosa", f"Modelo exportado a:\n{exported_path}")
            self.results_text.insert(tk.END, f"\nModelo DXF exportado: {exported_path}")
        else:
            messagebox.showerror("Error de Exportación DXF", "No se pudo exportar el modelo a DXF.")
            self.results_text.insert(tk.END, "\nFallo al exportar a DXF.")

        self.results_text.config(state="disabled")

if __name__ == '__main__':
    main_window = tk.Tk()
    app = StructuralAnalysisGUI(main_window)
    main_window.mainloop()
```
