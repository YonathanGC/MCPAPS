// Standard/Commands/Structural/DefineLoadCasesAndCombinationsCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic;

namespace Standard.Commands.Structural
{
    public class LoadCombinationComponentInfo
    {
        public string CaseId { get; set; } // ElementId of the LoadCase
        public double Factor { get; set; }
    }

    public class DefineLoadCasesAndCombinationsCommand : ExternalEventCommandBase
    {
        public string Action { get; private set; } // "create_case", "create_combination"

        // For create_case
        public string CaseName { get; private set; }
        public string Nature { get; private set; } // e.g., "Dead", "Live", "Wind", "Snow", "Accidental"
        public string CategoryName { get; private set; } // Optional: If not provided, might use default based on nature

        // For create_combination
        public string CombinationName { get; private set; }
        public string CombinationType { get; private set; } // e.g., "Combination", "Envelope"
        public List<LoadCombinationComponentInfo> Components { get; private set; }

        public DefineLoadCasesAndCombinationsCommand(JObject commandParameters) : base(commandParameters)
        {
            Action = commandParameters.Value<string>("action");

            if (Action == "create_case")
            {
                CaseName = commandParameters.Value<string>("case_name");
                Nature = commandParameters.Value<string>("nature");
                CategoryName = commandParameters.Value<string>("category_name"); // Can be null
            }
            else if (Action == "create_combination")
            {
                CombinationName = commandParameters.Value<string>("combination_name");
                CombinationType = commandParameters.Value<string>("combination_type");
                Components = commandParameters["components"]?.ToObject<List<LoadCombinationComponentInfo>>() ?? new List<LoadCombinationComponentInfo>();
            }
        }
    }
}
