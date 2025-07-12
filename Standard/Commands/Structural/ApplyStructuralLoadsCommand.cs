// Standard/Commands/Structural/ApplyStructuralLoadsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;
using System.Collections.Generic;

namespace Standard.Commands.Structural
{
    public class ApplyStructuralLoadsCommand : ExternalEventCommandBase
    {
        public string LoadType { get; private set; } // "PointLoad", "LineLoad", "AreaLoad"
        public string HostElementId { get; private set; }
        public string LoadCaseId { get; private set; }
        public XYZParameter ForceVector { get; private set; } // For PointLoad, LineLoad (force per unit length)
        public XYZParameter MomentVector { get; private set; } // Optional

        // For PointLoad
        public XYZParameter PointLocation { get; private set; } // If on linear element, could be actual coords or normalized (0-1)
                                                              // If on area/surface, XYZ world coordinate.

        // For LineLoad (if varying, Start and End vectors)
        public XYZParameter ForceVectorEnd { get; private set; } // Optional, for varying line load
        public XYZParameter MomentVectorEnd { get; private set; } // Optional, for varying line load
        public List<XYZParameter> LineLoadPath { get; private set; } // Optional: if line load is not directly on host element's curve but on a defined path.

        // For AreaLoad
        public List<List<XYZParameter>> AreaLoadBoundaryLoops { get; private set; } // List of loops, if not on entire element surface.
        public bool IsProjectedLoad { get; private set; }

        public ApplyStructuralLoadsCommand(JObject commandParameters) : base(commandParameters)
        {
            LoadType = commandParameters.Value<string>("load_type");
            HostElementId = commandParameters.Value<string>("host_element_id");
            LoadCaseId = commandParameters.Value<string>("load_case_id");

            ForceVector = commandParameters["force_vector"]?.ToObject<XYZParameter>();
            MomentVector = commandParameters["moment_vector"]?.ToObject<XYZParameter>(); // Can be null

            if (LoadType == "PointLoad")
            {
                PointLocation = commandParameters["point_location"]?.ToObject<XYZParameter>();
            }
            else if (LoadType == "LineLoad")
            {
                ForceVectorEnd = commandParameters["force_vector_end"]?.ToObject<XYZParameter>(); // Can be null
                MomentVectorEnd = commandParameters["moment_vector_end"]?.ToObject<XYZParameter>(); // Can be null
                LineLoadPath = commandParameters["line_load_path"]?.ToObject<List<XYZParameter>>(); // Can be null
            }
            else if (LoadType == "AreaLoad")
            {
                AreaLoadBoundaryLoops = commandParameters["area_load_boundary_loops"]?.ToObject<List<List<XYZParameter>>>(); // Can be null
                IsProjectedLoad = commandParameters.Value<bool?>("is_projected_load") ?? false;
            }
        }
    }
}
