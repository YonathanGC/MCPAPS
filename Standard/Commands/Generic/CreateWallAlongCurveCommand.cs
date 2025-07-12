// Standard/Commands/Generic/CreateWallAlongCurveCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;
using System.Collections.Generic;

namespace Standard.Commands.Generic
{
    public class CreateWallAlongCurveCommand : ExternalEventCommandBase
    {
        public string WallTypeName { get; private set; }
        public string LevelId { get; private set; }
        public List<XYZParameter> PathPoints { get; private set; } // List of points defining the wall path
        public double Height { get; private set; } // Unconnected height
        public bool IsStructural { get; private set; }
        public string LocationLine { get; private set; } // e.g., "WallCenterline", "CoreCenterline", etc.
        public double BaseOffset { get; private set; } // Optional base offset from level

        public CreateWallAlongCurveCommand(JObject commandParameters) : base(commandParameters)
        {
            WallTypeName = commandParameters.Value<string>("wall_type_name");
            LevelId = commandParameters.Value<string>("level_id");
            PathPoints = commandParameters["path_points"]?.ToObject<List<XYZParameter>>() ?? new List<XYZParameter>();
            Height = commandParameters.Value<double?>("height") ?? 0; // Default to 0, but should be validated
            IsStructural = commandParameters.Value<bool?>("is_structural") ?? false;
            LocationLine = commandParameters.Value<string>("location_line"); // Can be null
            BaseOffset = commandParameters.Value<double?>("base_offset") ?? 0.0;
        }
    }
}
