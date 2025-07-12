// Standard/Commands/Generic/GetElementsByFilterEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter
using System;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class GetElementsByFilterEventHandler : WaitableExternalEventHandlerBase<GetElementsByFilterCommand>
    {
        public override string GetName() => "GetElementsByFilterEventHandler";

        // Helper to map string category name to BuiltInCategory
        private bool TryGetBuiltInCategory(string categoryName, out BuiltInCategory builtInCategory)
        {
            builtInCategory = BuiltInParameter.INVALID.ToBuiltInCategory(); // Placeholder for invalid
            if (string.IsNullOrEmpty(categoryName)) return false;

            // Try direct enum parse
            if (Enum.TryParse<BuiltInCategory>(categoryName, true, out builtInCategory))
            {
                // Check if it's a valid category enum by trying to get its label (can throw if not a real category)
                try { LabelUtils.GetLabelFor(builtInCategory); return true; } catch { /* not a valid category */ }
            }

            // Common mappings (extend as needed)
            var map = new Dictionary<string, BuiltInCategory>(StringComparer.OrdinalIgnoreCase) {
                { "Walls", BuiltInCategory.OST_Walls }, { "Floors", BuiltInCategory.OST_Floors },
                { "Doors", BuiltInCategory.OST_Doors }, { "Windows", BuiltInCategory.OST_Windows },
                { "Roofs", BuiltInCategory.OST_Roofs }, { "Columns", BuiltInCategory.OST_Columns }, // Architectural columns
                { "Structural Columns", BuiltInCategory.OST_StructuralColumns },
                { "Structural Framing", BuiltInCategory.OST_StructuralFraming },
                { "Structural Foundations", BuiltInCategory.OST_StructuralFoundation },
                { "Levels", BuiltInCategory.OST_Levels }, { "Grids", BuiltInCategory.OST_Grids },
                { "Rooms", BuiltInCategory.OST_Rooms }, { "Furniture", BuiltInCategory.OST_Furniture },
                { "Generic Models", BuiltInCategory.OST_GenericModel },
                { "Views", BuiltInCategory.OST_Views }
                // ... add more common categories
            };
            return map.TryGetValue(categoryName, out builtInCategory);
        }

        // Helper to map string class name to Type
        private Type GetTypeFromString(string className)
        {
            if (string.IsNullOrEmpty(className)) return null;
            // This is a simplified mapping. A more robust solution might use reflection
            // or a pre-defined dictionary of supported types.
            switch (className.ToLowerInvariant())
            {
                case "wall": return typeof(Wall);
                case "floor": return typeof(Floor);
                case "familyinstance": return typeof(FamilyInstance);
                case "level": return typeof(Level);
                case "grid": return typeof(Grid);
                case "view": return typeof(View);
                // Add more types as needed
                default: return null;
            }
        }


        protected override void Execute(UIApplication app, GetElementsByFilterCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JArray elementsArray = new JArray();

            try
            {
                FilteredElementCollector collector;
                if (!string.IsNullOrEmpty(command.FilterCriteria.ViewId))
                {
                    ElementId viewEid;
                    try { viewEid = new ElementId(long.Parse(command.FilterCriteria.ViewId)); }
                    catch { result["success"] = false; result["message"] = $"Invalid ViewId: {command.FilterCriteria.ViewId}"; SetResult(result.ToString()); return; }
                    collector = new FilteredElementCollector(doc, viewEid);
                }
                else
                {
                    collector = new FilteredElementCollector(doc);
                }

                if (command.FilterCriteria.ExcludeElementTypes)
                {
                    collector.WhereElementIsNotElementType();
                }

                // Category Filter
                if (!string.IsNullOrEmpty(command.FilterCriteria.CategoryName))
                {
                    BuiltInCategory bic;
                    if (TryGetBuiltInCategory(command.FilterCriteria.CategoryName, out bic) && bic != BuiltInParameter.INVALID.ToBuiltInCategory())
                    {
                        collector.OfCategory(bic);
                    }
                    else
                    {
                        result["success"] = false; result["message"] = $"Category '{command.FilterCriteria.CategoryName}' not recognized or not a valid BuiltInCategory.";
                        SetResult(result.ToString()); return;
                    }
                }

                // Class Filter
                if (!string.IsNullOrEmpty(command.FilterCriteria.ClassName))
                {
                    Type type = GetTypeFromString(command.FilterCriteria.ClassName);
                    if (type != null) collector.OfClass(type);
                    else { /* Optional: warning if class name not recognized, or just ignore */ }
                }


                List<ElementFilter> elementFilters = new List<ElementFilter>();

                // Bounding Box Filter
                if (command.FilterCriteria.BoundingBoxIntersect != null)
                {
                    var bboxInfo = command.FilterCriteria.BoundingBoxIntersect;
                    if (bboxInfo.MinPoint != null && bboxInfo.MaxPoint != null)
                    {
                        XYZ min = new XYZ(bboxInfo.MinPoint.X, bboxInfo.MinPoint.Y, bboxInfo.MinPoint.Z);
                        XYZ max = new XYZ(bboxInfo.MaxPoint.X, bboxInfo.MaxPoint.Y, bboxInfo.MaxPoint.Z);
                        BoundingBoxXYZ bbox = new BoundingBoxXYZ { Min = min, Max = max };
                        elementFilters.Add(new BoundingBoxIntersectsFilter(new Outline(min,max), bboxInfo.IsStrictIntersect));
                        // Note: BoundingBoxIntersectsFilter constructor might vary slightly by API version or need an Outline.
                    }
                }

                // Parameter Filters - These will be applied after the initial collector fetches elements,
                // as combining many ElementParameterFilters with LogicalAndFilter can be complex to build dynamically for all cases.
                // For very large models, it's more efficient to use ElementParameterFilter directly in the collector if possible.

                if (elementFilters.Any()) {
                    if (elementFilters.Count == 1) collector.WherePasses(elementFilters.First());
                    else collector.WherePasses(new LogicalAndFilter(elementFilters));
                }

                IEnumerable<Element> foundElements = collector.ToElements();

                // Post-filter for things harder to do with collector directly or for refinement
                if (!string.IsNullOrEmpty(command.FilterCriteria.FamilyName))
                {
                    foundElements = foundElements.Where(el => el is FamilyInstance fi && fi.Symbol?.Family?.Name.Equals(command.FilterCriteria.FamilyName, StringComparison.OrdinalIgnoreCase) == true);
                }
                if (!string.IsNullOrEmpty(command.FilterCriteria.TypeName)) // FamilySymbol Name
                {
                    foundElements = foundElements.Where(el => el.Name.Equals(command.FilterCriteria.TypeName, StringComparison.OrdinalIgnoreCase) ||
                                                              (el is FamilyInstance fi && fi.Symbol?.Name.Equals(command.FilterCriteria.TypeName, StringComparison.OrdinalIgnoreCase) == true));
                }
                if (!string.IsNullOrEmpty(command.FilterCriteria.LevelId))
                {
                    ElementId levelEid;
                    try { levelEid = new ElementId(long.Parse(command.FilterCriteria.LevelId)); }
                    catch { result["success"] = false; result["message"] = $"Invalid LevelId: {command.FilterCriteria.LevelId}"; SetResult(result.ToString()); return; }
                    foundElements = foundElements.Where(el => el.LevelId == levelEid || el.get_Parameter(BuiltInParameter.INSTANCE_LEVEL_PARAM)?.AsElementId() == levelEid);
                }

                // Apply Parameter Filters (post-collection for more flexibility here)
                if (command.FilterCriteria.ParameterFilters != null && command.FilterCriteria.ParameterFilters.Any())
                {
                    foreach (var pFilterInfo in command.FilterCriteria.ParameterFilters)
                    {
                        foundElements = foundElements.Where(el => {
                            Parameter param = null;
                            if (pFilterInfo.IsSharedParameter) { /* TODO: Handle shared param by GUID */ return false; } // Placeholder
                            else { param = el.LookupParameter(pFilterInfo.ParameterName); }
                            if (param == null) return false;

                            // Basic rule implementation - extend as needed
                            switch (pFilterInfo.FilterRule.ToLowerInvariant()) {
                                case "equals":
                                    if (param.StorageType == StorageType.String) return param.AsString()?.Equals(pFilterInfo.Value.ToString(), pFilterInfo.IsCaseSensitive ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase) == true;
                                    if (param.StorageType == StorageType.Double) return Math.Abs(param.AsDouble() - pFilterInfo.Value.Value<double>()) < 1e-6;
                                    if (param.StorageType == StorageType.Integer) return param.AsInteger() == pFilterInfo.Value.Value<int>();
                                    if (param.StorageType == StorageType.ElementId) return param.AsElementId()?.ToString() == pFilterInfo.Value.ToString();
                                    return false;
                                case "contains": // String only
                                    if (param.StorageType == StorageType.String) return param.AsString()?.IndexOf(pFilterInfo.Value.ToString(), pFilterInfo.IsCaseSensitive ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase) >= 0;
                                    return false;
                                // Add GreaterThan, LessThan, etc.
                                default: return false;
                            }
                        });
                    }
                }


                foreach (Element el in foundElements)
                {
                    JObject elJson = new JObject();
                    elJson["element_id"] = el.Id.ToString();
                    elJson["name"] = el.Name;
                    elJson["type"] = el.Category != null ? el.Category.Name : el.GetType().Name; // Category name if available

                    if (command.IncludeParameters.Any())
                    {
                        JObject paramsJson = new JObject();
                        foreach (string paramName in command.IncludeParameters)
                        {
                            Parameter p = el.LookupParameter(paramName);
                            if (p != null && p.HasValue)
                            {
                                switch (p.StorageType)
                                {
                                    case StorageType.Double: paramsJson[paramName] = p.AsDouble(); break;
                                    case StorageType.Integer: paramsJson[paramName] = p.AsInteger(); break;
                                    case StorageType.String: paramsJson[paramName] = p.AsString(); break;
                                    case StorageType.ElementId: paramsJson[paramName] = p.AsElementId().ToString(); break;
                                    default: paramsJson[paramName] = "N/A (Unhandled StorageType)"; break;
                                }
                            } else {
                                paramsJson[paramName] = null; // Parameter not found or no value
                            }
                        }
                        elJson["parameters"] = paramsJson;
                    }
                    elementsArray.Add(elJson);
                }

                result["success"] = true;
                result["elements"] = elementsArray;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting elements by filter: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
