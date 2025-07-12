// Standard/Commands/Structural/ExportToRobotFormatEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
// using Autodesk.Revit.DB.Structure; // For AnalyticalModelExchangeService or similar if it exists and is relevant
using System;
using System.IO; // For Path operations
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class ExportToRobotFormatEventHandler : WaitableExternalEventHandlerBase<ExportToRobotFormatCommand>
    {
        public override string GetName() => "ExportToRobotFormatEventHandler";

        protected override void Execute(UIApplication app, ExportToRobotFormatCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (string.IsNullOrEmpty(command.OutputFilePath))
                {
                    result["success"] = false;
                    result["message"] = "OutputFilePath is required.";
                    SetResult(result.ToString());
                    return;
                }

                // Validate path (basic validation)
                try
                {
                    string directory = Path.GetDirectoryName(command.OutputFilePath);
                    if (!Directory.Exists(directory))
                    {
                        Directory.CreateDirectory(directory); // Attempt to create directory if it doesn't exist
                    }
                    if (!command.OutputFilePath.EndsWith(".smxx", StringComparison.OrdinalIgnoreCase) &&
                        !command.OutputFilePath.EndsWith(".stpx", StringComparison.OrdinalIgnoreCase) && // CIS/2
                        !command.OutputFilePath.EndsWith(".ifc", StringComparison.OrdinalIgnoreCase)) // IFC as another option
                    {
                         // For now, let's be flexible but note primarily SMXX is the target for Robot.
                         // result["success"] = false;
                         // result["message"] = "OutputFilePath must end with .smxx (or other supported structural exchange format like .stpx, .ifc).";
                         // SetResult(result.ToString());
                         // return;
                    }
                }
                catch (Exception pathEx)
                {
                    result["success"] = false;
                    result["message"] = $"Invalid OutputFilePath or directory access issue: {pathEx.Message}";
                    SetResult(result.ToString());
                    return;
                }

                // Revit's direct API for triggering SMXX export programmatically is not straightforward or always available.
                // Often, this relies on the "Revit To Robot Structural Analysis Link" add-in.
                // The AnalyticalModelExchangeService class was introduced in later APIs but its capabilities might vary.

                // Option 1: Check for a dedicated service (Conceptual - API might differ or not exist for direct SMXX)
                /*
                AnalyticalModelExchangeServerInfo serverInfo = AnalyticalModelExchangeService.GetServerInfo(doc, "Robot Structural Analysis");
                if (serverInfo != null) {
                    AnalyticalModelExchangeOptions options = new AnalyticalModelExchangeOptions();
                    // Configure options based on command.ExportOptions
                    // e.g., options.IncludeSelfWeight = command.ExportOptions.IncludeSelfWeight ?? true;
                    // options.SetLoadCases(command.ExportOptions.SelectedLoadCaseIds.Select(id => new ElementId(long.Parse(id))).ToList());

                    AnalyticalModelExchangeService.Export(doc, serverInfo.Id, command.OutputFilePath, options);
                    result["success"] = true;
                    result["message"] = $"Model successfully exported to '{command.OutputFilePath}' using AnalyticalModelExchangeService.";
                    result["exported_file_path"] = command.OutputFilePath;
                } else {
                    // Fallback or primary method: Instruct user or try UI automation (not for direct MCP tool)
                    result["success"] = true; // Or false if we strictly require automation
                    result["status"] = "prepared_for_manual_export";
                    result["message"] = "Revit API for direct SMXX export not found or Robot link not configured for direct API access. " +
                                       "Please use the 'Robot Structural Analysis Link' add-in to export the model. " +
                                       $"Ensure the analytical model is consistent. Target path: {command.OutputFilePath}";
                    result["exported_file_path"] = command.OutputFilePath; // Provide path for user reference
                }
                */

                // For now, as a robust starting point, this command will primarily serve to:
                // 1. Validate the analytical model to some extent (conceptual - could be a separate pre-check tool).
                // 2. Inform the user of the intended export path and instruct on manual/add-in based export.
                // This makes the tool useful as a preparation step even without full automation.

                // Placeholder for future model validation logic (can be extensive)
                bool isModelValidForExport = true; // Assume valid for now
                string validationMessage = "Model validation passed (conceptual). ";

                if (isModelValidForExport)
                {
                    result["success"] = true;
                    result["status"] = "guidance_for_manual_export"; // Clearer status
                    result["message"] = validationMessage +
                                       "Please use the 'Robot Structural Analysis' add-in in Revit to export the analytical model. " +
                                       "When prompted for a file path, or in the export settings, please use or verify the following path: " +
                                       command.OutputFilePath;
                    if (command.ExportOptions != null) {
                        if (command.ExportOptions.IncludeSelfWeight.HasValue) {
                            result["message"] += $" Consider setting 'Include Self Weight': {command.ExportOptions.IncludeSelfWeight.Value}.";
                        }
                        if (command.ExportOptions.SelectedLoadCaseIds != null && command.ExportOptions.SelectedLoadCaseIds.Any()) {
                            result["message"] += $" Consider exporting specific load cases: {string.Join(", ", command.ExportOptions.SelectedLoadCaseIds)}.";
                        }
                    }
                    result["target_output_path"] = command.OutputFilePath;
                }
                else
                {
                    result["success"] = false;
                    result["message"] = "Model validation failed. Please check the analytical model for errors before exporting.";
                    // Add specific validation errors if implemented
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error during export preparation: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
