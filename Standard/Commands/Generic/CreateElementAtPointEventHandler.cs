// Standard/Commands/Generic/CreateElementAtPointEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure; // For StructuralType enum
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter
using System;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class CreateElementAtPointEventHandler : WaitableExternalEventHandlerBase<CreateElementAtPointCommand>
    {
        public override string GetName() => "CreateElementAtPointEventHandler";

        protected override void Execute(UIApplication app, CreateElementAtPointCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (string.IsNullOrEmpty(command.FamilyName) || string.IsNullOrEmpty(command.TypeName) || command.InsertionPoint == null || string.IsNullOrEmpty(command.LevelId))
                {
                    result["success"] = false; result["message"] = "FamilyName, TypeName, InsertionPoint, and LevelId are required.";
                    SetResult(result.ToString()); return;
                }

                FamilySymbol familySymbol = new FilteredElementCollector(doc)
                    .OfClass(typeof(FamilySymbol))
                    .WhereElementIsElementType()
                    .Cast<FamilySymbol>()
                    .FirstOrDefault(fs => fs.Family.Name.Equals(command.FamilyName, StringComparison.OrdinalIgnoreCase) &&
                                           fs.Name.Equals(command.TypeName, StringComparison.OrdinalIgnoreCase));

                if (familySymbol == null)
                {
                    result["success"] = false; result["message"] = $"FamilySymbol '{command.FamilyName} : {command.TypeName}' not found.";
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

                XYZ point = new XYZ(command.InsertionPoint.X, command.InsertionPoint.Y, command.InsertionPoint.Z);

                StructuralType structuralTypeEnum = StructuralType.NonStructural; // Default
                if (!string.IsNullOrEmpty(command.StructuralTypeName))
                {
                    if (!Enum.TryParse<StructuralType>(command.StructuralTypeName, true, out structuralTypeEnum))
                    {
                        // Log warning or error if desired, for now, defaults to NonStructural if parse fails
                        // For a stricter approach:
                        // result["success"] = false; result["message"] = $"Invalid StructuralTypeName: {command.StructuralTypeName}";
                        // SetResult(result.ToString()); return;
                        structuralTypeEnum = StructuralType.NonStructural;
                    }
                }


                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create Element at Point: {command.TypeName}");

                    if (!familySymbol.IsActive)
                    {
                        familySymbol.Activate();
                        doc.Regenerate(); // Important after activating
                    }

                    // NewFamilyInstance(XYZ location, FamilySymbol symbol, Element host, Level level, StructuralType structuralType)
                    // For non-hosted, point-based families, host is often null, level provides context.
                    // However, the API often prefers NewFamilyInstance(location, symbol, level, structuralType)
                    // or NewFamilyInstance(location, symbol, host, structuralType) for hosted.
                    // Let's try with level.
                    FamilyInstance instance = doc.Create.NewFamilyInstance(point, familySymbol, level, structuralTypeEnum);

                    if (instance == null)
                    {
                        result["success"] = false; result["message"] = "Failed to create family instance. NewFamilyInstance returned null.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                        SetResult(result.ToString()); return;
                    }

                    // Apply rotation if specified
                    if (command.RotationDegrees.HasValue && command.RotationDegrees.Value != 0)
                    {
                        LocationPoint locPoint = instance.Location as LocationPoint;
                        if (locPoint != null)
                        {
                            Line axis = Line.CreateBound(locPoint.Point, locPoint.Point + XYZ.BasisZ); // Rotate around Z-axis at insertion point
                            double angleRadians = command.RotationDegrees.Value * (Math.PI / 180.0);
                            ElementTransformUtils.RotateElement(doc, instance.Id, axis, angleRadians);
                        }
                        else
                        {
                            // Could add a warning if rotation was specified but element is not point-based
                        }
                    }

                    result["success"] = true;
                    result["message"] = $"Element '{command.FamilyName} : {command.TypeName}' created successfully.";
                    result["element_id"] = instance.Id.ToString();
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating element at point: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
