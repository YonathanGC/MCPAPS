// Standard/Commands/Structural/ExportToRobotFormatCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic;

namespace Standard.Commands.Structural
{
    public class ExportOptionsInfo
    {
        public bool? IncludeSelfWeight { get; set; }
        public List<string> SelectedLoadCaseIds { get; set; } // ElementIds of LoadCases
        // Add other relevant export options as needed
    }

    public class ExportToRobotFormatCommand : ExternalEventCommandBase
    {
        public string OutputFilePath { get; private set; } // Full path for the .smxx file
        public ExportOptionsInfo ExportOptions { get; private set; }

        public ExportToRobotFormatCommand(JObject commandParameters) : base(commandParameters)
        {
            OutputFilePath = commandParameters.Value<string>("output_file_path");
            ExportOptions = commandParameters["export_options"]?.ToObject<ExportOptionsInfo>() ?? new ExportOptionsInfo();
        }
    }
}
