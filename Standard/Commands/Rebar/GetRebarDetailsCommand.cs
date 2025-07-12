// Standard/Commands/Rebar/GetRebarDetailsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;

namespace Standard.Commands.Rebar
{
    public class GetRebarDetailsCommand : ExternalEventCommandBase
    {
        public string RebarElementId { get; private set; }

        public GetRebarDetailsCommand(JObject commandParameters) : base(commandParameters)
        {
            RebarElementId = commandParameters.Value<string>("rebar_element_id");
        }
    }
}
