// Standard/Commands/Structural/SetElementParameterValueEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class SetElementParameterValueEventHandler : WaitableExternalEventHandlerBase<SetElementParameterValueCommand>
    {
        public override string GetName() => "SetElementParameterValueEventHandler";

        protected override void Execute(UIApplication app, SetElementParameterValueCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

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
                    Parameter param = element.LookupParameter(command.ParameterName);
                    if (param == null)
                    {
                        // Attempt to find by BuiltInParameter if ParameterName matches one
                        BuiltInParameter builtInParamEnum = BuiltInParameter.INVALID;
                        try
                        {
                            builtInParamEnum = (BuiltInParameter)Enum.Parse(typeof(BuiltInParameter), command.ParameterName, true);
                        }
                        catch { /* Ignore if not a valid enum name */ }

                        if (builtInParamEnum != BuiltInParameter.INVALID)
                        {
                            param = element.get_Parameter(builtInParamEnum);
                        }
                    }


                    if (param == null || param.Definition == null) // Check Definition as well for validity
                    {
                        result["success"] = false;
                        result["message"] = $"Parameter '{command.ParameterName}' not found on element ID '{command.ElementId}'.";
                    }
                    else if (param.IsReadOnly)
                    {
                        result["success"] = false;
                        result["message"] = $"Parameter '{command.ParameterName}' is read-only.";
                    }
                    else
                    {
                        using (Transaction tx = new Transaction(doc))
                        {
                            tx.Start($"MCP Set Parameter {command.ParameterName}");
                            bool success = false;
                            string errorMsg = string.Empty;

                            try
                            {
                                switch (param.StorageType)
                                {
                                    case StorageType.Double:
                                        if (command.ParameterValue.Type == JTokenType.Float || command.ParameterValue.Type == JTokenType.Integer)
                                            param.Set(command.ParameterValue.Value<double>());
                                        else
                                            errorMsg = "Invalid value type for Double parameter. Expected number.";
                                        break;
                                    case StorageType.Integer:
                                         if (command.ParameterValue.Type == JTokenType.Integer)
                                            param.Set(command.ParameterValue.Value<int>());
                                        else
                                            errorMsg = "Invalid value type for Integer parameter. Expected integer.";
                                        break;
                                    case StorageType.String:
                                        param.Set(command.ParameterValue.Value<string>());
                                        break;
                                    case StorageType.ElementId:
                                        // Assuming the value is provided as the ElementId string or long
                                        ElementId valId;
                                        try {
                                            valId = new ElementId(long.Parse(command.ParameterValue.Value<string>()));
                                        } catch {
                                            valId = ElementId.InvalidElementId; // Fallback for direct string if it's special
                                            // For some ElementId parameters, a string name might be settable (e.g. Level name)
                                            // This part might need more sophisticated handling based on parameter type
                                             if (param.Definition.ParameterType == ParameterType.Text) { // A guess
                                                param.Set(command.ParameterValue.Value<string>());
                                            } else {
                                                 errorMsg = "Invalid value for ElementId parameter. Expected ID string or long.";
                                            }
                                        }
                                        if(valId != ElementId.InvalidElementId) param.Set(valId);
                                        else if (string.IsNullOrEmpty(errorMsg)) { /* error already set or handled by text fallback */ }

                                        break;
                                    default:
                                        errorMsg = $"Unsupported parameter storage type: {param.StorageType}.";
                                        break;
                                }

                                if (string.IsNullOrEmpty(errorMsg))
                                {
                                    success = true;
                                    result["success"] = true;
                                    result["message"] = $"Parameter '{command.ParameterName}' updated successfully for element '{command.ElementId}'.";
                                    result["updated_value"] = command.ParameterValue.ToString(); // Reflect what was attempted to set
                                }
                                else
                                {
                                    result["success"] = false;
                                    result["message"] = errorMsg;
                                }

                            }
                            catch (Exception ex)
                            {
                                success = false; // Ensure success is false if an exception occurs
                                result["success"] = false;
                                result["message"] = $"API Error setting parameter: {ex.Message}";
                            }


                            if (success)
                            {
                                tx.Commit();
                            }
                            else
                            {
                                if (tx.GetStatus() == TransactionStatus.Started)
                                    tx.RollBack();
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error setting element parameter: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
