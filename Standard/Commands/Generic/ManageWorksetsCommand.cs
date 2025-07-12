// Standard/Commands/Generic/ManageWorksetsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Generic
{
    public class ManageWorksetsCommand : ExternalEventCommandBase
    {
        public string Action { get; private set; } // "list_worksets", "get_active_workset", "set_active_workset", "create_workset", "get_workset_of_element", "is_element_editable"
        public string WorksetName { get; private set; } // For set_active_workset, create_workset
        public string ElementId { get; private set; } // For get_workset_of_element, is_element_editable

        public ManageWorksetsCommand(JObject commandParameters) : base(commandParameters)
        {
            Action = commandParameters.Value<string>("action");
            WorksetName = commandParameters.Value<string>("workset_name"); // Can be null
            ElementId = commandParameters.Value<string>("element_id"); // Can be null
        }
    }
}
