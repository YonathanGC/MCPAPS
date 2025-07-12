// Standard/Commands/Generic/GetElementsByFilterCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter if used in BBox
using System.Collections.Generic;

namespace Standard.Commands.Generic
{
    public class ParameterFilterInfo
    {
        public string ParameterName { get; set; }
        public string FilterRule { get; set; } // "Equals", "GreaterThan", "LessThan", "Contains", "DoesNotContain", "BeginsWith", "EndsWith"
        public JToken Value { get; set; } // JToken to handle various data types (string, double, int, ElementId as string)
        public bool IsSharedParameter { get; set; } = false; // If true, ParameterName is GUID
        public bool IsCaseSensitive { get; set; } = false; // For string comparisons
    }

    public class BoundingBoxIntersectInfo
    {
        public XYZParameter MinPoint { get; set; }
        public XYZParameter MaxPoint { get; set; }
        public bool IsStrictIntersect { get; set; } = false; // If true, element must be entirely within BBox
    }

    public class ElementFilterCriteria
    {
        public string CategoryName { get; set; } // BuiltInCategory enum name or localized name
        public string ClassName { get; set; } // e.g., "Wall", "FamilyInstance", "Floor"
        public string FamilyName { get; set; }
        public string TypeName { get; set; } // FamilySymbol name
        public string LevelId { get; set; } // ElementId of a Level
        public List<ParameterFilterInfo> ParameterFilters { get; set; }
        public BoundingBoxIntersectInfo BoundingBoxIntersect { get; set; }
        public string ViewId { get; set; } // ElementId of a View to filter elements visible in that view
        public bool ExcludeElementTypes { get; set; } = true; // Generally, we want instances, not types
    }

    public class GetElementsByFilterCommand : ExternalEventCommandBase
    {
        public ElementFilterCriteria FilterCriteria { get; private set; }
        public List<string> IncludeParameters { get; private set; } // Parameters to return for each found element

        public GetElementsByFilterCommand(JObject commandParameters) : base(commandParameters)
        {
            FilterCriteria = commandParameters["filter_criteria"]?.ToObject<ElementFilterCriteria>() ?? new ElementFilterCriteria();
            IncludeParameters = commandParameters["include_parameters"]?.ToObject<List<string>>() ?? new List<string>();
        }
    }
}
