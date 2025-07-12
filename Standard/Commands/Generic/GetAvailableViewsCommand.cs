// Standard/Commands/Generic/GetAvailableViewsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Generic
{
    public class GetAvailableViewsCommand : ExternalEventCommandBase
    {
        public string ViewTypeFilter { get; private set; } // e.g., "FloorPlan", "ThreeD", "Section", etc.
        public bool ExcludeTemplates { get; private set; }

        public GetAvailableViewsCommand(JObject commandParameters) : base(commandParameters)
        {
            ViewTypeFilter = commandParameters.Value<string>("view_type_filter"); // Can be null or empty
            ExcludeTemplates = commandParameters.Value<bool?>("exclude_templates") ?? true; // Default to excluding templates
        }
    }
}
