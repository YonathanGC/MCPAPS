using RSAddin.Core.Services.Interfaces;
using RobotOM;
using System;
using System.Diagnostics;

namespace RSAddin.RobotService.Implementations
{
    public class RobotAnalysisService : IRobotAnalysisService
    {
        public bool RunAnalysis()
        {
            IRobotApplication? robot = RobotConnectionManager.GetRobotApplication();
            if (robot == null)
            {
                 Debug.WriteLine("Error: No se pudo conectar a Robot para análisis.");
                return false;
            }

            try
            {
                if (robot.Project.Structure.Nodes.Count == 0)
                {
                    Debug.WriteLine("No hay modelo para analizar.");
                    return false;
                }
                Debug.WriteLine("Iniciando análisis...");
                robot.Project.CalcEngine.Calculate();
                Debug.WriteLine("Análisis completado.");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error durante el análisis en Robot: {ex.Message}");
                return false;
            }
        }

        public string GetSimpleBeamMidPointDeflection(int barNumber, int loadCaseNumber)
        {
            IRobotApplication? robot = RobotConnectionManager.GetRobotApplication();
            if (robot == null) return "Error: Robot no conectado.";

            try
            {
                IRobotStructure str = robot.Project.Structure;
                if (str.Bars.Get(barNumber) == null) return $"Error: Barra {barNumber} no encontrada.";
                if (str.Cases.Get(loadCaseNumber) == null) return $"Error: Caso {loadCaseNumber} no encontrado.";


                if (str.Results.Available != 1)
                {
                    return "Resultados no disponibles. Ejecute el análisis primero.";
                }


                IRobotBar bar = str.Bars.Get(barNumber) as IRobotBar;
                if (bar == null) return "Barra no encontrada";

                IRobotResultServer? resultsServer = robot.Project.Structure.Results.Server;
                if (resultsServer == null) return "Servidor de resultados no disponible.";

                int endNodeId = bar.EndNode; // Simplificación: tomamos el nodo final
                // En un caso real, se buscaría el nodo central o se interpolaría.

                RobotSelection sel = robot.CmpntFactory.Create(IRobotComponentType.I_CT_SELECTION) as RobotSelection;
                sel.Clear();
                sel.AddOne(endNodeId, IRobotObjectType.I_OT_NODE);

                RobotResultsParams resParams = robot.CmpntFactory.Create(IRobotComponentType.I_CT_RES_PARAMS) as RobotResultsParams;
                resParams.Cases = loadCaseNumber.ToString();
                resParams.Selection.Set(IRobotObjectType.I_OT_NODE, sel);

                IRobotNumericalResultValue resValue = resultsServer.GetResult(IRobotNumericalResultType.I_NRT_DISPLACEMENT_NODAL_DEFORMATIONS,
                                                                          (int)IRobotNodalDeformationType.I_NDT_D_UZ,
                                                                          resParams) as IRobotNumericalResultValue;

                if (resValue != null && resValue.ValueCount > 0)
                {
                    double deflectionMeters = resValue.GetValue(0, 0);
                    double deflectionMm = deflectionMeters * 1000.0;
                    return $"Deflexión UZ en nodo {endNodeId} (extremo de barra {barNumber}), caso {loadCaseNumber}: {deflectionMm:F2} mm";
                }
                else
                {
                    return $"No se pudo obtener la deflexión para el nodo {endNodeId}, barra {barNumber}, caso {loadCaseNumber}.";
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error obteniendo resultados de Robot: {ex.Message}\n{ex.StackTrace}");
                return $"Error: {ex.Message}";
            }
        }
    }
}
