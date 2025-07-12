// Standard/Commands/Generic/CreateNewViewEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using RevitMCP.SDK.Core.Parameters; // For XYZParameter
using System;
using System.Linq;

namespace Standard.Commands.Generic
{
    public class CreateNewViewEventHandler : WaitableExternalEventHandlerBase<CreateNewViewCommand>
    {
        public override string GetName() => "CreateNewViewEventHandler";

        protected override void Execute(UIApplication app, CreateNewViewCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            View newView = null;

            try
            {
                if (string.IsNullOrEmpty(command.ViewTypeName) || string.IsNullOrEmpty(command.ViewName))
                {
                    result["success"] = false; result["message"] = "ViewTypeName and ViewName are required.";
                    SetResult(result.ToString()); return;
                }

                ViewFamilyType viewFamilyType = null;
                Level level = null;

                if (command.ViewTypeName.Equals("FloorPlan", StringComparison.OrdinalIgnoreCase) ||
                    command.ViewTypeName.Equals("CeilingPlan", StringComparison.OrdinalIgnoreCase))
                {
                    if (string.IsNullOrEmpty(command.LevelId)) {
                        result["success"] = false; result["message"] = "LevelId is required for FloorPlan/CeilingPlan.";
                        SetResult(result.ToString()); return;
                    }
                    ElementId levelEid;
                    try { levelEid = new ElementId(long.Parse(command.LevelId)); }
                    catch { result["success"] = false; result["message"] = $"Invalid LevelId: {command.LevelId}"; SetResult(result.ToString()); return; }
                    level = doc.GetElement(levelEid) as Level;
                    if (level == null) { result["success"] = false; result["message"] = $"Level with ID '{command.LevelId}' not found."; SetResult(result.ToString()); return; }

                    ViewFamily viewFamily = command.ViewTypeName.Equals("FloorPlan", StringComparison.OrdinalIgnoreCase) ? ViewFamily.FloorPlan : ViewFamily.CeilingPlan;
                    viewFamilyType = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(vft => vft.ViewFamily == viewFamily);

                    if (viewFamilyType == null) { result["success"] = false; result["message"] = $"No default ViewFamilyType found for {command.ViewTypeName}."; SetResult(result.ToString()); return; }
                }
                else if (command.ViewTypeName.Equals("ThreeD", StringComparison.OrdinalIgnoreCase))
                {
                    viewFamilyType = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(vft => vft.ViewFamily == ViewFamily.ThreeDimensional);
                     if (viewFamilyType == null) { result["success"] = false; result["message"] = "No default ViewFamilyType found for 3D views."; SetResult(result.ToString()); return; }
                }
                else if (command.ViewTypeName.Equals("Section", StringComparison.OrdinalIgnoreCase))
                {
                     viewFamilyType = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(vft => vft.ViewFamily == ViewFamily.Section);
                    if (viewFamilyType == null) { result["success"] = false; result["message"] = "No default ViewFamilyType found for Section views."; SetResult(result.ToString()); return; }
                    if (command.SectionLineStart == null || command.SectionLineEnd == null || command.SectionViewDirection == null) {
                        result["success"] = false; result["message"] = "SectionLineStart, SectionLineEnd, and SectionViewDirection are required for Section views.";
                        SetResult(result.ToString()); return;
                    }
                }
                // Add more types: Elevation, Schedule, Legend, DraftingView as needed.


                using (Transaction tx = new Transaction(doc))
                {
                    tx.Start($"MCP Create View: {command.ViewName}");

                    if (command.ViewTypeName.Equals("FloorPlan", StringComparison.OrdinalIgnoreCase))
                    {
                        newView = ViewPlan.Create(doc, viewFamilyType.Id, level.Id);
                    }
                    else if (command.ViewTypeName.Equals("CeilingPlan", StringComparison.OrdinalIgnoreCase))
                    {
                        newView = ViewPlan.Create(doc, viewFamilyType.Id, level.Id);
                    }
                    else if (command.ViewTypeName.Equals("ThreeD", StringComparison.OrdinalIgnoreCase))
                    {
                        newView = View3D.CreateIsometric(doc, viewFamilyType.Id);
                    }
                    else if (command.ViewTypeName.Equals("Section", StringComparison.OrdinalIgnoreCase))
                    {
                        XYZ p1 = new XYZ(command.SectionLineStart.X, command.SectionLineStart.Y, command.SectionLineStart.Z);
                        XYZ p2 = new XYZ(command.SectionLineEnd.X, command.SectionLineEnd.Y, command.SectionLineEnd.Z);
                        XYZ dir = new XYZ(command.SectionViewDirection.X, command.SectionViewDirection.Y, command.SectionViewDirection.Z).Normalize();

                        // Create a bounding box for the section view
                        // This defines the crop region extents perpendicular to the section line and the far clip.
                        // For simplicity, creating a generic BBox around the section line.
                        // A more precise BBox would depend on model extents or user input.
                        XYZ midPoint = (p1 + p2) / 2.0;
                        XYZ lineDir = (p2 - p1).Normalize();
                        XYZ up = XYZ.BasisZ; // Assuming sections are generally vertical cuts in plan
                        if (Math.Abs(lineDir.DotProduct(XYZ.BasisZ)) > 0.99) up = XYZ.BasisY; // If line is vertical, use Y for up.

                        Transform transform = Transform.Identity;
                        transform.Origin = midPoint;
                        transform.BasisX = lineDir;
                        transform.BasisY = up.CrossProduct(lineDir).Normalize(); // right vector
                        transform.BasisZ = up; // This might need to be dir if section is not plan-cut. For true section, BasisZ is view direction.
                                               // Let's use view direction as Z for the BBox transform
                        transform.BasisZ = dir;
                        transform.BasisY = dir.CrossProduct(lineDir).Normalize();


                        BoundingBoxXYZ sectionBBox = new BoundingBoxXYZ();
                        sectionBBox.Transform = transform;
                        // Define extents of BBox (min/max points relative to the transform origin)
                        double sectionDepth = command.SectionFarClipOffset;
                        double sectionWidth = (p1.DistanceTo(p2))/2 + 5; // Arbitrary width beyond line ends
                        double sectionHeight = 10; // Arbitrary height

                        sectionBBox.Min = new XYZ(-sectionWidth, -sectionHeight/2, 0); // Min along line, min height, near clip (0)
                        sectionBBox.Max = new XYZ(sectionWidth, sectionHeight/2, sectionDepth); // Max along line, max height, far clip

                        newView = ViewSection.CreateSection(doc, viewFamilyType.Id, sectionBBox);
                    }
                    else
                    {
                        result["success"] = false; result["message"] = $"ViewType '{command.ViewTypeName}' creation not yet implemented or invalid.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }

                    if (newView == null)
                    {
                        result["success"] = false; result["message"] = "Failed to create view. Creation method returned null.";
                        if (tx.GetStatus() == TransactionStatus.Started) tx.RollBack(); SetResult(result.ToString()); return;
                    }

                    newView.Name = command.ViewName;

                    if (command.Scale.HasValue && newView.CanModifyViewScale())
                    {
                        newView.Scale = command.Scale.Value;
                    }

                    if (command.SectionBoxMin != null && command.SectionBoxMax != null && newView.CanUseSectionBox())
                    {
                        BoundingBoxXYZ sbox = new BoundingBoxXYZ
                        {
                            Min = new XYZ(command.SectionBoxMin.X, command.SectionBoxMin.Y, command.SectionBoxMin.Z),
                            Max = new XYZ(command.SectionBoxMax.X, command.SectionBoxMax.Y, command.SectionBoxMax.Z)
                        };
                        if (sbox.Min.X < sbox.Max.X && sbox.Min.Y < sbox.Max.Y && sbox.Min.Z < sbox.Max.Z) // Basic validation
                        {
                             newView.SetSectionBox(sbox);
                             // For some view types (like View3D), you might also need to activate the section box:
                             Parameter sectionBoxParam = newView.get_Parameter(BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP);
                             if (sectionBoxParam != null && !sectionBoxParam.IsReadOnly) sectionBoxParam.Set(1); // 1 for true
                        }
                    }

                    result["success"] = true;
                    result["message"] = $"View '{command.ViewName}' ({command.ViewTypeName}) created successfully.";
                    result["view_id"] = newView.Id.ToString();
                    tx.Commit();
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error creating new view: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
