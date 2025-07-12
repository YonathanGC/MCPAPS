// Standard/Commands/Rebar/ModifyRebarSetEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Rebar
{
    public class ModifyRebarSetEventHandler : WaitableExternalEventHandlerBase<ModifyRebarSetCommand>
    {
        public override string GetName() => "ModifyRebarSetEventHandler";

        protected override void Execute(UIApplication app, ModifyRebarSetCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            List<string> modifiedParameters = new List<string>();

            try
            {
                ElementId rebarEid;
                try { rebarEid = new ElementId(long.Parse(command.RebarElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid RebarElementId: {command.RebarElementId}"; SetResult(result.ToString()); return; }

                Autodesk.Revit.DB.Structure.Rebar rebar = doc.GetElement(rebarEid) as Autodesk.Revit.DB.Structure.Rebar;

                if (rebar == null)
                {
                    result["success"] = false; result["message"] = $"Rebar element '{command.RebarElementId}' not found.";
                    SetResult(result.ToString()); return;
                }

                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Modify Rebar Set {command.RebarElementId}");
                    RebarShapeDrivenAccessor accessor = rebar.GetShapeDrivenAccessor();

                    // Modify Bar Type
                    if (!string.IsNullOrEmpty(command.RebarBarTypeName))
                    {
                        RebarBarType newBarType = new FilteredElementCollector(doc)
                            .OfClass(typeof(RebarBarType))
                            .Cast<RebarBarType>()
                            .FirstOrDefault(bt => bt.Name.Equals(command.RebarBarTypeName, StringComparison.OrdinalIgnoreCase));
                        if (newBarType == null) {
                            result["success"] = false; result["message"] = $"New RebarBarType '{command.RebarBarTypeName}' not found.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                        rebar.SetBarTypeId(newBarType.Id);
                        modifiedParameters.Add("rebar_bar_type_name");
                    }

                    // Modify Layout Parameters - This depends on the current layout rule.
                    // For simplicity, we'll try to set common parameters if the accessor supports them.
                    // A more robust solution would check rebar.LayoutRule before attempting to set.
                    bool layoutModified = false;
                    if (command.Quantity.HasValue && accessor.LayoutRule != RebarLayoutRule.Single) // Quantity not for single
                    {
                        // For FixedNumber or NumberWithSpacing
                        // Need to get other params for SetLayoutAs... methods or use parameter if available.
                        Parameter quantityParam = rebar.LookupParameter("Quantity");
                        if (quantityParam != null && !quantityParam.IsReadOnly) {
                            quantityParam.Set(command.Quantity.Value);
                             modifiedParameters.Add("quantity");
                             layoutModified = true;
                        } else {
                            // Try to use accessor methods if direct param fails or is not ideal
                            // This requires knowing the other parameters (arraylength/spacing) to reset the layout.
                            // For now, we rely on the parameter.
                        }
                    }
                    if (command.Spacing.HasValue &&
                        (accessor.LayoutRule == RebarLayoutRule.MaximumSpacing || accessor.LayoutRule == RebarLayoutRule.NumberWithSpacing))
                    {
                        Parameter spacingParam = rebar.LookupParameter("Spacing");
                        if (spacingParam != null && !spacingParam.IsReadOnly) {
                            spacingParam.Set(command.Spacing.Value);
                            modifiedParameters.Add("spacing");
                            layoutModified = true;
                        }
                    }
                     if (command.ArrayLength.HasValue &&
                        (accessor.LayoutRule == RebarLayoutRule.FixedNumber || accessor.LayoutRule == RebarLayoutRule.MaximumSpacing))
                    {
                        // ArrayLength might be controlled by a parameter or by the SetLayoutAs... methods.
                        // For instance, for FixedNumber: accessor.SetLayoutAsFixedNumber(rebar.Quantity, command.ArrayLength.Value, ...);
                        // This requires getting current quantity, barsOnNormalSide etc.
                        // Simpler: try to set "Array Length" parameter if it exists.
                        Parameter arrayLengthParam = rebar.LookupParameter("Array Length"); // Name might vary
                        if (arrayLengthParam == null) arrayLengthParam = rebar.LookupParameter("Length"); // Common fallback

                        if (arrayLengthParam != null && !arrayLengthParam.IsReadOnly) {
                            arrayLengthParam.Set(command.ArrayLength.Value);
                            modifiedParameters.Add("array_length");
                            layoutModified = true;
                        }
                    }


                    // Modify Hooks
                    if (command.HookAtStartTypeName != null) // Allow empty string to remove hook maybe? Or specific "None" value.
                    {
                        if (string.IsNullOrEmpty(command.HookAtStartTypeName) || command.HookAtStartTypeName.Equals("none", StringComparison.OrdinalIgnoreCase)) {
                            rebar.SetHookTypeId(0, ElementId.InvalidElementId); // Remove hook
                        } else {
                            RebarHookType newHookStart = new FilteredElementCollector(doc).OfClass(typeof(RebarHookType)).Cast<RebarHookType>()
                                .FirstOrDefault(ht => ht.Name.Equals(command.HookAtStartTypeName, StringComparison.OrdinalIgnoreCase));
                            if (newHookStart == null) {
                                result["success"] = false; result["message"] = $"New RebarHookType '{command.HookAtStartTypeName}' for start hook not found.";
                                if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            }
                            rebar.SetHookTypeId(0, newHookStart.Id);
                        }
                        modifiedParameters.Add("hook_at_start_type_name");
                    }

                    if (command.HookAtEndTypeName != null)
                    {
                         if (string.IsNullOrEmpty(command.HookAtEndTypeName) || command.HookAtEndTypeName.Equals("none", StringComparison.OrdinalIgnoreCase)) {
                            rebar.SetHookTypeId(1, ElementId.InvalidElementId); // Remove hook
                        } else {
                            RebarHookType newHookEnd = new FilteredElementCollector(doc).OfClass(typeof(RebarHookType)).Cast<RebarHookType>()
                                .FirstOrDefault(ht => ht.Name.Equals(command.HookAtEndTypeName, StringComparison.OrdinalIgnoreCase));
                            if (newHookEnd == null) {
                                result["success"] = false; result["message"] = $"New RebarHookType '{command.HookAtEndTypeName}' for end hook not found.";
                                if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            }
                            rebar.SetHookTypeId(1, newHookEnd.Id);
                        }
                        modifiedParameters.Add("hook_at_end_type_name");
                    }

                    if (layoutModified || modifiedParameters.Contains("rebar_bar_type_name") || modifiedParameters.Contains("hook_at_start_type_name") || modifiedParameters.Contains("hook_at_end_type_name"))
                    {
                         doc.Regenerate(); // Regenerate if significant changes were made
                    }


                    result["success"] = true;
                    result["message"] = $"Rebar set '{command.RebarElementId}' modified successfully.";
                    result["modified_parameters"] = new JArray(modifiedParameters);
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error modifying rebar set: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
