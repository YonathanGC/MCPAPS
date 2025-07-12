// Standard/Commands/Generic/GetProjectInfoCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class GetProjectInfoCommand : ExternalEventCommandBase
    {
        public List<string> Fields { get; private set; }

        public GetProjectInfoCommand(JObject commandParameters) : base(commandParameters)
        {
            Fields = commandParameters["fields"]?.ToObject<List<string>>() ?? new List<string>();
        }
    }
}
