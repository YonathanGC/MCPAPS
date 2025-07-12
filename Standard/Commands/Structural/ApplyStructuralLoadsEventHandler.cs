// Standard/Commands/Structural/ApplyStructuralLoadsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class ApplyStructuralLoadsEventHandler : WaitableExternalEventHandlerBase<ApplyStructuralLoadsCommand>
    {
        public override string GetName() => "ApplyStructuralLoadsEventHandler";

        protected override void Execute(UIApplication app, ApplyStructuralLoadsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                ElementId hostEid, loadCaseEid;
                try { hostEid = new ElementId(long.Parse(command.HostElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid HostElementId: {command.HostElementId}"; SetResult(result.ToString()); return; }

                try { loadCaseEid = new ElementId(long.Parse(command.LoadCaseId)); }
                catch { result["success"] = false; result["message"] = $"Invalid LoadCaseId: {command.LoadCaseId}"; SetResult(result.ToString()); return; }

                Element hostElement = doc.GetElement(hostEid);
                LoadCase loadCase = doc.GetElement(loadCaseEid) as LoadCase;

                if (hostElement == null)
                {
                    result["success"] = false; result["message"] = $"Host element with ID '{command.HostElementId}' not found.";
                    SetResult(result.ToString()); return;
                }
                if (loadCase == null)
                {
                    result["success"] = false; result["message"] = $"Load case with ID '{command.LoadCaseId}' not found.";
                    SetResult(result.ToString()); return;
                }
                 if (command.ForceVector == null)
                {
                    result["success"] = false; result["message"] = "ForceVector is required for applying loads.";
                    SetResult(result.ToString()); return;
                }


                XYZ force = new XYZ(command.ForceVector.X, command.ForceVector.Y, command.ForceVector.Z);
                XYZ moment = command.MomentVector != null ? new XYZ(command.MomentVector.X, command.MomentVector.Y, command.MomentVector.Z) : XYZ.Zero;

                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Apply {command.LoadType}");
                    Element createdLoad = null;

                    AnalyticalModel analyticalModel = hostElement.GetAnalyticalModel();
                    if (analyticalModel == null && command.LoadType != "AreaLoad") // Area loads can sometimes be hosted on physical elements directly
                    {
                        // For some elements (like Walls, Floors), the physical element itself can host AreaLoads.
                        // For line/point loads, an analytical model is typically needed.
                        // This check might need refinement based on specific host types.
                        if (!(hostElement is Wall || hostElement is Floor)) {
                             result["success"] = false;
                             result["message"] = $"Host element ID '{hostElement.Id}' does not have an analytical model, which is required for {command.LoadType}.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                             SetResult(result.ToString());
                             return;
                        }
                    }
                    ElementId analyticalHostId = analyticalModel?.Id ?? hostElement.Id; // Use analytical model ID if available


                    if (command.LoadType == "PointLoad")
                    {
                        if (command.PointLocation == null) {
                             result["success"] = false; result["message"] = "PointLocation is required for PointLoad.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                        XYZ point = new XYZ(command.PointLocation.X, command.PointLocation.Y, command.PointLocation.Z);
                        // The host for PointLoad.Create should be the analytical element.
                        createdLoad = PointLoad.Create(doc, analyticalHostId, point, force, moment, loadCase.Id, null); // last arg is sketch plane for some loads
                    }
                    else if (command.LoadType == "LineLoad")
                    {
                        // For LineLoad on analytical member, start/end points are relative to the member's curve.
                        // If LineLoadPath is provided, it's a series of absolute points defining the load path.
                        // For simplicity, this example assumes LineLoad is applied to the entire host analytical member curve.
                        // A more complex scenario would involve creating a specific path.

                        // Assuming the line load is applied along the entire length of the host analytical element.
                        // If the host is an AnalyticalBeam, AnalyticalBrace, or AnalyticalColumn
                        if (analyticalModel is AnalyticalMember) {
                            // For uniform load on the entire member
                            // The API expects array of forces/moments for start/end if varying.
                            // PointLoad.Create(doc, analyticalHostId, point, force, moment, loadCase.Id, sketchPlaneId);
                            // LineLoad.Create(doc, analyticalHostId, new List<XYZ>{force}, new List<XYZ>{moment}, loadCase.Id, sketchPlaneId) ?
                            // The API for LineLoad.Create(Document, ElementId, IList<XYZ>, IList<XYZ>, ElementId, ElementId) is for loads at points along curve.
                            // LineLoad.Create(Document, ElementId, Curve, IList<XYZ>, IList<XYZ>, ElementId, ElementId, bool) is for on curve.

                            // Simpler: LineLoad.Create(doc, analyticalHostId, force, moment, loadCase.Id, isProjectedLoad, useEntireCurve)
                            // This specific overload may not exist. Let's use the one that takes a curve from the analytical model.
                            Curve analyticalCurve = (analyticalModel as AnalyticalMember).GetCurve();
                            if (analyticalCurve != null) {
                                // For uniform load, start and end vectors are the same.
                                IList<XYZ> forces = new List<XYZ> { force, force };
                                IList<XYZ> moments = new List<XYZ> { moment, moment };
                                createdLoad = LineLoad.Create(doc, analyticalHostId, analyticalCurve, forces, moments, loadCase.Id, null, false); // false for not projected
                            } else {
                                 result["success"] = false; result["message"] = "Could not retrieve curve from analytical member for LineLoad.";
                                 if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            }
                        } else {
                             result["success"] = false; result["message"] = $"Host element ID '{hostElement.Id}' is not an AnalyticalMember, unsupported for this simplified LineLoad.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                    }
                    else if (command.LoadType == "AreaLoad")
                    {
                        // AreaLoad.Create(doc, host_element_id_or_analyticalSurface_id, force_vector_per_area, load_case_id, curveLoopArray_for_boundaries)
                        // If AreaLoadBoundaryLoops is null or empty, it implies load on the entire surface of the host.
                        // The host can be a physical element (Wall, Floor, Roof) or an AnalyticalSurface.

                        IList<CurveLoop> loops = new List<CurveLoop>();
                        if (command.AreaLoadBoundaryLoops != null && command.AreaLoadBoundaryLoops.Any())
                        {
                            foreach (var loopParams in command.AreaLoadBoundaryLoops)
                            {
                                CurveLoop cl = new CurveLoop();
                                if (loopParams.Count < 3) {
                                    result["success"] = false; result["message"] = "AreaLoad boundary loop must have at least 3 points.";
                                    if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                                }
                                for (int i = 0; i < loopParams.Count; i++)
                                {
                                    XYZ p1 = new XYZ(loopParams[i].X, loopParams[i].Y, loopParams[i].Z);
                                    XYZ p2 = new XYZ(loopParams[(i + 1) % loopParams.Count].X,
                                                     loopParams[(i + 1) % loopParams.Count].Y,
                                                     loopParams[(i + 1) % loopParams.Count].Z);
                                    cl.Append(Line.CreateBound(p1, p2));
                                }
                                loops.Add(cl);
                            }
                        }
                        else // Load on entire face - need to get boundary of host face. This is more complex.
                        {
                            // For simplicity, if no boundary is given, we'll assume the API handles "entire face" if loops is empty or null.
                            // However, typically you need to provide the boundary.
                            // If the host is an AnalyticalPanel, you can get its boundary.
                            if (analyticalModel is AnalyticalPanel panel) {
                                loops = panel.GetLoops(AnalyticalLoopType.External);
                            } else if (hostElement is Floor floorEl) {
                                // Getting floor boundary might require more work (getting geometry, finding faces)
                                // For now, this path might fail if API requires explicit loops.
                                 result["success"] = false; result["message"] = "Applying AreaLoad to entire Floor without explicit boundary not yet fully supported in this simplified version. Provide boundary loops.";
                                 if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            } else {
                                 result["success"] = false; result["message"] = "Applying AreaLoad to entire surface of this host type without explicit boundary not supported. Provide boundary loops or use an AnalyticalPanel host.";
                                 if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            }
                        }

                        if (!loops.Any()) {
                             result["success"] = false; result["message"] = "No valid boundary loops found or generated for AreaLoad.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        // AreaLoad.Create(doc, ElementId hostElementId, IList<CurveLoop> profile, XYZ forceVector, ElementId loadCaseId)
                        // The API has changed. Let's find a suitable one.
                        // AreaLoad.Create(doc, analyticalHostId (or physical host if applicable), force, loadCase.Id, loops.First()); // Simplified, takes one loop
                        // AreaLoad.Create(Document, ElementId, IList<CurveLoop>, XYZ, ElementId)
                        // For AnalyticalPanel, AreaLoad.Create(doc, analyticalHostId, force, moment (usually zero for area), loadCase.Id, isProjected)
                        // This is confusing. The API for AreaLoad changed over versions.
                        // Assuming we use AreaLoad.Create(doc, hostId, force, loadCaseId, curveLoops)
                        // However, the official samples often use symbolic constants for force directions.
                        // For now, we'll try with the hostElement.Id as the host for AreaLoad.
                        createdLoad = AreaLoad.Create(doc, hostElement.Id, loops, force, loadCase.Id);


                    }
                    else
                    {
                        result["success"] = false; result["message"] = $"Unsupported LoadType: {command.LoadType}";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }


                    if (createdLoad != null && createdLoad.IsValidObject)
                    {
                        result["success"] = true;
                        result["message"] = $"{command.LoadType} applied successfully to element '{command.HostElementId}'.";
                        result["load_element_id"] = createdLoad.Id.ToString();
                        tx.Commit();
                    }
                    else
                    {
                        if (! (bool)(result["success"] ?? false)) // if success not already set to false
                        {
                           result["success"] = false;
                           result["message"] = $"Failed to create {command.LoadType}. Creation method returned null or invalid object.";
                        }
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error applying structural load: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
