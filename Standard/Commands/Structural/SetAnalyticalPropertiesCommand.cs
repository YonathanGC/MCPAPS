// Standard/Commands/Structural/SetAnalyticalPropertiesCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Structural
{
    public class BoundaryConditionState
    {
        // States: "Fixed", "Released", "Spring" (Revit API uses enum or boolean)
        public string TranslationX { get; set; }
        public string TranslationY { get; set; }
        public string TranslationZ { get; set; }
        public string RotationX { get; set; }
        public string RotationY { get; set; }
        public string RotationZ { get; set; }
        // Spring moduli if "Spring"
        public double? SpringModulusTX { get; set; }
        public double? SpringModulusTY { get; set; }
        public double? SpringModulusTZ { get; set; }
        public double? SpringModulusRX { get; set; }
        public double? SpringModulusRY { get; set; }
        public double? SpringModulusRZ { get; set; }
    }

    public class EndReleasesState
    {
        public bool? StartMx { get; set; } // True if released
        public bool? StartMy { get; set; }
        public bool? StartMz { get; set; }
        public bool? EndMx { get; set; }
        public bool? EndMy { get; set; }
        public bool? EndMz { get; set; }
        // Could also include translational releases if applicable (Fx, Fy, Fz)
    }

    public class SetAnalyticalPropertiesCommand : ExternalEventCommandBase
    {
        public string ElementId { get; private set; }
        public string PropertyType { get; private set; } // "boundary_conditions", "end_releases"
        public BoundaryConditionState BoundaryConditions { get; private set; }
        public EndReleasesState EndReleases { get; private set; }

        public SetAnalyticalPropertiesCommand(JObject commandParameters) : base(commandParameters)
        {
            ElementId = commandParameters.Value<string>("element_id");
            PropertyType = commandParameters.Value<string>("property_type");

            if (PropertyType == "boundary_conditions")
            {
                BoundaryConditions = commandParameters["boundary_conditions"]?.ToObject<BoundaryConditionState>();
            }
            else if (PropertyType == "end_releases")
            {
                EndReleases = commandParameters["end_releases"]?.ToObject<EndReleasesState>();
            }
        }
    }
}
