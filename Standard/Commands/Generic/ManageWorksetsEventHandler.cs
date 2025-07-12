// Standard/Commands/Generic/ManageWorksetsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class ManageWorksetsEventHandler : WaitableExternalEventHandlerBase<ManageWorksetsCommand>
    {
        public override string GetName() => "ManageWorksetsEventHandler";

        protected override void Execute(UIApplication app, ManageWorksetsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (!doc.IsWorkshared &&
                    (command.Action.Equals("set_active_workset", StringComparison.OrdinalIgnoreCase) ||
                     command.Action.Equals("create_workset", StringComparison.OrdinalIgnoreCase) ||
                     command.Action.Equals("get_active_workset", StringComparison.OrdinalIgnoreCase) ||
                     command.Action.Equals("list_worksets", StringComparison.OrdinalIgnoreCase) )) // is_element_editable and get_workset_of_element can still be relevant
                {
                    result["success"] = false;
                    result["message"] = "Project is not workshared. Most workset operations are not applicable.";
                    // For get_workset_of_element or is_element_editable, we might still want to proceed and report default workset info.
                    // However, the concept of "active" or "creating" doesn't apply.
                    // Let's allow list_worksets to show default worksets if any.
                     if (!command.Action.Equals("list_worksets", StringComparison.OrdinalIgnoreCase)) {
                        SetResult(result.ToString());
                        return;
                     }
                }

                WorksetTable worksetTable = doc.GetWorksetTable();

                switch (command.Action.ToLowerInvariant())
                {
                    case "list_worksets":
                        JArray worksetsArray = new JArray();
                        // IList<Workset> worksets = new FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset).ToWorksets();
                        // To include all kinds (user, family, view):
                        IList<WorksetPreview> allWorksetsPreview = worksetTable.GetWorksetPreviewTable(); // Gives basic info

                        // For more details like IsEditable, need to get Workset objects
                        IList<Workset> allWorksets = new FilteredWorksetCollector(doc).ToWorksets();


                        foreach (Workset ws in allWorksets)
                        {
                            JObject wsJson = new JObject();
                            wsJson["id"] = ws.Id.IntegerValue.ToString(); // WorksetId.IntegerValue
                            wsJson["unique_id"] = ws.UniqueId.ToString(); // Guid
                            wsJson["name"] = ws.Name;
                            wsJson["kind"] = ws.Kind.ToString();
                            wsJson["is_editable"] = ws.IsEditable;
                            wsJson["is_open"] = ws.IsOpen;
                            wsJson["is_default_workset"] = ws.IsDefaultWorkset;
                            // Owner is not directly on Workset, but on WorksharingTooltipInfo
                            worksetsArray.Add(wsJson);
                        }
                        result["success"] = true;
                        result["worksets"] = worksetsArray;
                        break;

                    case "get_active_workset":
                        if (!doc.IsWorkshared) { /* Handled above, but as safeguard */ }
                        WorksetId activeId = worksetTable.GetActiveWorksetId();
                        Workset activeWs = worksetTable.GetWorkset(activeId);
                        if (activeWs != null)
                        {
                            result["success"] = true;
                            result["active_workset"] = new JObject {
                                { "id", activeWs.Id.IntegerValue.ToString() },
                                { "name", activeWs.Name },
                                { "kind", activeWs.Kind.ToString() }
                            };
                        }
                        else
                        {
                            result["success"] = false; result["message"] = "Could not retrieve active workset.";
                        }
                        break;

                    case "set_active_workset":
                         if (!doc.IsWorkshared) { /* Handled above */ }
                        if (string.IsNullOrEmpty(command.WorksetName)) {
                            result["success"] = false; result["message"] = "WorksetName is required to set active workset."; break;
                        }
                        Workset targetWs = new FilteredWorksetCollector(doc)
                            .OfKind(WorksetKind.UserWorkset) // Typically only set user worksets as active
                            .Cast<Workset>()
                            .FirstOrDefault(ws => ws.Name.Equals(command.WorksetName, StringComparison.OrdinalIgnoreCase));
                        if (targetWs == null) {
                            result["success"] = false; result["message"] = $"UserWorkset named '{command.WorksetName}' not found."; break;
                        }
                        if (!targetWs.IsEditable) { // Or if it's not open, etc.
                             result["success"] = false; result["message"] = $"Workset '{command.WorksetName}' is not editable or cannot be made active."; break;
                        }
                        // Transaction needed for SetActiveWorksetId
                        using (Transaction txSetActive = new Transaction(doc, "Set Active Workset"))
                        {
                            txSetActive.Start();
                            worksetTable.SetActiveWorksetId(targetWs.Id);
                            txSetActive.Commit();
                            result["success"] = true;
                            result["message"] = $"Active workset changed to '{command.WorksetName}'.";
                        }
                        break;

                    case "create_workset":
                        if (!doc.IsWorkshared) { /* Handled above */ }
                        if (string.IsNullOrEmpty(command.WorksetName)) {
                            result["success"] = false; result["message"] = "WorksetName is required to create a workset."; break;
                        }
                        if (WorksetTable.IsWorksetNameUnique(doc, command.WorksetName))
                        {
                            using (Transaction txCreate = new Transaction(doc, "Create Workset"))
                            {
                                txCreate.Start();
                                Workset newWs = Workset.Create(doc, command.WorksetName);
                                txCreate.Commit();
                                result["success"] = true;
                                result["message"] = $"Workset '{command.WorksetName}' created successfully.";
                                result["workset_id"] = newWs.Id.IntegerValue.ToString();
                                result["workset_name"] = newWs.Name;
                            }
                        }
                        else
                        {
                            result["success"] = false; result["message"] = $"Workset name '{command.WorksetName}' is not unique.";
                        }
                        break;

                    case "get_workset_of_element":
                        if (string.IsNullOrEmpty(command.ElementId)) {
                             result["success"] = false; result["message"] = "ElementId is required to get its workset."; break;
                        }
                        ElementId elEid;
                        try { elEid = new ElementId(long.Parse(command.ElementId)); }
                        catch { result["success"] = false; result["message"] = $"Invalid ElementId: {command.ElementId}"; break; }
                        Element el = doc.GetElement(elEid);
                        if (el == null) { result["success"] = false; result["message"] = $"Element '{command.ElementId}' not found."; break; }

                        WorksetId elWorksetId = el.WorksetId;
                        if (elWorksetId == null || elWorksetId == WorksetId.InvalidWorksetId) {
                             result["success"] = true; // Element exists but may not have a specific user workset (e.g. in non-workshared or certain system elements)
                             result["message"] = "Element does not have a specific user workset or project is not workshared.";
                             result["workset_id"] = WorksetId.InvalidWorksetId.IntegerValue.ToString();
                             result["workset_name"] = "N/A";
                             break;
                        }
                        Workset elWs = worksetTable.GetWorkset(elWorksetId);
                        if (elWs != null) {
                            result["success"] = true;
                            result["element_id"] = command.ElementId;
                            result["workset_id"] = elWs.Id.IntegerValue.ToString();
                            result["workset_name"] = elWs.Name;
                            result["workset_kind"] = elWs.Kind.ToString();
                        } else {
                             result["success"] = false; result["message"] = $"Could not retrieve workset for element '{command.ElementId}' with WorksetId {elWorksetId.IntegerValue}.";
                        }
                        break;

                    case "is_element_editable": // More complex, involves checking out status.
                        // This is a simplified check. True editability depends on ownership.
                        if (string.IsNullOrEmpty(command.ElementId)) {
                             result["success"] = false; result["message"] = "ElementId is required for is_element_editable."; break;
                        }
                        ElementId editElId;
                        try { editElId = new ElementId(long.Parse(command.ElementId)); }
                        catch { result["success"] = false; result["message"] = $"Invalid ElementId: {command.ElementId}"; break; }
                        Element editEl = doc.GetElement(editElId);
                        if (editEl == null) { result["success"] = false; result["message"] = $"Element '{command.ElementId}' not found."; break; }

                        bool isEditable = false;
                        string editableStatus = "Unknown";
                        if (doc.IsWorkshared) {
                            WorksharingTooltipInfo tooltipInfo = WorksharingUtils.GetWorksharingTooltipInfo(doc, editElId);
                            editableStatus = tooltipInfo.CheckoutStatus.ToString(); // OwnedByOtherUser, NotOwned, OwnedByCurrentUser, etc.
                            isEditable = tooltipInfo.CheckoutStatus == CheckoutStatus.OwnedByCurrentUser || tooltipInfo.CheckoutStatus == CheckoutStatus.NotOwned;
                        } else {
                            isEditable = true; // In non-workshared, all local elements are editable.
                            editableStatus = "NotWorkshared";
                        }
                        result["success"] = true;
                        result["element_id"] = command.ElementId;
                        result["is_editable"] = isEditable;
                        result["checkout_status"] = editableStatus;
                        break;


                    default:
                        result["success"] = false; result["message"] = $"Unsupported action: {command.Action}";
                        break;
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error managing worksets: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
