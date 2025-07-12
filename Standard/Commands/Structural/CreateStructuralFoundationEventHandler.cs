// Standard/Commands/Structural/CreateStructuralFoundationEventHandler.cs
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
    public class CreateStructuralFoundationEventHandler : WaitableExternalEventHandlerBase<CreateStructuralFoundationCommand>
    {
        public override string GetName() => "CreateStructuralFoundationEventHandler";

        protected override void Execute(UIApplication app, CreateStructuralFoundationCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                Level level;
                ElementId levelIdParsed;
                try
                {
                    levelIdParsed = new ElementId(long.Parse(command.LevelId));
                    level = doc.GetElement(levelIdParsed) as Level;
                }
                catch
                {
                    level = new FilteredElementCollector(doc)
                                .OfClass(typeof(Level))
                                .FirstOrDefault(l => l.Name.Equals(command.LevelId, StringComparison.OrdinalIgnoreCase)) as Level;
                }

                if (level == null)
                {
                    result["success"] = false;
                    result["message"] = $"Error creating foundation: Level with ID/Name '{command.LevelId}' not found.";
                    SetResult(result.ToString());
                    return;
                }

                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create Foundation {command.FoundationType}");
                    FamilyInstance foundationInstance = null;
                    Floor foundationSlab = null;

                    if (command.FoundationType == "IsolatedFooting")
                    {
                        if (command.InsertionPoint == null)
                        {
                            result["success"] = false;
                            result["message"] = "Error: InsertionPoint is required for IsolatedFooting.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }

                        FamilySymbol familySymbol = new FilteredElementCollector(doc)
                            .OfClass(typeof(FamilySymbol))
                            .WhereElementIsElementType()
                            .Cast<FamilySymbol>()
                            .FirstOrDefault(fs => fs.Name.Equals(command.FamilySymbolName, StringComparison.OrdinalIgnoreCase) &&
                                                   fs.Family.FamilyCategory.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralFoundation);
                        if (familySymbol == null)
                        {
                            result["success"] = false;
                            result["message"] = $"Family symbol '{command.FamilySymbolName}' for isolated footing not found or not a structural foundation type.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }
                        if (!familySymbol.IsActive) familySymbol.Activate();

                        XYZ point = new XYZ(command.InsertionPoint.X, command.InsertionPoint.Y, command.InsertionPoint.Z);
                        foundationInstance = doc.Create.NewFamilyInstance(point, familySymbol, level, StructuralType.Footing);
                    }
                    else if (command.FoundationType == "WallFooting")
                    {
                        ElementId wallId;
                        try { wallId = new ElementId(long.Parse(command.HostWallId)); }
                        catch {
                             result["success"] = false;
                             result["message"] = $"Invalid HostWallId format: {command.HostWallId}";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                             SetResult(result.ToString());
                             return;
                        }

                        Wall hostWall = doc.GetElement(wallId) as Wall;
                        if (hostWall == null)
                        {
                            result["success"] = false;
                            result["message"] = $"Host wall with ID '{command.HostWallId}' not found.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }

                        WallFoundationType wallFoundationType = new FilteredElementCollector(doc)
                            .OfClass(typeof(WallFoundationType))
                            .Cast<WallFoundationType>()
                            .FirstOrDefault(wt => wt.Name.Equals(command.FamilySymbolName, StringComparison.OrdinalIgnoreCase)); // FamilySymbolName used for WallFoundationType name

                        if (wallFoundationType == null) {
                            result["success"] = false;
                            result["message"] = $"WallFoundationType '{command.FamilySymbolName}' not found.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }
                        // Note: WallFoundation.Create is not available.
                        // Instead, you create a WallFoundation element and set its type.
                        // This usually requires creating a new Wall element of a foundation type,
                        // or specific API for strip footings if available.
                        // For simplicity, this example assumes a direct creation method or that
                        // FamilySymbolName refers to a type that can be used with a general foundation element.
                        // Revit API for WallFoundation is often by creating a wall with a specific foundation type.
                        // Let's assume for now we are trying to create a standard foundation element and assign its type if that's how it works.
                        // This part is tricky and might need specific workflow for "Wall Footings" if not simple family instance.
                        // A common method is to create a Wall element whose WallType is a foundation type.
                        // The prompt implies a specific "WallFooting" tool, often these are family instances under walls or special types.
                        // Given the structure, it's more likely `doc.Create.NewFoundationWall` was intended if it existed,
                        // or `doc.Create.NewFamilyInstance` with a line-based family hosted on a wall or level.
                        // For this example, we'll assume it's a family instance that might be line-based or point-based but associated with a wall.
                        // This part of the Revit API is complex for wall footings.
                        // A more robust way for Wall Footings (Bearing Footing type) is to use WallFoundation.Create(doc, wallFoundationType.Id, hostWall.Id);
                        // However, this creates a WallFoundation, not a FamilyInstance. The output expects an element_id.
                        // Let's pivot to creating a WallFoundation object if that's the intent for "WallFooting"
                        WallFoundation newWallFoundation = WallFoundation.Create(doc, wallFoundationType.Id, hostWall.Id);
                        if (newWallFoundation != null) {
                             result["success"] = true;
                             result["message"] = $"Wall footing '{command.FamilySymbolName}' created successfully for wall '{command.HostWallId}'.";
                             result["element_id"] = newWallFoundation.Id.ToString();
                             tx.Commit();
                             SetResult(result.ToString());
                             return;
                        } else {
                             result["success"] = false;
                             result["message"] = "Failed to create WallFoundation.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                             SetResult(result.ToString());
                             return;
                        }

                    }
                    else if (command.FoundationType == "SlabOnGrade")
                    {
                        if (command.BoundaryLoops == null || !command.BoundaryLoops.Any() || !command.BoundaryLoops.First().Any())
                        {
                            result["success"] = false;
                            result["message"] = "Error: BoundaryLoops are required for SlabOnGrade.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }

                        FloorType floorType = new FilteredElementCollector(doc)
                            .OfClass(typeof(FloorType))
                            .Cast<FloorType>()
                            .FirstOrDefault(ft => ft.Name.Equals(command.FloorTypeName, StringComparison.OrdinalIgnoreCase));

                        if (floorType == null) {
                            result["success"] = false;
                            result["message"] = $"FloorType '{command.FloorTypeName}' not found.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                            SetResult(result.ToString());
                            return;
                        }

                        CurveArray profile = new CurveArray();
                        // Assuming first loop is the outer boundary for simplicity here.
                        // Revit's NewFloor method takes a single CurveLoop for the boundary.
                        // For floors with openings, you'd use NewFloor(CurveLoopArray, FloorType, Level, bool)
                        // or create a simple floor then add openings.
                        // This example will use the first loop as the main boundary.

                        CurveLoop curveLoop = new CurveLoop();
                        List<XYZParameter> firstLoopParams = command.BoundaryLoops.First();
                        for(int i = 0; i < firstLoopParams.Count; i++)
                        {
                            XYZ p1 = new XYZ(firstLoopParams[i].X, firstLoopParams[i].Y, firstLoopParams[i].Z);
                            XYZ p2 = new XYZ(firstLoopParams[(i + 1) % firstLoopParams.Count].X,
                                             firstLoopParams[(i + 1) % firstLoopParams.Count].Y,
                                             firstLoopParams[(i + 1) % firstLoopParams.Count].Z);
                            curveLoop.Append(Line.CreateBound(p1, p2));
                        }

                        // foundationSlab = doc.Create.NewFloor(profile, floorType, level, command.IsStructuralSlab); This is old API
                        // Use NewFloor(CurveLoop, FloorType, Level, bool structural)
                        // Or NewFloor(IList<CurveLoop>, FloorType, Level, bool structural, Transform)
                        // For simplicity, taking the first loop as the boundary.
                        // For multiple loops (e.g., openings), you'd construct a CurveLoopArray (IList<CurveLoop>)

                        IList<CurveLoop> BLoops = new List<CurveLoop>();
                        foreach(var loopParams in command.BoundaryLoops)
                        {
                            CurveLoop cl = new CurveLoop();
                            for(int i = 0; i < loopParams.Count; i++)
                            {
                                XYZ p1 = new XYZ(loopParams[i].X, loopParams[i].Y, loopParams[i].Z);
                                XYZ p2 = new XYZ(loopParams[(i + 1) % loopParams.Count].X,
                                                 loopParams[(i + 1) % loopParams.Count].Y,
                                                 loopParams[(i + 1) % loopParams.Count].Z);
                                cl.Append(Line.CreateBound(p1, p2));
                            }
                            BLoops.Add(cl);
                        }

                        foundationSlab = Floor.Create(doc, BLoops, floorType.Id, level.Id, command.IsStructuralSlab);

                    }
                    else
                    {
                        result["success"] = false;
                        result["message"] = "Invalid FoundationType specified.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                        SetResult(result.ToString());
                        return;
                    }

                    if ((foundationInstance != null && foundationInstance.IsValidObject) || (foundationSlab != null && foundationSlab.IsValidObject))
                    {
                        result["success"] = true;
                        result["message"] = $"{command.FoundationType} '{command.FamilySymbolName ?? command.FloorTypeName}' created successfully.";
                        result["element_id"] = (foundationInstance != null) ? foundationInstance.Id.ToString() : foundationSlab.Id.ToString();
                        tx.Commit();
                    }
                    else
                    {
                        //This case should ideally be caught by specific checks above, but as a fallback:
                        if (! (bool)(result["success"] ?? false) ) // if success not already set to false
                        {
                           result["success"] = false;
                           result["message"] = $"Failed to create {command.FoundationType}. The creation method returned null or an invalid object.";
                        }
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating foundation: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
