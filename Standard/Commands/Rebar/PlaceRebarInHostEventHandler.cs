// Standard/Commands/Rebar/PlaceRebarInHostEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter (if used directly, or map to XYZ)
using System;
using System.Collections.Generic; // For IList
using System.Linq;
using System.Threading;

namespace Standard.Commands.Rebar
{
    public class PlaceRebarInHostEventHandler : WaitableExternalEventHandlerBase<PlaceRebarInHostCommand>
    {
        public override string GetName() => "PlaceRebarInHostEventHandler";

        protected override void Execute(UIApplication app, PlaceRebarInHostCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                ElementId hostEid;
                try { hostEid = new ElementId(long.Parse(command.HostElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid HostElementId: {command.HostElementId}"; SetResult(result.ToString()); return; }

                Element hostElement = doc.GetElement(hostEid);
                if (hostElement == null || !(hostElement is HostObject || hostElement.Category?.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralFraming || hostElement.Category?.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralColumns || hostElement.Category?.Id.IntegerValue == (int)BuiltInCategory.OST_StructuralFoundation) ) // Check if it can host rebar
                {
                    result["success"] = false; result["message"] = $"Host element '{command.HostElementId}' not found or is not a valid rebar host.";
                    SetResult(result.ToString()); return;
                }

                RebarBarType barType = new FilteredElementCollector(doc)
                    .OfClass(typeof(RebarBarType))
                    .Cast<RebarBarType>()
                    .FirstOrDefault(bt => bt.Name.Equals(command.RebarBarTypeName, StringComparison.OrdinalIgnoreCase));
                if (barType == null) { result["success"] = false; result["message"] = $"RebarBarType '{command.RebarBarTypeName}' not found."; SetResult(result.ToString()); return; }

                RebarShape shape = new FilteredElementCollector(doc)
                    .OfClass(typeof(RebarShape))
                    .Cast<RebarShape>()
                    .FirstOrDefault(s => s.Name.Equals(command.RebarShapeName, StringComparison.OrdinalIgnoreCase));
                if (shape == null) { result["success"] = false; result["message"] = $"RebarShape '{command.RebarShapeName}' not found."; SetResult(result.ToString()); return; }

                RebarHookType hookStart = null;
                if (!string.IsNullOrEmpty(command.HookAtStartTypeName))
                {
                    hookStart = new FilteredElementCollector(doc).OfClass(typeof(RebarHookType)).Cast<RebarHookType>()
                        .FirstOrDefault(ht => ht.Name.Equals(command.HookAtStartTypeName, StringComparison.OrdinalIgnoreCase));
                    if (hookStart == null) { result["success"] = false; result["message"] = $"RebarHookType '{command.HookAtStartTypeName}' for start hook not found."; SetResult(result.ToString()); return; }
                }

                RebarHookType hookEnd = null;
                if (!string.IsNullOrEmpty(command.HookAtEndTypeName))
                {
                    hookEnd = new FilteredElementCollector(doc).OfClass(typeof(RebarHookType)).Cast<RebarHookType>()
                        .FirstOrDefault(ht => ht.Name.Equals(command.HookAtEndTypeName, StringComparison.OrdinalIgnoreCase));
                    if (hookEnd == null) { result["success"] = false; result["message"] = $"RebarHookType '{command.HookAtEndTypeName}' for end hook not found."; SetResult(result.ToString()); return; }
                }


                if (command.NormalToPlaneVector == null || command.OriginPoint == null || command.ShapeOrientationVector == null) {
                     result["success"] = false; result["message"] = "NormalToPlaneVector, OriginPoint, and ShapeOrientationVector are required for standard rebar layouts.";
                     SetResult(result.ToString()); return;
                }
                XYZ normal = new XYZ(command.NormalToPlaneVector.X, command.NormalToPlaneVector.Y, command.NormalToPlaneVector.Z).Normalize();
                XYZ origin = new XYZ(command.OriginPoint.X, command.OriginPoint.Y, command.OriginPoint.Z);
                XYZ xVec = new XYZ(command.ShapeOrientationVector.X, command.ShapeOrientationVector.Y, command.ShapeOrientationVector.Z).Normalize();
                XYZ yVec = normal.CrossProduct(xVec).Normalize(); // Ensure Y is perpendicular to X and Normal


                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Place Rebar in {command.HostElementId}");

                    // Rebar.CreateFromRebarShape requires a RebarShapeDrivenAccessor
                    // For simpler layouts, Rebar.CreateFromCurves might be easier if we define the curves.
                    // However, the prompt implies using RebarShape.
                    // The API Rebar.CreateFromRebarShape(doc, shape, barType, hostElement, origin, xVec, yVec) is a common one.

                    Autodesk.Revit.DB.Structure.Rebar rebar = null;

                    // This is one way to create rebar with shape, though it's complex.
                    // Simpler: Rebar.CreateFromShape (if available and takes these params)
                    // Let's use CreateFromCurves as it's often more direct for simple shapes if we can generate the curves based on shape definition
                    // However, the input is shape-driven.
                    // The method CreateFromRebarShape is the most direct for shape-driven placement.

                    // Ensure vectors are normalized and orthogonal where expected.
                    if (!xVec.IsAlmostEqualTo(XYZ.Zero) && !yVec.IsAlmostEqualTo(XYZ.Zero) && Math.Abs(xVec.DotProduct(yVec)) < 1e-6)
                    {
                        // CreateFromRebarShape(Document doc, RebarShape rebarShape, RebarBarType barType, Element host, XYZ origin, XYZ xVec, XYZ yVec)
                        rebar = Autodesk.Revit.DB.Structure.Rebar.CreateFromRebarShape(doc, shape, barType, hostElement, origin, xVec, yVec);
                    }
                    else
                    {
                        result["success"] = false; result["message"] = "ShapeOrientationVector (xVec) and calculated yVec (from Normal) must be valid and orthogonal.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }


                    if (rebar == null)
                    {
                        result["success"] = false; result["message"] = "Failed to create rebar instance. CreateFromRebarShape returned null.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }

                    // Set layout
                    RebarShapeDrivenAccessor accessor = rebar.GetShapeDrivenAccessor();
                    bool barsOnNormalSide = true; // Default, can be parameterized
                    bool includeFirstBar = true; // Default
                    bool includeLastBar = true; // Default

                    if (command.LayoutRule.Equals("Single", StringComparison.OrdinalIgnoreCase))
                    {
                        accessor.SetLayoutAsSingle();
                    }
                    else if (command.LayoutRule.Equals("FixedNumber", StringComparison.OrdinalIgnoreCase))
                    {
                        if (!command.Quantity.HasValue || !command.ArrayLength.HasValue) {
                             result["success"] = false; result["message"] = "Quantity and ArrayLength are required for FixedNumber layout.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                        accessor.SetLayoutAsFixedNumber(command.Quantity.Value, command.ArrayLength.Value, barsOnNormalSide, includeFirstBar, includeLastBar);
                    }
                    else if (command.LayoutRule.Equals("MaximumSpacing", StringComparison.OrdinalIgnoreCase))
                    {
                         if (!command.Spacing.HasValue || !command.ArrayLength.HasValue) {
                             result["success"] = false; result["message"] = "Spacing and ArrayLength are required for MaximumSpacing layout.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                        accessor.SetLayoutAsMaximumSpacing(command.Spacing.Value, command.ArrayLength.Value, barsOnNormalSide, includeFirstBar, includeLastBar);
                    }
                    else if (command.LayoutRule.Equals("NumberWithSpacing", StringComparison.OrdinalIgnoreCase))
                    {
                        if (!command.Quantity.HasValue || !command.Spacing.HasValue) {
                             result["success"] = false; result["message"] = "Quantity and Spacing are required for NumberWithSpacing layout.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                        accessor.SetLayoutAsNumberWithSpacing(command.Quantity.Value, command.Spacing.Value, barsOnNormalSide, includeFirstBar, includeLastBar);
                    }
                    else
                    {
                        result["success"] = false; result["message"] = $"Unsupported LayoutRule: {command.LayoutRule}";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }

                    // Apply Hooks
                    if (hookStart != null) rebar.SetHookTypeId(0, hookStart.Id); // 0 for start hook
                    if (hookEnd != null) rebar.SetHookTypeId(1, hookEnd.Id);   // 1 for end hook

                    doc.Regenerate(); // Important for rebar visibility and for some parameters to update.

                    result["success"] = true;
                    result["message"] = $"Rebar placed successfully in host '{command.HostElementId}'.";
                    result["rebar_element_id"] = rebar.Id.ToString();
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error placing rebar: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
