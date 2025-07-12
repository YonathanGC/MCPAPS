// Standard/Commands/Generic/GetAvailableViewsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class GetAvailableViewsEventHandler : WaitableExternalEventHandlerBase<GetAvailableViewsCommand>
    {
        public override string GetName() => "GetAvailableViewsEventHandler";

        protected override void Execute(UIApplication app, GetAvailableViewsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JArray viewsArray = new JArray();

            try
            {
                FilteredElementCollector collector = new FilteredElementCollector(doc).OfClass(typeof(View));
                IEnumerable<View> views = collector.Cast<View>();

                if (command.ExcludeTemplates)
                {
                    views = views.Where(v => !v.IsTemplate);
                }

                if (!string.IsNullOrEmpty(command.ViewTypeFilter))
                {
                    ViewType targetViewType;
                    if (Enum.TryParse<ViewType>(command.ViewTypeFilter, true, out targetViewType))
                    {
                        views = views.Where(v => v.ViewType == targetViewType);
                    }
                    else
                    {
                        // Optional: could add a more forgiving filter if Enum.TryParse fails,
                        // e.g. by checking v.GetType().Name against command.ViewTypeFilter
                        // For now, strict enum matching.
                         result["success"] = false;
                         result["message"] = $"Invalid ViewTypeFilter: '{command.ViewTypeFilter}'. Not a recognized ViewType enum value.";
                         SetResult(result.ToString());
                         return;
                    }
                }

                foreach (View view in views)
                {
                    // Additional check to filter out some internal or less relevant view types if not specifically requested
                    if (string.IsNullOrEmpty(command.ViewTypeFilter)) {
                        if (view.ViewType == ViewType.Internal ||
                            view.ViewType == ViewType.ProjectBrowser ||
                            view.ViewType == ViewType.SystemBrowser ||
                            view.ViewType == ViewType.Undefined) {
                            continue;
                        }
                    }

                    JObject viewJson = new JObject();
                    viewJson["id"] = view.Id.ToString();
                    viewJson["name"] = view.Name;
                    viewJson["view_type"] = view.ViewType.ToString();

                    // Add other relevant properties if needed, e.g., Scale, DetailLevel
                    try { // Scale might not be applicable to all view types (e.g. Schedules, 3D views often 0)
                        if (view.CanModifyViewDiscipline() && view.get_Parameter(BuiltInParameter.VIEW_SCALE) != null) { // A check if scale is typical
                             viewJson["scale"] = view.Scale;
                        } else {
                             viewJson["scale"] = 0; // Or "N/A"
                        }
                    } catch { viewJson["scale"] = "N/A (Error or not applicable)";}


                    viewsArray.Add(viewJson);
                }

                result["success"] = true;
                result["views"] = viewsArray;

            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting available views: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
