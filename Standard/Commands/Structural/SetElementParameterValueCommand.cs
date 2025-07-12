// Standard/Commands/Structural/SetElementParameterValueCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Structural
{
    public class SetElementParameterValueCommand : ExternalEventCommandBase
    {
        public string ElementId { get; private set; }
        public string ParameterName { get; private set; }
        public JToken ParameterValue { get; private set; } // Use JToken to handle various types

        public SetElementParameterValueCommand(JObject commandParameters) : base(commandParameters)
        {
            ElementId = commandParameters.Value<string>("element_id");
            ParameterName = commandParameters.Value<string>("parameter_name");
            ParameterValue = commandParameters["parameter_value"];
        }
    }
}
