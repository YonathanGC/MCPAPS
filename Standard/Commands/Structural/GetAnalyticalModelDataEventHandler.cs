// Standard/Commands/Structural/GetAnalyticalModelDataEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class GetAnalyticalModelDataEventHandler : WaitableExternalEventHandlerBase<GetAnalyticalModelDataCommand>
    {
        public override string GetName() => "GetAnalyticalModelDataEventHandler";

        protected override void Execute(UIApplication app, GetAnalyticalModelDataCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JObject analyticalData = new JObject();
            JArray membersArray = new JArray();
            JArray panelsArray = new JArray();
            JArray nodesArray = new JArray();
            JArray loadsArray = new JArray();

            // To keep track of unique nodes already processed
            Dictionary<ElementId, JObject> processedNodes = new Dictionary<ElementId, JObject>();

            try
            {
                List<Element> elementsToProcess = new List<Element>();

                if (command.Scope == "element_ids")
                {
                    if (command.ElementIds == null || !command.ElementIds.Any())
                    {
                        result["success"] = false; result["message"] = "ElementIds must be provided for 'element_ids' scope.";
                        SetResult(result.ToString()); return;
                    }
                    foreach (string idStr in command.ElementIds)
                    {
                        ElementId eid;
                        try { eid = new ElementId(long.Parse(idStr)); }
                        catch { result["success"] = false; result["message"] = $"Invalid ElementId: {idStr}"; SetResult(result.ToString()); return; }
                        Element el = doc.GetElement(eid);
                        if (el != null) elementsToProcess.Add(el);
                    }
                }
                else // "full_model"
                {
                    // Collect all relevant analytical elements
                    elementsToProcess.AddRange(new FilteredElementCollector(doc).OfClass(typeof(AnalyticalMember)).ToElements());
                    elementsToProcess.AddRange(new FilteredElementCollector(doc).OfClass(typeof(AnalyticalPanel)).ToElements());
                    // Potentially add AnalyticalLink, AnalyticalNode if they are primary elements of interest
                }

                foreach (Element el in elementsToProcess)
                {
                    AnalyticalModel am = el.GetAnalyticalModel();
                    if (am == null) continue;

                    JObject amJson = new JObject();
                    amJson["original_element_id"] = el.Id.ToString();
                    amJson["analytical_element_id"] = am.Id.ToString();
                    amJson["type_name"] = am.GetType().Name; // "AnalyticalMember", "AnalyticalPanel", etc.

                    if (am is AnalyticalMember member)
                    {
                        amJson["structural_role"] = member.StructuralRole.ToString();
                        Curve curve = member.GetCurve();
                        if (curve != null)
                        {
                            amJson["start_point"] = new JObject { { "X", curve.GetEndPoint(0).X }, { "Y", curve.GetEndPoint(0).Y }, { "Z", curve.GetEndPoint(0).Z } };
                            amJson["end_point"] = new JObject { { "X", curve.GetEndPoint(1).X }, { "Y", curve.GetEndPoint(1).Y }, { "Z", curve.GetEndPoint(1).Z } };
                        }
                        // Section & Material - these might be on the physical element or analytical
                        Element physicalElement = doc.GetElement(member.GetElementId()); // Get physical element
                        if (physicalElement is FamilyInstance fi) {
                            amJson["section_name"] = fi.Symbol?.Name;
                            Parameter materialParam = fi.Symbol?.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM);
                            if (materialParam == null) materialParam = fi.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM); // Instance param
                             if (materialParam != null && materialParam.HasValue) {
                                Element materialEl = doc.GetElement(materialParam.AsElementId());
                                if (materialEl != null) amJson["material_name"] = materialEl.Name;
                            }
                        }


                        if (command.IncludeReleases)
                        {
                            JObject releases = new JObject();
                            bool sFx,sFy,sFz,sMx,sMy,sMz, eFx,eFy,eFz,eMx,eMy,eMz;
                            member.GetReleases(true, out sFx, out sFy, out sFz, out sMx, out sMy, out sMz);
                            member.GetReleases(false, out eFx, out eFy, out eFz, out eMx, out eMy, out eMz);
                            releases["start_Mx_released"] = sMx; releases["start_My_released"] = sMy; releases["start_Mz_released"] = sMz;
                            releases["end_Mx_released"] = eMx; releases["end_My_released"] = eMy; releases["end_Mz_released"] = eMz;
                            // Could add translational releases too if needed: sFx, eFx etc.
                            amJson["releases"] = releases;
                        }
                        membersArray.Add(amJson);
                    }
                    else if (am is AnalyticalPanel panel)
                    {
                        // Get boundary loops
                        IList<CurveLoop> loops = panel.GetLoops(AnalyticalLoopType.External);
                        if (loops != null && loops.Any())
                        {
                            JArray panelLoops = new JArray();
                            foreach(CurveLoop cl in loops)
                            {
                                JArray loopPoints = new JArray();
                                foreach(Curve c in cl) {
                                    loopPoints.Add(new JObject { { "X", c.GetEndPoint(0).X }, { "Y", c.GetEndPoint(0).Y }, { "Z", c.GetEndPoint(0).Z } });
                                }
                                // Add last point to close loop visually if not already included by Revit's CurveLoop iteration
                                if (cl.First() != null) loopPoints.Add(new JObject { { "X", cl.Last().GetEndPoint(1).X }, { "Y", cl.Last().GetEndPoint(1).Y }, { "Z", cl.Last().GetEndPoint(1).Z } });
                                panelLoops.Add(loopPoints);
                            }
                            amJson["boundary_loops"] = panelLoops;
                        }
                        panelsArray.Add(amJson);
                    }

                    // Common properties like Boundary Conditions & Loads
                    if (command.IncludeBoundaryConditions)
                    {
                        BoundaryConditions bc = am.GetBoundaryConditions();
                        if (bc != null) {
                            JObject bcJson = new JObject();
                            // Extract BC details - this can be verbose. Example:
                            bcJson["translation_x_type"] = bc.GetBoundaryConditionType(0,0).ToString(); // 0 for X, 0 for point
                            bcJson["translation_y_type"] = bc.GetBoundaryConditionType(0,1).ToString();
                            // ... and so on for all 6 DOFs and spring moduli if applicable.
                            amJson["boundary_conditions"] = bcJson; // Simplified for brevity
                        }
                    }

                    if (command.IncludeLoads)
                    {
                        foreach (ElementId loadId in am.GetLoads())
                        {
                            LoadBase load = doc.GetElement(loadId) as LoadBase;
                            if (load != null)
                            {
                                JObject loadJson = new JObject();
                                loadJson["load_id"] = load.Id.ToString();
                                loadJson["load_type"] = load.GetType().Name;
                                loadJson["host_analytical_element_id"] = am.Id.ToString();
                                if (load.LoadCaseId != null) loadJson["load_case_id"] = load.LoadCaseId.ToString();

                                if (load is PointLoad pl) {
                                    loadJson["force_vector"] = new JObject{ {"X",pl.ForceVector.X}, {"Y",pl.ForceVector.Y}, {"Z",pl.ForceVector.Z}};
                                    loadJson["moment_vector"] = new JObject{ {"X",pl.MomentVector.X}, {"Y",pl.MomentVector.Y}, {"Z",pl.MomentVector.Z}};
                                    loadJson["point_location"] = new JObject{ {"X",pl.Point.X}, {"Y",pl.Point.Y}, {"Z",pl.Point.Z}};
                                } else if (load is LineLoad ll) {
                                     // For LineLoad, getting detailed force vectors might require more specific API calls
                                     // This is a simplification
                                    loadJson["description"] = "LineLoad - detailed vector data requires specific API access";
                                } else if (load is AreaLoad al) {
                                    loadJson["force_vector_per_area"] = new JObject{ {"X",al.ForceVectorPerArea.X}, {"Y",al.ForceVectorPerArea.Y}, {"Z",al.ForceVectorPerArea.Z}};
                                }
                                loadsArray.Add(loadJson);
                            }
                        }
                    }
                }

                // Collect all unique nodes from analytical members (if not already primary elements)
                // This part can be enhanced to get all AnalyticalNode elements directly too.
                // For now, focusing on nodes derived from members.
                // This is a simplified node collection. A full structural model export would rigorously collect all nodes.


                analyticalData["members"] = membersArray;
                analyticalData["panels"] = panelsArray;
                // analyticalData["nodes"] = new JArray(processedNodes.Values.ToList()); // If nodes were collected
                analyticalData["loads"] = loadsArray;
                result["success"] = true;
                result["analytical_data"] = analyticalData;

            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting analytical model data: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
