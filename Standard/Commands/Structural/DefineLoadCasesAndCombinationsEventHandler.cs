// Standard/Commands/Structural/DefineLoadCasesAndCombinationsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class DefineLoadCasesAndCombinationsEventHandler : WaitableExternalEventHandlerBase<DefineLoadCasesAndCombinationsCommand>
    {
        public override string GetName() => "DefineLoadCasesAndCombinationsEventHandler";

        protected override void Execute(UIApplication app, DefineLoadCasesAndCombinationsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Define Load {command.Action}");
                    Element createdElement = null;

                    if (command.Action == "create_case")
                    {
                        if (string.IsNullOrEmpty(command.CaseName) || string.IsNullOrEmpty(command.Nature))
                        {
                            result["success"] = false; result["message"] = "CaseName and Nature are required for create_case.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        LoadCaseNature nature;
                        if (!Enum.TryParse<LoadCaseNature>(command.Nature, true, out nature))
                        {
                            result["success"] = false; result["message"] = $"Invalid LoadCaseNature: {command.Nature}.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        LoadCategory category = null;
                        if (!string.IsNullOrEmpty(command.CategoryName))
                        {
                            category = new FilteredElementCollector(doc)
                                .OfClass(typeof(LoadCategory))
                                .Cast<LoadCategory>()
                                .FirstOrDefault(lc => lc.Name.Equals(command.CategoryName, StringComparison.OrdinalIgnoreCase));
                            if (category == null) {
                                result["success"] = false; result["message"] = $"LoadCategory '{command.CategoryName}' not found.";
                                if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                            }
                        } else {
                            // Attempt to get a default category based on nature if not specified
                            // This is a simplification; Revit's internal mapping might be more complex
                            // or it might pick a default automatically. For explicit control, user should provide category.
                            // For this example, if not provided, we let Revit decide or it might fail if category is strictly required by API.
                            // The API LoadCase.Create(doc, name, nature, categoryId) - categoryId is ElementId.
                        }

                        // Check if a load case with the same name already exists
                        LoadCase existingCase = new FilteredElementCollector(doc)
                            .OfClass(typeof(LoadCase))
                            .Cast<LoadCase>()
                            .FirstOrDefault(lc => lc.Name.Equals(command.CaseName, StringComparison.OrdinalIgnoreCase));

                        if (existingCase != null) {
                             result["success"] = false; result["message"] = $"LoadCase with name '{command.CaseName}' already exists.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }


                        createdElement = LoadCase.Create(doc, command.CaseName, nature, category?.Id ?? ElementId.InvalidElementId);
                    }
                    else if (command.Action == "create_combination")
                    {
                        if (string.IsNullOrEmpty(command.CombinationName) || string.IsNullOrEmpty(command.CombinationType) || command.Components == null || !command.Components.Any())
                        {
                            result["success"] = false; result["message"] = "CombinationName, CombinationType, and at least one Component are required for create_combination.";
                            if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        LoadCombinationType type;
                        if (!Enum.TryParse<LoadCombinationType>(command.CombinationType, true, out type))
                        {
                             result["success"] = false; result["message"] = $"Invalid LoadCombinationType: {command.CombinationType}.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }

                        // Check if a load combination with the same name already exists
                        LoadCombination existingCombo = new FilteredElementCollector(doc)
                            .OfClass(typeof(LoadCombination))
                            .Cast<LoadCombination>()
                            .FirstOrDefault(lc => lc.Name.Equals(command.CombinationName, StringComparison.OrdinalIgnoreCase));

                        if (existingCombo != null) {
                             result["success"] = false; result["message"] = $"LoadCombination with name '{command.CombinationName}' already exists.";
                             if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                        }


                        LoadCombination combination = LoadCombination.Create(doc, command.CombinationName, type);
                        if (combination != null)
                        {
                            foreach (var componentInfo in command.Components)
                            {
                                ElementId caseEid;
                                try { caseEid = new ElementId(long.Parse(componentInfo.CaseId));}
                                catch {
                                     result["success"] = false; result["message"] = $"Invalid CaseId '{componentInfo.CaseId}' in combination components.";
                                     if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                                }

                                LoadCase caseForComponent = doc.GetElement(caseEid) as LoadCase;
                                if (caseForComponent == null)
                                {
                                    result["success"] = false; result["message"] = $"LoadCase with ID '{componentInfo.CaseId}' not found for combination component.";
                                    if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                                }
                                LoadComponent.Create(doc, combination.Id, caseForComponent.Id, componentInfo.Factor);
                            }
                            createdElement = combination;
                        }
                    }
                    else
                    {
                        result["success"] = false; result["message"] = "Invalid action specified. Must be 'create_case' or 'create_combination'.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }

                    if (createdElement != null && createdElement.IsValidObject)
                    {
                        result["success"] = true;
                        result["message"] = $"{command.Action.Replace("_", " ")} '{ (command.Action == "create_case" ? command.CaseName : command.CombinationName) }' created successfully.";
                        result["element_id"] = createdElement.Id.ToString();
                        tx.Commit();
                    }
                    else
                    {
                         if (! (bool)(result["success"] ?? false))
                         {
                           result["success"] = false;
                           result["message"] = $"Failed to create {command.Action.Replace("_", " ")}. Creation method returned null or invalid object.";
                         }
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack();
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error defining load case/combination: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
