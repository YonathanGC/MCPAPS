// Standard/Commands/Structural/CreateStructuralFramingEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class CreateStructuralFramingEventHandler : WaitableExternalEventHandlerBase<CreateStructuralFramingCommand>
    {
        public override string GetName() => "CreateStructuralFramingEventHandler";

        protected override void Execute(UIApplication app, CreateStructuralFramingCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (command.StartPoint == null || command.EndPoint == null)
                {
                    result["success"] = false;
                    result["message"] = "Error creating structural framing: StartPoint or EndPoint is null.";
                    SetResult(result.ToString());
                    return;
                }

                XYZ start = new XYZ(command.StartPoint.X, command.StartPoint.Y, command.StartPoint.Z);
                XYZ end = new XYZ(command.EndPoint.X, command.EndPoint.Y, command.EndPoint.Z);
                Line curve = Line.CreateBound(start, end);

                if (curve == null || curve.Length < 1e-6)
                {
                    result["success"] = false;
                    result["message"] = "Error creating structural framing: Invalid line geometry (zero length or failed to create).";
                    SetResult(result.ToString());
                    return;
                }

                FamilySymbol familySymbol = new FilteredElementCollector(doc)
                    .OfClass(typeof(FamilySymbol))
                    .WhereElementIsElementType()
                    .Cast<FamilySymbol>()
                    .FirstOrDefault(fs => fs.Name.Equals(command.FamilySymbolName, StringComparison.OrdinalIgnoreCase) &&
                                           (fs.Family.FamilyCategory.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralFraming ||
                                            fs.Family.FamilyCategory.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralColumns));

                if (familySymbol == null)
                {
                    result["success"] = false;
                    result["message"] = $"Error creating structural framing: Family symbol '{command.FamilySymbolName}' not found or not a structural framing/column type.";
                    SetResult(result.ToString());
                    return;
                }

                Level level;
                ElementId levelId;
                try
                {
                    levelId = new ElementId(long.Parse(command.LevelId));
                    level = doc.GetElement(levelId) as Level;
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
                    result["message"] = $"Error creating structural framing: Level with ID/Name '{command.LevelId}' not found.";
                    SetResult(result.ToString());
                    return;
                }

                StructuralType structuralType;
                if (!Enum.TryParse<StructuralType>(command.StructuralType, true, out structuralType) || structuralType == StructuralType.Unknown)
                {
                    // Fallback for common names if direct enum parse fails or is unknown
                    if ("Beam".Equals(command.StructuralType, StringComparison.OrdinalIgnoreCase))
                        structuralType = StructuralType.Beam;
                    else if ("Column".Equals(command.StructuralType, StringComparison.OrdinalIgnoreCase))
                        structuralType = StructuralType.Column;
                    else if ("Brace".Equals(command.StructuralType, StringComparison.OrdinalIgnoreCase))
                        structuralType = StructuralType.Brace;
                    else if ("Footing".Equals(command.StructuralType, StringComparison.OrdinalIgnoreCase)) // Though usually for foundation command
                        structuralType = StructuralType.Footing;
                    else {
                        result["success"] = false;
                        result["message"] = $"Error creating structural framing: Invalid StructuralType '{command.StructuralType}'. Must be Beam, Column, or Brace.";
                        SetResult(result.ToString());
                        return;
                    }
                }


                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create Structural Framing {command.FamilySymbolName}");

                    if (!familySymbol.IsActive)
                    {
                        familySymbol.Activate();
                        doc.Regenerate(); // Important after activating a symbol
                    }

                    FamilyInstance instance = doc.Create.NewFamilyInstance(curve, familySymbol, level, structuralType);

                    if (instance == null)
                    {
                        result["success"] = false;
                        result["message"] = "Error creating structural framing: NewFamilyInstance returned null.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                    }
                    else
                    {
                        // Optional: Set justification parameters if provided
                        if (!string.IsNullOrEmpty(command.YZJustification))
                        {
                            Parameter yzJustParam = instance.LookupParameter("YZ Justification");
                            if (yzJustParam != null && !yzJustParam.IsReadOnly)
                            {
                                // YZ Justification is often an enum (integer). Need to map string to int.
                                // This is a simplified example. A robust solution would map common names to enum values.
                                // For "Top", "Center", "Bottom", "Origin"
                                // E.g. if command.YZJustification.ToLower() == "top" set to appropriate integer
                            }
                        }
                        if (command.ZOffset != 0) // Check if ZOffset was provided and is non-default
                        {
                            Parameter zOffsetParam = instance.LookupParameter("z Offset Value"); // Or "Z Offset Value" - check exact param name in Revit
                             if (zOffsetParam == null) zOffsetParam = instance.LookupParameter("Z Offset Value");


                            if (zOffsetParam != null && !zOffsetParam.IsReadOnly)
                            {
                                zOffsetParam.Set(command.ZOffset);
                            }
                        }

                        // For columns, set Top Level and Base/Top Offsets if applicable (often needed)
                        if (structuralType == StructuralType.Column)
                        {
                            // This is a common requirement for columns. The input structure might need
                            // to be enhanced to include TopLevelId, BaseOffset, TopOffset.
                            // For now, it will create a column based on the line and base level.
                        }


                        result["success"] = true;
                        result["message"] = $"Structural framing element '{command.FamilySymbolName}' created successfully.";
                        result["element_id"] = instance.Id.ToString();
                        tx.Commit();
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating structural framing: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
