// Standard/Commands/Generic/CreateFloorFromBoundaryEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter
using System;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class CreateFloorFromBoundaryEventHandler : WaitableExternalEventHandlerBase<CreateFloorFromBoundaryCommand>
    {
        public override string GetName() => "CreateFloorFromBoundaryEventHandler";

        protected override void Execute(UIApplication app, CreateFloorFromBoundaryCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (string.IsNullOrEmpty(command.FloorTypeName) || string.IsNullOrEmpty(command.LevelId) ||
                    command.BoundaryLoops == null || !command.BoundaryLoops.Any() || !command.BoundaryLoops.First().Any())
                {
                    result["success"] = false;
                    result["message"] = "FloorTypeName, LevelId, and at least one valid BoundaryLoop (exterior) are required.";
                    SetResult(result.ToString());
                    return;
                }

                FloorType floorType = new FilteredElementCollector(doc)
                    .OfClass(typeof(FloorType))
                    .Cast<FloorType>()
                    .FirstOrDefault(ft => ft.Name.Equals(command.FloorTypeName, StringComparison.OrdinalIgnoreCase));

                if (floorType == null)
                {
                    result["success"] = false; result["message"] = $"FloorType '{command.FloorTypeName}' not found.";
                    SetResult(result.ToString()); return;
                }

                Level level;
                ElementId levelEid;
                try { levelEid = new ElementId(long.Parse(command.LevelId)); }
                catch { result["success"] = false; result["message"] = $"Invalid LevelId: {command.LevelId}"; SetResult(result.ToString()); return; }
                level = doc.GetElement(levelEid) as Level;

                if (level == null)
                {
                    result["success"] = false; result["message"] = $"Level with ID '{command.LevelId}' not found.";
                    SetResult(result.ToString()); return;
                }

                IList<CurveLoop> profileLoops = new List<CurveLoop>();
                foreach (var pointLoop in command.BoundaryLoops)
                {
                    if (pointLoop.Count < 3)
                    {
                        result["success"] = false; result["message"] = "Each boundary loop must contain at least 3 points.";
                        SetResult(result.ToString()); return;
                    }
                    CurveLoop curveLoop = new CurveLoop();
                    for (int i = 0; i < pointLoop.Count; i++)
                    {
                        XYZ p1 = new XYZ(pointLoop[i].X, pointLoop[i].Y, pointLoop[i].Z);
                        // Z-coordinate of points will be used as is. If floor is to be on level elevation, Z should match level.Elevation + offset.
                        // Or, ensure points are planar and Revit places it on the level.
                        // For simplicity, we assume Z coordinates are correctly set for the desired plane.
                        XYZ p2 = new XYZ(pointLoop[(i + 1) % pointLoop.Count].X,
                                         pointLoop[(i + 1) % pointLoop.Count].Y,
                                         pointLoop[(i + 1) % pointLoop.Count].Z);
                        if (p1.IsAlmostEqualTo(p2)) continue;
                        curveLoop.Append(Line.CreateBound(p1, p2));
                    }
                    if (!curveLoop.IsOpen()) // Ensure it's closed, though CreateBound should handle pairs.
                    {
                         profileLoops.Add(curveLoop);
                    } else {
                        result["success"] = false; result["message"] = "One of the boundary loops is not closed.";
                        SetResult(result.ToString()); return;
                    }
                }

                if (!profileLoops.Any()) {
                     result["success"] = false; result["message"] = "No valid boundary loops provided or created.";
                     SetResult(result.ToString()); return;
                }


                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create Floor: {command.FloorTypeName}");

                    // Floor.Create(Document document, IList<CurveLoop> profile, ElementId floorTypeId, ElementId levelId, bool structural, Transform slabShapeEditUtil)
                    // The Transform is for slab shape editor, can be null or Identity if not used.
                    // Note: The points in boundary_loops should define a planar profile at the desired elevation (level.Elevation + offset)
                    // Revit's Floor.Create will use the Z of the first point of the first curve of the first loop to determine the plane if not perfectly on level.
                    // It's safer if the Z coordinates of all points in boundary_loops are already adjusted for the offset.

                    Floor newFloor = Floor.Create(doc, profileLoops, floorType.Id, level.Id, command.IsStructural);

                    if (newFloor == null)
                    {
                        result["success"] = false; result["message"] = "Failed to create floor. Floor.Create returned null.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                        SetResult(result.ToString()); return;
                    }

                    // Apply offset if specified and non-zero
                    if (Math.Abs(command.OffsetFromLevel) > 1e-6) // Tolerance for double comparison
                    {
                        Parameter offsetParam = newFloor.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM);
                        if (offsetParam != null && !offsetParam.IsReadOnly)
                        {
                            offsetParam.Set(command.OffsetFromLevel);
                        }
                        else
                        {
                            // Log or add to message that offset could not be set directly
                            // result["warning"] = "Could not set OffsetFromLevel directly via parameter.";
                        }
                    }

                    result["success"] = true;
                    result["message"] = $"Floor '{command.FloorTypeName}' created successfully.";
                    result["element_id"] = newFloor.Id.ToString();
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                // Revit API can throw specific exceptions for invalid profiles (e.g., self-intersecting)
                // Autodesk.Revit.Exceptions.InvalidOperationException for "Curve loop is not closed or not planar"
                result["message"] = $"Error creating floor: {ex.Message}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
