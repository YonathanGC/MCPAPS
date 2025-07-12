// Standard/Commands/Structural/GetElementParametersEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class GetElementParametersEventHandler : WaitableExternalEventHandlerBase<GetElementParametersCommand>
    {
        public override string GetName() => "GetElementParametersEventHandler";

        protected override void Execute(UIApplication app, GetElementParametersCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JArray parametersArray = new JArray();

            try
            {
                ElementId eid;
                try
                {
                    eid = new ElementId(long.Parse(command.ElementId));
                }
                catch (FormatException)
                {
                    result["success"] = false;
                    result["message"] = $"Invalid Element ID format: '{command.ElementId}'.";
                    SetResult(result.ToString());
                    return;
                }

                Element element = doc.GetElement(eid);

                if (element == null)
                {
                    result["success"] = false;
                    result["message"] = $"Element with ID '{command.ElementId}' not found.";
                }
                else
                {
                    result["success"] = true;
                    result["element_id"] = command.ElementId;

                    IList<Parameter> parameters = element.GetOrderedParameters();

                    foreach (Parameter param in parameters)
                    {
                        if (command.ParameterNames.Any() && !command.ParameterNames.Contains(param.Definition.Name, StringComparer.OrdinalIgnoreCase))
                        {
                            continue; // Skip if specific names are requested and this is not one of them
                        }

                        JObject paramJson = new JObject();
                        paramJson["name"] = param.Definition.Name;
                        paramJson["is_readonly"] = param.IsReadOnly;
                        paramJson["storage_type"] = param.StorageType.ToString();

                        switch (param.StorageType)
                        {
                            case StorageType.Double:
                                paramJson["value"] = param.AsDouble();
                                break;
                            case StorageType.Integer:
                                paramJson["value"] = param.AsInteger();
                                break;
                            case StorageType.String:
                                paramJson["value"] = param.AsString();
                                break;
                            case StorageType.ElementId:
                                ElementId valId = param.AsElementId();
                                if (valId != null && valId != ElementId.InvalidElementId)
                                {
                                    // Attempt to get the element name if it's an ElementId
                                    Element referencedElement = doc.GetElement(valId);
                                    paramJson["value"] = referencedElement != null ? $"{referencedElement.Name} (ID: {valId.ToString()})" : valId.ToString();
                                }
                                else
                                {
                                     paramJson["value"] = ElementId.InvalidElementId.ToString();
                                }
                                break;
                            case StorageType.None: // For parameters like Family or Type that don't have a simple value
                                if (param.Definition.Name.Equals("Family", StringComparison.OrdinalIgnoreCase) && element.get_Parameter(BuiltInParameter.ELEM_FAMILY_PARAM) != null)
                                {
                                     paramJson["value"] = element.get_Parameter(BuiltInParameter.ELEM_FAMILY_PARAM).AsValueString();
                                }
                                else if (param.Definition.Name.Equals("Type", StringComparison.OrdinalIgnoreCase) && element.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM) != null)
                                {
                                     paramJson["value"] = element.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM).AsValueString();
                                }
                                else
                                {
                                     paramJson["value"] = "N/A (StorageType.None)";
                                }
                                break;
                            default:
                                paramJson["value"] = param.AsValueString(); // Fallback, might not be ideal for all types
                                break;
                        }
                        parametersArray.Add(paramJson);
                    }
                    result["parameters"] = parametersArray;
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting element parameters: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
