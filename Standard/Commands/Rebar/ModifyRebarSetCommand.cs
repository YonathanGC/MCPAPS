// Standard/Commands/Rebar/ModifyRebarSetCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Rebar
{
    public class ModifyRebarSetCommand : ExternalEventCommandBase
    {
        public string RebarElementId { get; private set; }

        // Optional parameters to modify
        public int? Quantity { get; private set; }
        public double? Spacing { get; private set; } // In project internal units (feet)
        public double? ArrayLength { get; private set; } // In project internal units (feet)
        public string RebarBarTypeName { get; private set; } // New BarType name
        public string HookAtStartTypeName { get; private set; } // New HookType name or null to remove
        public string HookAtEndTypeName { get; private set; }   // New HookType name or null to remove

        // Note: Changing LayoutRule or RebarShape is complex and often requires recreating the rebar.
        // So, those are not included as simple modification parameters here.

        public ModifyRebarSetCommand(JObject commandParameters) : base(commandParameters)
        {
            RebarElementId = commandParameters.Value<string>("rebar_element_id");

            Quantity = commandParameters.Value<int?>("quantity");
            Spacing = commandParameters.Value<double?>("spacing");
            ArrayLength = commandParameters.Value<double?>("array_length");
            RebarBarTypeName = commandParameters.Value<string>("rebar_bar_type_name");
            HookAtStartTypeName = commandParameters.Value<string>("hook_at_start_type_name");
            HookAtEndTypeName = commandParameters.Value<string>("hook_at_end_type_name");
        }
    }
}
