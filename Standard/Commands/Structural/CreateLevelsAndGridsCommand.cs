// Standard/Commands/Structural/CreateLevelsAndGridsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;

namespace Standard.Commands.Structural
{
    public class CreateLevelsAndGridsCommand : ExternalEventCommandBase
    {
        public string Action { get; private set; }
        public string LevelName { get; private set; }
        public double Elevation { get; private set; }
        public string GridName { get; private set; }
        public XYZParameter StartPoint { get; private set; }
        public XYZParameter EndPoint { get; private set; }

        public CreateLevelsAndGridsCommand(JObject commandParameters) : base(commandParameters)
        {
            Action = commandParameters.Value<string>("action");

            if (Action == "create_level")
            {
                LevelName = commandParameters.Value<string>("level_name");
                Elevation = commandParameters.Value<double>("elevation");
            }
            else if (Action == "create_grid")
            {
                GridName = commandParameters.Value<string>("grid_name");
                StartPoint = commandParameters["start_point"]?.ToObject<XYZParameter>();
                EndPoint = commandParameters["end_point"]?.ToObject<XYZParameter>();
            }
        }
    }
}
