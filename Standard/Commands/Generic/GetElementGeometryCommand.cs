// Standard/Commands/Generic/GetElementGeometryCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Generic
{
    public class GetElementGeometryOptions
    {
        public bool IncludeBoundingBox { get; set; } = true;
        public bool IncludeCurves { get; set; } = true;
        public bool IncludeInsertionPoint { get; set; } = true;
        public bool IncludeSolidGeometryDetails { get; set; } = false; // Potentially heavy
        public string ViewIdForBoundingBox { get; set; } // Optional: ElementId of a View for view-specific BBox
    }

    public class GetElementGeometryCommand : ExternalEventCommandBase
    {
        public string ElementId { get; private set; }
        public GetElementGeometryOptions Options { get; private set; }

        public GetElementGeometryCommand(JObject commandParameters) : base(commandParameters)
        {
            ElementId = commandParameters.Value<string>("element_id");
            Options = commandParameters["options"]?.ToObject<GetElementGeometryOptions>() ?? new GetElementGeometryOptions();
        }
    }
}
