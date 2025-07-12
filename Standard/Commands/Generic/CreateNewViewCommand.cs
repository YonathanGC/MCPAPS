// Standard/Commands/Generic/CreateNewViewCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter

namespace Standard.Commands.Generic
{
    public class CreateNewViewCommand : ExternalEventCommandBase
    {
        public string ViewTypeName { get; private set; } // "FloorPlan", "CeilingPlan", "Section", "ThreeD", etc.
        public string ViewName { get; private set; }
        public string LevelId { get; private set; } // Required for Plan views
        public XYZParameter SectionBoxMin { get; private set; } // Optional for 3D/Section
        public XYZParameter SectionBoxMax { get; private set; } // Optional for 3D/Section
        public int? Scale { get; private set; } // Optional, e.g., 100 for 1:100

        // For Section views:
        public XYZParameter SectionLineStart { get; private set; }
        public XYZParameter SectionLineEnd { get; private set; }
        public XYZParameter SectionViewDirection { get; private set; } // Vector perpendicular to section line
        public double SectionFarClipOffset { get; private set; }


        public CreateNewViewCommand(JObject commandParameters) : base(commandParameters)
        {
            ViewTypeName = commandParameters.Value<string>("view_type_name");
            ViewName = commandParameters.Value<string>("view_name");
            LevelId = commandParameters.Value<string>("level_id");
            SectionBoxMin = commandParameters["section_box_min"]?.ToObject<XYZParameter>();
            SectionBoxMax = commandParameters["section_box_max"]?.ToObject<XYZParameter>();
            Scale = commandParameters.Value<int?>("scale");

            if (ViewTypeName?.Equals("Section", System.StringComparison.OrdinalIgnoreCase) == true)
            {
                SectionLineStart = commandParameters["section_line_start"]?.ToObject<XYZParameter>();
                SectionLineEnd = commandParameters["section_line_end"]?.ToObject<XYZParameter>();
                SectionViewDirection = commandParameters["section_view_direction"]?.ToObject<XYZParameter>();
                SectionFarClipOffset = commandParameters.Value<double?>("section_far_clip_offset") ?? 20.0; // Default far clip
            }
        }
    }
}
