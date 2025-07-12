// Standard/Commands/Generic/CreateWallAlongCurveEventHandler.cs
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
    public class CreateWallAlongCurveEventHandler : WaitableExternalEventHandlerBase<CreateWallAlongCurveCommand>
    {
        public override string GetName() => "CreateWallAlongCurveEventHandler";

        private WallLocationLine GetWallLocationLineEnum(string locationLineName)
        {
            if (string.IsNullOrEmpty(locationLineName)) return WallLocationLine.WallCenterline; // Default
            if (Enum.TryParse<WallLocationLine>(locationLineName, true, out WallLocationLine wll)) return wll;

            // Fallback for common variations if direct enum parse fails
            switch(locationLineName.ToLowerInvariant())
            {
                case "wallcenterline": case "wall centerline": return WallLocationLine.WallCenterline;
                case "corecenterline": case "core centerline": return WallLocationLine.CoreCenterline;
                case "finishfaceexterior": case "finish face exterior": return WallLocationLine.FinishFaceExterior;
                case "finishfaceinterior": case "finish face interior": return WallLocationLine.FinishFaceInterior;
                case "coreexterior": case "core exterior": return WallLocationLine.CoreExterior;
                case "coreinterior": case "core interior": return WallLocationLine.CoreInterior;
                default: return WallLocationLine.WallCenterline; // Default or throw error
            }
        }

        protected override void Execute(UIApplication app, CreateWallAlongCurveCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JArray createdWallIds = new JArray();

            try
            {
                if (string.IsNullOrEmpty(command.WallTypeName) || string.IsNullOrEmpty(command.LevelId) || command.PathPoints == null || command.PathPoints.Count < 2)
                {
                    result["success"] = false; result["message"] = "WallTypeName, LevelId, and at least two PathPoints are required.";
                    SetResult(result.ToString()); return;
                }
                if (command.Height <= 0) {
                    result["success"] = false; result["message"] = "Height must be a positive value.";
                    SetResult(result.ToString()); return;
                }


                WallType wallType = new FilteredElementCollector(doc)
                    .OfClass(typeof(WallType))
                    .Cast<WallType>()
                    .FirstOrDefault(wt => wt.Name.Equals(command.WallTypeName, StringComparison.OrdinalIgnoreCase));

                if (wallType == null)
                {
                    result["success"] = false; result["message"] = $"WallType '{command.WallTypeName}' not found.";
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

                WallLocationLine locLineEnum = GetWallLocationLineEnum(command.LocationLine);

                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create Wall: {command.WallTypeName}");

                    List<Curve> curves = new List<Curve>();
                    for (int i = 0; i < command.PathPoints.Count - 1; i++)
                    {
                        XYZ p1 = new XYZ(command.PathPoints[i].X, command.PathPoints[i].Y, command.PathPoints[i].Z);
                        XYZ p2 = new XYZ(command.PathPoints[i+1].X, command.PathPoints[i+1].Y, command.PathPoints[i+1].Z);
                        if (p1.IsAlmostEqualTo(p2)) continue; // Skip zero-length segments
                        curves.Add(Line.CreateBound(p1, p2));
                    }

                    if (!curves.Any()) {
                        result["success"] = false; result["message"] = "No valid curve segments created from PathPoints.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                        SetResult(result.ToString()); return;
                    }

                    // Create walls segment by segment to allow individual parameter setting if needed,
                    // or use Wall.Create(doc, List<Curve>, ...) if available and suitable for chained walls.
                    // For simplicity and control, creating one by one:
                    foreach (Curve curveSegment in curves)
                    {
                        // Wall.Create(Document document, Curve curve, ElementId wallTypeId, ElementId levelId, double height, double offset, bool flip, bool structural)
                        Wall newWall = Wall.Create(doc, curveSegment, wallType.Id, level.Id, command.Height, command.BaseOffset, false, command.IsStructural);

                        if (newWall == null)
                        {
                            result["success"] = false; result["message"] = "Failed to create one or more wall segments.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); // Rollback all if any segment fails
                            SetResult(result.ToString()); return;
                        }

                        // Set Location Line if not default or if Wall.Create doesn't take it directly
                        // The LocationLine parameter is (BuiltInParameter.WALL_KEY_REF_PARAM) and is an integer.
                        Parameter locLineParam = newWall.get_Parameter(BuiltInParameter.WALL_KEY_REF_PARAM);
                        if (locLineParam != null && !locLineParam.IsReadOnly)
                        {
                            locLineParam.Set((int)locLineEnum);
                        }
                        createdWallIds.Add(newWall.Id.ToString());
                    }

                    result["success"] = true;
                    result["message"] = $"Wall(s) created successfully using type '{command.WallTypeName}'.";
                    result["element_ids"] = createdWallIds;
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating wall: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
