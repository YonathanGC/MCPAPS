// Standard/Commands/Structural/CreateStructuralFoundationCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using RevitMCP.SDK.Core.Parameters;
using System.Collections.Generic;

namespace Standard.Commands.Structural
{
    public class CreateStructuralFoundationCommand : ExternalEventCommandBase
    {
        public string FoundationType { get; private set; } // "IsolatedFooting", "WallFooting", "SlabOnGrade"
        public string FamilySymbolName { get; private set; } // For IsolatedFooting or a WallFoundationType name
        public string LevelId { get; private set; }
        public XYZParameter InsertionPoint { get; private set; } // For IsolatedFooting
        public string HostWallId { get; private set; } // For WallFooting
        public string FloorTypeName { get; private set; } // For SlabOnGrade
        public List<List<XYZParameter>> BoundaryLoops { get; private set; } // For SlabOnGrade, list of loops (each loop is a list of points)
        public bool IsStructuralSlab { get; private set; } // For SlabOnGrade

        public CreateStructuralFoundationCommand(JObject commandParameters) : base(commandParameters)
        {
            FoundationType = commandParameters.Value<string>("foundation_type");
            FamilySymbolName = commandParameters.Value<string>("family_symbol_name"); // Used for Isolated or WallFoundationType
            LevelId = commandParameters.Value<string>("level_id");

            if (FoundationType == "IsolatedFooting")
            {
                InsertionPoint = commandParameters["insertion_point"]?.ToObject<XYZParameter>();
            }
            else if (FoundationType == "WallFooting")
            {
                HostWallId = commandParameters.Value<string>("host_wall_id");
            }
            else if (FoundationType == "SlabOnGrade")
            {
                FloorTypeName = commandParameters.Value<string>("floor_type_name");
                BoundaryLoops = commandParameters["boundary_loops"]?.ToObject<List<List<XYZParameter>>>();
                IsStructuralSlab = commandParameters.Value<bool?>("is_structural_slab") ?? true; // Default to true
            }
        }
    }
}
