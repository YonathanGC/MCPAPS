// Standard/Commands/Rebar/PlaceRebarInHostCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;
using System.Collections.Generic;

namespace Standard.Commands.Rebar
{
    public class PlaceRebarInHostCommand : ExternalEventCommandBase
    {
        public string HostElementId { get; private set; }
        public string RebarBarTypeName { get; private set; }
        public string RebarShapeName { get; private set; }
        public string LayoutRule { get; private set; }

        // Layout-dependent parameters
        public int? Quantity { get; private set; }
        public double? Spacing { get; private set; } // In project internal units (feet)
        public double? ArrayLength { get; private set; } // In project internal units (feet)

        // Geometry for standard layouts
        public XYZParameter NormalToPlaneVector { get; private set; } // Normal to the plane of the rebar set
        public XYZParameter OriginPoint { get; private set; } // Defines rebar plane and start position
        public XYZParameter ShapeOrientationVector { get; private set; } // 'X' direction of RebarShape

        // For PathReinforcement (Conceptual - path reinforcement is more complex)
        // public List<List<XYZParameter>> PathCurves { get; private set; }
        // public XYZParameter PathFaceNormal { get; private set; }
        // public double? PrimaryBarSpacing { get; private set; }

        public string HookAtStartTypeName { get; private set; } // Optional
        public string HookAtEndTypeName { get; private set; } // Optional

        public PlaceRebarInHostCommand(JObject commandParameters) : base(commandParameters)
        {
            HostElementId = commandParameters.Value<string>("host_element_id");
            RebarBarTypeName = commandParameters.Value<string>("rebar_bar_type_name");
            RebarShapeName = commandParameters.Value<string>("rebar_shape_name");
            LayoutRule = commandParameters.Value<string>("layout_rule");

            Quantity = commandParameters.Value<int?>("quantity");
            Spacing = commandParameters.Value<double?>("spacing");
            ArrayLength = commandParameters.Value<double?>("array_length");

            NormalToPlaneVector = commandParameters["normal_to_plane_vector"]?.ToObject<XYZParameter>();
            OriginPoint = commandParameters["origin_point"]?.ToObject<XYZParameter>();
            ShapeOrientationVector = commandParameters["shape_orientation_vector"]?.ToObject<XYZParameter>();

            HookAtStartTypeName = commandParameters.Value<string>("hook_at_start_type_name");
            HookAtEndTypeName = commandParameters.Value<string>("hook_at_end_type_name");
        }
    }
}
