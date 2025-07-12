// Standard/Commands/Generic/GetProjectInfoEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Linq; // Required for Any()
using System.Collections.Generic; // Required for List<string>

namespace Standard.Commands.Generic
{
    public class GetProjectInfoEventHandler : WaitableExternalEventHandlerBase<GetProjectInfoCommand>
    {
        public override string GetName() => "GetProjectInfoEventHandler";

        protected override void Execute(UIApplication app, GetProjectInfoCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            JObject result = new JObject();
            JObject projectInfo = new JObject();

            if (uidoc == null || uidoc.Document == null)
            {
                result["success"] = false;
                result["message"] = "Error getting project info: No active document.";
                SetResult(result.ToString());
                return;
            }

            Document doc = uidoc.Document;

            try
            {
                bool getAll = !command.Fields.Any(); // If Fields list is empty, get all defined info

                if (getAll || command.Fields.Contains("project_name", StringComparer.OrdinalIgnoreCase))
                    projectInfo["project_name"] = doc.Title;

                if (getAll || command.Fields.Contains("file_path", StringComparer.OrdinalIgnoreCase))
                    projectInfo["file_path"] = doc.PathName;

                if (getAll || command.Fields.Contains("revit_version", StringComparer.OrdinalIgnoreCase))
                    projectInfo["revit_version"] = $"{app.Application.VersionName} (Build: {app.Application.VersionBuild})";

                if (getAll || command.Fields.Contains("is_workshared", StringComparer.OrdinalIgnoreCase))
                    projectInfo["is_workshared"] = doc.IsWorkshared;

                if (doc.IsWorkshared)
                {
                    if (getAll || command.Fields.Contains("central_model_path", StringComparer.OrdinalIgnoreCase))
                    {
                        try { // GetWorksharingCentralModelPath can throw if not a workshared doc or no central path
                             ModelPath centralPath = doc.GetWorksharingCentralModelPath();
                             projectInfo["central_model_path"] = centralPath != null ? ModelPathUtils.ConvertModelPathToUserVisiblePath(centralPath) : "N/A";
                        } catch {
                             projectInfo["central_model_path"] = "N/A (Error retrieving or not set)";
                        }
                    }
                }
                else
                {
                    if (command.Fields.Contains("central_model_path", StringComparer.OrdinalIgnoreCase)) // Only include if specifically requested for non-workshared
                        projectInfo["central_model_path"] = "N/A (Not a workshared project)";
                }

                if (getAll || command.Fields.Contains("user_name", StringComparer.OrdinalIgnoreCase))
                    projectInfo["user_name"] = app.Application.Username;

                // Additional ProjectInformation fields
                ProjectInfo projInfoElement = doc.ProjectInformation;
                if (projInfoElement != null)
                {
                    if (getAll || command.Fields.Contains("project_issue_date", StringComparer.OrdinalIgnoreCase))
                        projectInfo["project_issue_date"] = projInfoElement.IssueDate;
                    if (getAll || command.Fields.Contains("project_status", StringComparer.OrdinalIgnoreCase))
                        projectInfo["project_status"] = projInfoElement.Status;
                    if (getAll || command.Fields.Contains("client_name", StringComparer.OrdinalIgnoreCase))
                        projectInfo["client_name"] = projInfoElement.ClientName;
                    if (getAll || command.Fields.Contains("project_address", StringComparer.OrdinalIgnoreCase))
                        projectInfo["project_address"] = projInfoElement.Address;
                    if (getAll || command.Fields.Contains("project_number", StringComparer.OrdinalIgnoreCase))
                        projectInfo["project_number"] = projInfoElement.Number;
                    if (getAll || command.Fields.Contains("project_building_name", StringComparer.OrdinalIgnoreCase)) // Different from doc.Title
                        projectInfo["project_building_name"] = projInfoElement.BuildingName;
                }

                result["success"] = true;
                result["project_info"] = projectInfo;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting project info: {ex.Message}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
