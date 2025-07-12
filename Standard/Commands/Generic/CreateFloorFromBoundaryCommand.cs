// Standard/Commands/Generic/CreateFloorFromBoundaryCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;
using System.Collections.Generic;

namespace Standard.Commands.Generic
{
    public class CreateFloorFromBoundaryCommand : ExternalEventCommandBase
    {
        public string FloorTypeName { get; private set; }
        public string LevelId { get; private set; }
        public List<List<XYZParameter>> BoundaryLoops { get; private set; } // List of loops; first is exterior, others are openings.
        public bool IsStructural { get; private set; }
        public double OffsetFromLevel { get; private set; } // In project internal units (feet)

        public CreateFloorFromBoundaryCommand(JObject commandParameters) : base(commandParameters)
        {
            FloorTypeName = commandParameters.Value<string>("floor_type_name");
            LevelId = commandParameters.Value<string>("level_id");
            BoundaryLoops = commandParameters["boundary_loops"]?.ToObject<List<List<XYZParameter>>>() ?? new List<List<XYZParameter>>();
            IsStructural = commandParameters.Value<bool?>("is_structural") ?? false;
            OffsetFromLevel = commandParameters.Value<double?>("offset_from_level") ?? 0.0;
        }
    }
}
