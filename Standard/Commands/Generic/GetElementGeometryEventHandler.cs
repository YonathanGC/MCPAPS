// Standard/Commands/Generic/GetElementGeometryEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Linq;
using System.Text; // For StringBuilder if creating WKT

namespace Standard.Commands.Generic
{
    public class GetElementGeometryEventHandler : WaitableExternalEventHandlerBase<GetElementGeometryCommand>
    {
        public override string GetName() => "GetElementGeometryEventHandler";

        // Helper to convert XYZ to JObject
        private JObject XyzToJson(XYZ point)
        {
            if (point == null) return null;
            return new JObject { { "X", point.X }, { "Y", point.Y }, { "Z", point.Z } };
        }

        // Helper to convert Curve to a simplified WKT-like string
        private string CurveToWkt(Curve curve)
        {
            if (curve == null) return null;
            if (curve is Line line)
            {
                return $"LINESTRING ({line.GetEndPoint(0).X} {line.GetEndPoint(0).Y} {line.GetEndPoint(0).Z}, {line.GetEndPoint(1).X} {line.GetEndPoint(1).Y} {line.GetEndPoint(1).Z})";
            }
            else if (curve is Arc arc)
            {
                // Arc WKT is more complex, for now a simplified representation
                return $"ARC (Center: {XyzToJson(arc.Center)}, Radius: {arc.Radius}, StartAngle: {arc.GetEndParameter(0)}, EndAngle: {arc.GetEndParameter(1)})";
            }
            // Add more curve types if needed (Ellipse, NurbsSpline)
            return $"CURVETYPE ({curve.GetType().Name})";
        }


        protected override void Execute(UIApplication app, GetElementGeometryCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();
            JObject geometryData = new JObject();

            try
            {
                ElementId eid;
                try { eid = new ElementId(long.Parse(command.ElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid ElementId: {command.ElementId}"; SetResult(result.ToString()); return; }

                Element element = doc.GetElement(eid);
                if (element == null)
                {
                    result["success"] = false; result["message"] = $"Element with ID '{command.ElementId}' not found.";
                    SetResult(result.ToString()); return;
                }

                result["success"] = true;
                result["element_id"] = command.ElementId;

                // BoundingBox
                if (command.Options.IncludeBoundingBox)
                {
                    BoundingBoxXYZ bbox = null;
                    if (!string.IsNullOrEmpty(command.Options.ViewIdForBoundingBox)) {
                        ElementId viewEid;
                        try {
                            viewEid = new ElementId(long.Parse(command.Options.ViewIdForBoundingBox));
                            View specificView = doc.GetElement(viewEid) as View;
                            if (specificView != null) bbox = element.get_BoundingBox(specificView);
                            else geometryData["bounding_box_error"] = $"View with ID '{command.Options.ViewIdForBoundingBox}' not found for BBox.";
                        } catch {
                             geometryData["bounding_box_error"] = $"Invalid ViewId for BBox: '{command.Options.ViewIdForBoundingBox}'.";
                        }
                    }
                    if (bbox == null) { // Fallback to model BBox or if no view was specified
                         bbox = element.get_BoundingBox(null);
                    }

                    if (bbox != null)
                    {
                        geometryData["bounding_box_xyz"] = new JObject {
                            { "min_point", XyzToJson(bbox.Min) },
                            { "max_point", XyzToJson(bbox.Max) }
                        };
                    } else {
                        geometryData["bounding_box_xyz"] = "N/A (Could not retrieve)";
                    }
                }

                // Location Curve (for linear elements)
                if (command.Options.IncludeCurves && element.Location is LocationCurve locationCurve)
                {
                    geometryData["location_curve_wkt"] = CurveToWkt(locationCurve.Curve);
                }

                // Insertion Point (for FamilyInstance)
                if (command.Options.IncludeInsertionPoint && element.Location is LocationPoint locationPoint)
                {
                    geometryData["insertion_point_xyz"] = XyzToJson(locationPoint.Point);
                    // Also include rotation for FamilyInstance
                    if (element is FamilyInstance fi) {
                         geometryData["insertion_point_rotation_degrees"] = fi.GetTransform().BasisZ.AngleOnPlaneTo(XYZ.BasisY, XYZ.BasisX) * (180.0 / Math.PI); // Rotation around Z
                    }
                }

                // Solid Geometry Details (Conceptual - can be very heavy)
                if (command.Options.IncludeSolidGeometryDetails)
                {
                    JObject solidDetails = new JObject();
                    long totalVertices = 0;
                    long totalTriangles = 0; // Revit solids are often BRep, direct triangles might need tessellation.
                    long solidCount = 0;

                    Options geomOptions = new Options();
                    // geomOptions.ComputeReferences = true; // If you need stable references
                    // geomOptions.DetailLevel = ViewDetailLevel.Fine; // Or as needed
                    // geomOptions.IncludeNonVisibleObjects = false;

                    GeometryElement geomElement = element.get_Geometry(geomOptions);
                    if (geomElement != null)
                    {
                        foreach (GeometryObject geomObj in geomElement)
                        {
                            if (geomObj is Solid solid)
                            {
                                solidCount++;
                                totalVertices += solid.Vertices.Size;
                                // totalTriangles += solid.Triangles.Size; // Solid.Triangles is not directly available.
                                // You'd typically iterate through faces and then triangulate them if needed.
                                // For simplicity, we'll just count faces.
                                solidDetails["solid_face_count_" + solidCount] = solid.Faces.Size;
                            }
                            else if (geomObj is GeometryInstance instance)
                            {
                                // Recurse or process instanced geometry
                                GeometryElement instanceGeom = instance.GetInstanceGeometry();
                                foreach (GeometryObject instObj in instanceGeom) {
                                     if (instObj is Solid s) {
                                        solidCount++;
                                        totalVertices += s.Vertices.Size;
                                        solidDetails["instanced_solid_face_count_" + solidCount] = s.Faces.Size;
                                     }
                                }
                            }
                        }
                    }
                    solidDetails["detected_solid_object_count"] = solidCount;
                    solidDetails["total_vertices_in_solids"] = totalVertices;
                    geometryData["solid_details_summary"] = solidDetails;
                }

                result["geometry_data"] = geometryData;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting element geometry: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
