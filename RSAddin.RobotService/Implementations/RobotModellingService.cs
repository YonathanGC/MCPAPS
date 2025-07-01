using RSAddin.Core.Models;
using RSAddin.Core.Services.Interfaces;
using RobotOM;
using System;
using System.Diagnostics; // Para Debug.WriteLine

namespace RSAddin.RobotService.Implementations
{
    public class RobotModellingService : IRobotModellingService
    {
        public bool CreateSimpleBeam(BeamInputParameters parameters)
        {
            IRobotApplication? robot = RobotConnectionManager.GetRobotApplication();
            if (robot == null)
            {
                Debug.WriteLine("Error: No se pudo conectar a Robot.");
                return false;
            }

            try
            {
                robot.Project.New(IProjectType.I_PT_FRAME_3D); // Iniciar un nuevo proyecto 3D Frame si no hay uno

                IRobotStructure str = robot.Project.Structure;
                IRobotNodeCollection nodes = str.Nodes;
                IRobotBarCollection bars = str.Bars;
                IRobotLabelCollection sections = str.Labels.CreateMany(IRobotLabelType.I_LT_BAR_SECTION);
                IRobotCaseCollection cases = str.Cases;
                IRobotLoadRecordCollection loads = str.Records;

                // Limpiar estructura (opcional, para pruebas)
                // str.Nodes.DeleteAll();
                // str.Bars.DeleteAll();
                // str.Cases.DeleteAll();


                // 1. Crear Nodos
                int startNodeId = nodes.FreeNumber;
                nodes.Create(startNodeId, parameters.StartNode.X, parameters.StartNode.Y, parameters.StartNode.Z);
                int endNodeId = nodes.FreeNumber;
                nodes.Create(endNodeId, parameters.EndNode.X, parameters.EndNode.Y, parameters.EndNode.Z);
                Debug.WriteLine($"Nodos creados: {startNodeId}, {endNodeId}");

                // 2. Crear/Obtener Sección
                IRobotBarSectionData? sectionData = robot.Project.Structure.Labels.Get(IRobotLabelType.I_LT_BAR_SECTION, parameters.SectionName) as IRobotBarSectionData;
                if (sectionData == null)
                {
                    // La sección no existe, intentar crearla/cargarla desde la base de datos de secciones de Robot
                    IRobotLabelServer? labelServer = robot.Project.Structure.Labels.Server;
                    if (labelServer != null)
                    {
                        // Esto asume que es un nombre de sección estándar que Robot puede encontrar en sus bases de datos.
                        // Por ejemplo, "IPE 200", "HEB 300", etc.
                        labelServer.Create(IRobotLabelType.I_LT_BAR_SECTION, parameters.SectionName);
                        sectionData = robot.Project.Structure.Labels.Get(IRobotLabelType.I_LT_BAR_SECTION, parameters.SectionName) as IRobotBarSectionData;
                    }
                }

                if (sectionData == null)
                {
                    Debug.WriteLine($"Error: No se pudo crear o encontrar la sección '{parameters.SectionName}'. Verifique que el nombre sea correcto y exista en las bases de datos de secciones de Robot (ej. 'IPE 200').");
                    return false;
                }
                // Asignar material (opcional si la sección ya lo tiene definido por defecto)
                // sectionData.MaterialName = "Steel"; // O el material que corresponda
                Debug.WriteLine($"Sección '{parameters.SectionName}' lista/creada.");


                // 3. Crear Barra
                int barId = bars.FreeNumber;
                IRobotBar bar = bars.Create(barId, startNodeId, endNodeId);
                bar.SetLabel(IRobotLabelType.I_LT_BAR_SECTION, parameters.SectionName);
                Debug.WriteLine($"Barra creada: {barId}");

                // 4. Crear Apoyos
                IRobotNode startNode = nodes.Get(startNodeId) as IRobotNode;
                if (parameters.SupportStartNodeFixed)
                {
                    startNode.SetFixed(true, true, true, true, true, true); // UX,UY,UZ, RX,RY,RZ
                    Debug.WriteLine($"Apoyo fijo en nodo {startNodeId}");
                }

                IRobotNode endNode = nodes.Get(endNodeId) as IRobotNode;
                if (parameters.SupportEndNodeFixed)
                {
                     endNode.SetFixed(true, true, true, true, true, true);
                     Debug.WriteLine($"Apoyo fijo en nodo {endNodeId}");
                }
                else
                {
                    endNode.SetSupport(true, false, true, false, false, false); // UX, UY(libre), UZ, RX(libre), RY(libre), RZ(libre)
                    Debug.WriteLine($"Apoyo simple (UX, UZ) en nodo {endNodeId}");
                }


                // 5. Crear Caso de Carga
                short caseNumber;
                string caseName = parameters.LoadCaseForPointLoad.ToString();
                try
                {
                    IRobotCase? existingCase = cases.Get(caseName) as IRobotCase;
                    if (existingCase != null)
                    {
                        caseNumber = (short)existingCase.Number;
                    }
                    else
                    {
                        throw new Exception("Caso no existe, crear nuevo");
                    }
                }
                catch
                {
                    caseNumber = (short)cases.FreeNumber;
                    IRobotCaseAnalysisType caseType = (parameters.LoadCaseForPointLoad == LoadCaseType.Dead) ?
                                                       IRobotCaseAnalysisType.I_CAT_STATIC_LINEAR :
                                                       IRobotCaseAnalysisType.I_CAT_STATIC_LINEAR; // Simplificado
                    cases.Create(caseNumber, caseName, caseType);
                }
                Debug.WriteLine($"Caso de carga '{caseName}' (Número: {caseNumber}) listo.");

                // 6. Crear Carga Puntual en la Barra (en el centro)
                IRobotLoadRecordPntForce record = loads.CreateBarForce(barId, caseNumber, IRobotLoadSubtype.I_LST_BAR_PNT_FORCE, false) as IRobotLoadRecordPntForce;
                if (record != null)
                {
                    record.FZ = parameters.PointLoadValue;
                    record.X = 0.5;
                    record.IsRelative = true;
                    loads.Apply(record);
                    Debug.WriteLine($"Carga puntual aplicada en barra {barId}, caso {caseNumber}");
                }
                else
                {
                     Debug.WriteLine($"Error al crear el registro de carga puntual en barra.");
                }


                robot.Project.ViewMngr.Refresh();
                Debug.WriteLine("Modelo de viga simple creado exitosamente.");
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error creando modelo en Robot: {ex.Message}\n{ex.StackTrace}");
                return false;
            }
        }
    }
}
