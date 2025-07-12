// Standard/Commands/Structural/CreateLevelsAndGridsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Threading;

namespace Standard.Commands.Structural
{
    public class CreateLevelsAndGridsEventHandler : WaitableExternalEventHandlerBase<CreateLevelsAndGridsCommand>
    {
        public override string GetName() => "CreateLevelsAndGridsEventHandler";

        protected override void Execute(UIApplication app, CreateLevelsAndGridsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create {command.Action}");

                    if (command.Action == "create_level")
                    {
                        if (string.IsNullOrEmpty(command.LevelName))
                        {
                            result["success"] = false;
                            result["message"] = "Error creating level: Level name cannot be empty.";
                        }
                        else
                        {
                            Level newLevel = Level.Create(doc, command.Elevation);
                            if (newLevel == null)
                            {
                                result["success"] = false;
                                result["message"] = "Error creating level: Level.Create returned null.";
                            }
                            else
                            {
                                newLevel.Name = command.LevelName;
                                result["success"] = true;
                                result["message"] = $"Level '{command.LevelName}' created successfully.";
                                result["element_id"] = newLevel.Id.ToString();
                            }
                        }
                    }
                    else if (command.Action == "create_grid")
                    {
                        if (string.IsNullOrEmpty(command.GridName))
                        {
                            result["success"] = false;
                            result["message"] = "Error creating grid: Grid name cannot be empty.";
                        }
                        else if (command.StartPoint == null || command.EndPoint == null)
                        {
                            result["success"] = false;
                            result["message"] = "Error creating grid: StartPoint or EndPoint is null.";
                        }
                        else
                        {
                            XYZ start = new XYZ(command.StartPoint.X, command.StartPoint.Y, command.StartPoint.Z);
                            XYZ end = new XYZ(command.EndPoint.X, command.EndPoint.Y, command.EndPoint.Z);
                            Line line = Line.CreateBound(start, end);

                            if (line == null || line.Length < 1e-6) // Check for valid line
                            {
                                result["success"] = false;
                                result["message"] = "Error creating grid: Invalid line geometry (zero length or failed to create).";
                            }
                            else
                            {
                                Grid newGrid = Grid.Create(doc, line);
                                if (newGrid == null)
                                {
                                    result["success"] = false;
                                    result["message"] = "Error creating grid: Grid.Create returned null.";
                                }
                                else
                                {
                                    newGrid.Name = command.GridName;
                                    result["success"] = true;
                                    result["message"] = $"Grid '{command.GridName}' created successfully.";
                                    result["element_id"] = newGrid.Id.ToString();
                                }
                            }
                        }
                    }
                    else
                    {
                        result["success"] = false;
                        result["message"] = "Invalid action specified. Must be 'create_level' or 'create_grid'.";
                    }

                    if ((bool)result["success"])
                    {
                        tx.Commit();
                    }
                    else
                    {
                        if (tx.GetStatus() == TransactionStatus.Started)
                            tx.RollBack();
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating element: {ex.Message}";
                // Ensure transaction is rolled back in case of an unhandled exception
                // This is a simplified error handling. A more robust solution would check transaction status.
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
