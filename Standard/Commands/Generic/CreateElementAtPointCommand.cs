// Standard/Commands/Generic/CreateElementAtPointCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;

namespace Standard.Commands.Generic
{
    public class CreateElementAtPointCommand : ExternalEventCommandBase
    {
        public string FamilyName { get; private set; }
        public string TypeName { get; private set; } // FamilySymbol name
        public XYZParameter InsertionPoint { get; private set; }
        public string LevelId { get; private set; } // ElementId of the host Level
        public double? RotationDegrees { get; private set; } // Optional: rotation around Z axis of insertion point
        public string StructuralTypeName { get; private set; } // Optional: "NonStructural", "Column", "Beam", etc.

        public CreateElementAtPointCommand(JObject commandParameters) : base(commandParameters)
        {
            FamilyName = commandParameters.Value<string>("family_name");
            TypeName = commandParameters.Value<string>("type_name");
            InsertionPoint = commandParameters["insertion_point"]?.ToObject<XYZParameter>();
            LevelId = commandParameters.Value<string>("level_id");
            RotationDegrees = commandParameters.Value<double?>("rotation_degrees");
            StructuralTypeName = commandParameters.Value<string>("structural_type") ?? "NonStructural"; // Default
        }
    }
}
