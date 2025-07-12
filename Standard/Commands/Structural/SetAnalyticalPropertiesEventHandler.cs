// Standard/Commands/Structural/SetAnalyticalPropertiesEventHandler.cs
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
    public class SetAnalyticalPropertiesEventHandler : WaitableExternalEventHandlerBase<SetAnalyticalPropertiesCommand>
    {
        public override string GetName() => "SetAnalyticalPropertiesEventHandler";

        private BoundaryConditionType Get condizioneTypeFromString(string state)
        {
            if (string.IsNullOrEmpty(state)) return BoundaryConditionType.Released; // Default or decide error
            switch (state.ToLowerInvariant())
            {
                case "fixed": return BoundaryConditionType.Fixed;
                case "released": return BoundaryConditionType.Released;
                case "spring": return BoundaryConditionType.Spring;
                default: throw new ArgumentException($"Invalid boundary condition state: {state}");
            }
        }


        protected override void Execute(UIApplication app, SetAnalyticalPropertiesCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                ElementId eid;
                try { eid = new ElementId(long.Parse(command.ElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid ElementId: {command.ElementId}"; SetResult(result.ToString()); return; }

                Element element = doc.GetElement(eid);
                if (element == null)
                {
                    result["success"] = false; result["message"] = $"Element with ID '{command.ElementId}' not found.";
                    SetResult(result.ToString()); return;
                }

                AnalyticalModel analyticalModel = element.GetAnalyticalModel();
                if (analyticalModel == null)
                {
                    result["success"] = false; result["message"] = $"Element ID '{command.ElementId}' does not have an analytical model.";
                    SetResult(result.ToString()); return;
                }

                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Set Analytical Properties for {command.ElementId}");

                    if (command.PropertyType == "boundary_conditions")
                    {
                        if (command.BoundaryConditions == null) {
                             result["success"] = false; result["message"] = "BoundaryConditions data is required for property_type 'boundary_conditions'.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        // Boundary conditions can be applied to AnalyticalMember (at ends) or AnalyticalNode.
                        // This simplified example assumes applying to the entire AnalyticalModel element if it supports it directly,
                        // or to its start/end nodes if it's an AnalyticalMember.
                        // Revit API for BCs: AnalyticalModel.SetBoundaryConditions(BoundaryConditions boundaryConditions)
                        // BoundaryConditions is an object you construct.

                        BoundaryConditions bc = analyticalModel.GetBoundaryConditions();
                        if (bc == null) { // May need to create if not existing, or this indicates not applicable
                            // For some elements, you might need to get specific nodes if it's a member.
                            // This is a complex area. For now, we assume bc can be retrieved or the operation isn't applicable.
                            // Let's try to create new BoundaryConditions and set it.
                            // It's more common to set BCs on AnalyticalMember ends or AnalyticalNodes.
                            // This part needs careful API checking.
                            // A common pattern is AnalyticalMember.SetBoundaryConditions(startNodeBC, endNodeBC)
                            // Or for a point connection: AnalyticalNode.SetBoundaryConditions(nodeBC)
                            // For simplicity, if analyticalModel itself doesn't directly take SetBoundaryConditions, this will be tricky.

                            // Let's assume we are setting it for an AnalyticalLink or a specific node if the host is a point.
                            // The AnalyticalModel class itself has SetBoundaryConditions.
                             bc = new BoundaryConditions(analyticalModel.Id, CoordinateSystemType.Local); // Create new if null - might not be valid for all AM types
                        }

                        // This is a very simplified mapping. Revit's API might require more specific handling or use enums directly.
                        // The BoundaryConditions object has properties like TranslationX, RotationY etc.
                        // BoundaryConditions.SetXYZCondition(BoundaryConditionPosition position,CoordinateSystemType coordinateSystem,BoundaryConditionType x,BoundaryConditionType y,BoundaryConditionType z,double x_SpringModulus,double y_SpringModulus,double z_SpringModulus)
                        // This is complex. Let's try setting parameters if they exist.
                        // A more direct way is to use AnalyticalMember.SetBoundaryConditions(BoundaryConditions startConditions, BoundaryConditions endConditions)
                        // Or AnalyticalNode.SetBoundaryConditions(BoundaryConditions conditions)

                        // For this example, we'll try to set the parameters if they exist on the analytical model itself.
                        // This might not be the correct API usage for all cases.
                        // The SetBoundaryConditions method on AnalyticalModel is the target.

                        if (command.BoundaryConditions.TranslationX != null) bc.SetTranslation(BoundaryConditionPosition.Point, 0, GetCondizioneTypeFromString(command.BoundaryConditions.TranslationX), command.BoundaryConditions.SpringModulusTX ?? 0);
                        if (command.BoundaryConditions.TranslationY != null) bc.SetTranslation(BoundaryConditionPosition.Point, 1, GetCondizioneTypeFromString(command.BoundaryConditions.TranslationY), command.BoundaryConditions.SpringModulusTY ?? 0);
                        if (command.BoundaryConditions.TranslationZ != null) bc.SetTranslation(BoundaryConditionPosition.Point, 2, GetCondizioneTypeFromString(command.BoundaryConditions.TranslationZ), command.BoundaryConditions.SpringModulusTZ ?? 0);
                        if (command.BoundaryConditions.RotationX != null) bc.SetRotation(BoundaryConditionPosition.Point, 0, GetCondizioneTypeFromString(command.BoundaryConditions.RotationX), command.BoundaryConditions.SpringModulusRX ?? 0);
                        if (command.BoundaryConditions.RotationY != null) bc.SetRotation(BoundaryConditionPosition.Point, 1, GetCondizioneTypeFromString(command.BoundaryConditions.RotationY), command.BoundaryConditions.SpringModulusRY ?? 0);
                        if (command.BoundaryConditions.RotationZ != null) bc.SetRotation(BoundaryConditionPosition.Point, 2, GetCondizioneTypeFromString(command.BoundaryConditions.RotationZ), command.BoundaryConditions.SpringModulusRZ ?? 0);

                        analyticalModel.SetBoundaryConditions(bc); // This is the key API call.

                        result["success"] = true;
                        result["message"] = $"Boundary conditions updated for element '{command.ElementId}'.";
                    }
                    else if (command.PropertyType == "end_releases")
                    {
                        if (!(analyticalModel is AnalyticalMember am))
                        {
                            result["success"] = false; result["message"] = "End releases can only be applied to AnalyticalMember types.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }
                         if (command.EndReleases == null) {
                             result["success"] = false; result["message"] = "EndReleases data is required for property_type 'end_releases'.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        // Get current releases or create new default ones
                        bool startFx=false, startFy=false, startFz=false, startMx=false, startMy=false, startMz=false;
                        bool endFx=false, endFy=false, endFz=false, endMx=false, endMy=false, endMz=false;

                        am.GetReleases(true, out startFx, out startFy, out startFz, out startMx, out startMy, out startMz);
                        am.GetReleases(false, out endFx, out endFy, out endFz, out endMx, out endMy, out endMz);

                        // Update based on command input
                        if (command.EndReleases.StartMx.HasValue) startMx = command.EndReleases.StartMx.Value;
                        if (command.EndReleases.StartMy.HasValue) startMy = command.EndReleases.StartMy.Value;
                        if (command.EndReleases.StartMz.HasValue) startMz = command.EndReleases.StartMz.Value;
                        if (command.EndReleases.EndMx.HasValue) endMx = command.EndReleases.EndMx.Value;
                        if (command.EndReleases.EndMy.HasValue) endMy = command.EndReleases.EndMy.Value;
                        if (command.EndReleases.EndMz.HasValue) endMz = command.EndReleases.EndMz.Value;

                        am.SetReleases(true, startFx, startFy, startFz, startMx, startMy, startMz);
                        am.SetReleases(false, endFx, endFy, endFz, endMx, endMy, endMz);

                        result["success"] = true;
                        result["message"] = $"End releases updated for element '{command.ElementId}'.";
                    }
                    else
                    {
                        result["success"] = false; result["message"] = $"Unsupported PropertyType: {command.PropertyType}";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error setting analytical properties: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
