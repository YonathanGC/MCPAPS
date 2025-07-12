// Standard/Commands/Structural/CreateStructuralFramingCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;

namespace Standard.Commands.Structural
{
    public class CreateStructuralFramingCommand : ExternalEventCommandBase
    {
        public string FamilySymbolName { get; private set; }
        public string LevelId { get; private set; }
        public XYZParameter StartPoint { get; private set; }
        public XYZParameter EndPoint { get; private set; }
        public string StructuralType { get; private set; } // "Beam", "Column", "Brace"
        // Optional parameters for justification, etc.
        public string YZJustification { get; private set; } // e.g., "Top", "Center"
        public double ZOffset { get; private set; }

        public CreateStructuralFramingCommand(JObject commandParameters) : base(commandParameters)
        {
            FamilySymbolName = commandParameters.Value<string>("family_symbol_name");
            LevelId = commandParameters.Value<string>("level_id");
            StartPoint = commandParameters["start_point"]?.ToObject<XYZParameter>();
            EndPoint = commandParameters["end_point"]?.ToObject<XYZParameter>();
            StructuralType = commandParameters.Value<string>("structural_type");

            // Optional
            YZJustification = commandParameters.Value<string>("yz_justification"); // Will be null if not present
            JToken zOffsetToken = commandParameters["z_offset"];
            if (zOffsetToken != null && (zOffsetToken.Type == JTokenType.Float || zOffsetToken.Type == JTokenType.Integer))
            {
                ZOffset = zOffsetToken.Value<double>();
            }
            else
            {
                ZOffset = 0; // Default or indicate not set
            }
        }
    }
}
