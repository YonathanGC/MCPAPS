// Standard/Commands/Structural/GetAnalyticalModelDataCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic;

namespace Standard.Commands.Structural
{
    public class GetAnalyticalModelDataCommand : ExternalEventCommandBase
    {
        public string Scope { get; private set; } // "full_model", "element_ids"
        public List<string> ElementIds { get; private set; } // Optional, if scope is "element_ids"
        public bool IncludeLoads { get; private set; }
        public bool IncludeBoundaryConditions { get; private set; }
        public bool IncludeReleases { get; private set; }


        public GetAnalyticalModelDataCommand(JObject commandParameters) : base(commandParameters)
        {
            Scope = commandParameters.Value<string>("scope") ?? "full_model"; // Default to full_model
            ElementIds = commandParameters["element_ids"]?.ToObject<List<string>>() ?? new List<string>();
            IncludeLoads = commandParameters.Value<bool?>("include_loads") ?? true;
            IncludeBoundaryConditions = commandParameters.Value<bool?>("include_boundary_conditions") ?? true;
            IncludeReleases = commandParameters.Value<bool?>("include_releases") ?? true;
        }
    }
}
