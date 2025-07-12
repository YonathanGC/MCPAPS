// Standard/Commands/Structural/GetElementParametersCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Structural
{
    public class GetElementParametersCommand : ExternalEventCommandBase
    {
        public string ElementId { get; private set; }
        public List<string> ParameterNames { get; private set; }

        public GetElementParametersCommand(JObject commandParameters) : base(commandParameters)
        {
            ElementId = commandParameters.Value<string>("element_id");
            ParameterNames = commandParameters["parameter_names"]?.ToObject<List<string>>() ?? new List<string>();
        }
    }
}
