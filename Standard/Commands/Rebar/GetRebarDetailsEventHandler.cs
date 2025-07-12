// Standard/Commands/Rebar/GetRebarDetailsEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace Standard.Commands.Rebar
{
    public class GetRebarDetailsEventHandler : WaitableExternalEventHandlerBase<GetRebarDetailsCommand>
    {
        public override string GetName() => "GetRebarDetailsEventHandler";

        protected override void Execute(UIApplication app, GetRebarDetailsCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                ElementId rebarEid;
                try { rebarEid = new ElementId(long.Parse(command.RebarElementId)); }
                catch { result["success"] = false; result["message"] = $"Invalid RebarElementId: {command.RebarElementId}"; SetResult(result.ToString()); return; }

                Autodesk.Revit.DB.Structure.Rebar rebar = doc.GetElement(rebarEid) as Autodesk.Revit.DB.Structure.Rebar;

                if (rebar == null)
                {
                    result["success"] = false; result["message"] = $"Rebar element '{command.RebarElementId}' not found.";
                    SetResult(result.ToString()); return;
                }

                JObject details = new JObject();
                details["element_id"] = rebar.Id.ToString();
                details["host_element_id"] = rebar.GetHostId()?.ToString() ?? "N/A";

                RebarBarType barType = doc.GetElement(rebar.GetTypeId()) as RebarBarType; // This gets the Rebar element's type, not BarType directly
                // To get BarType name, use rebar.LookupParameter("Type Name") or rebar.BarTypeName is not direct.
                // The actual bar type used for diameter, etc. is via rebar.GetBarTypeId()
                ElementId barTypeId = rebar.GetBarTypeId();
                RebarBarType actualBarType = doc.GetElement(barTypeId) as RebarBarType;
                details["bar_type_name"] = actualBarType?.Name ?? "N/A";


                RebarShape shape = doc.GetElement(rebar.GetShapeId()) as RebarShape;
                details["rebar_shape_name"] = shape?.Name ?? "N/A";

                details["layout_rule"] = rebar.LayoutRule.ToString();
                details["quantity"] = rebar.Quantity;

                Parameter spacingParam = rebar.LookupParameter("Spacing"); // Common name
                if (spacingParam != null && spacingParam.HasValue) details["spacing"] = spacingParam.AsDouble(); // Internal units (feet)
                else details["spacing"] = "N/A";

                details["total_length"] = rebar.TotalLength; // Internal units (feet)

                ElementId startHookId = rebar.GetHookTypeId(0);
                if (startHookId != ElementId.InvalidElementId) {
                    RebarHookType startHook = doc.GetElement(startHookId) as RebarHookType;
                    details["hook_at_start_name"] = startHook?.Name ?? "N/A";
                } else {
                    details["hook_at_start_name"] = null;
                }

                ElementId endHookId = rebar.GetHookTypeId(1);
                 if (endHookId != ElementId.InvalidElementId) {
                    RebarHookType endHook = doc.GetElement(endHookId) as RebarHookType;
                    details["hook_at_end_name"] = endHook?.Name ?? "N/A";
                } else {
                    details["hook_at_end_name"] = null;
                }

                // Get centerline curves (can be complex for multi-planar rebar)
                // For simplicity, we'll just indicate if they are available.
                // A full WKT or similar representation would be more involved.
                try
                {
                    // GetCenterlineCurves(bool adjustForSelfIntersection, bool suppressHooks, bool suppressBendRadius, MultiplanarOption multiplanarOption)
                    IList<Curve> centerlineCurves = rebar.GetCenterlineCurves(false, false, false, MultiplanarOption.IncludeAllMultiplanarCurves);
                    details["centerline_curves_count"] = centerlineCurves.Count;
                    JArray curvesWkt = new JArray();
                    foreach(Curve c in centerlineCurves) {
                        // Simplified WKT-like representation
                        string wkt = $"LINESTRING ({c.GetEndPoint(0).X} {c.GetEndPoint(0).Y} {c.GetEndPoint(0).Z}, {c.GetEndPoint(1).X} {c.GetEndPoint(1).Y} {c.GetEndPoint(1).Z})";
                        curvesWkt.Add(wkt);
                    }
                    details["centerline_curves_wkt_simplified"] = curvesWkt;

                }
                catch (Exception) { details["centerline_curves_info"] = "Error retrieving centerline curves."; }

                // Bend Data (if RebarShapeDrivenAccessor is applicable)
                RebarShapeDrivenAccessor shapeAccessor = rebar.GetShapeDrivenAccessor();
                if (shapeAccessor != null && shape.RebarShapeDefinition != null && shape.RebarShapeDefinition.Type == RebarShapeDefinitionType.BySegments)
                {
                    RebarShapeDefinitionBySegments defBySegments = shape.RebarShapeDefinition as RebarShapeDefinitionBySegments;
                    if (defBySegments != null)
                    {
                        JArray segmentsJson = new JArray();
                        for (int i = 0; i < defBySegments.NumberOfSegments; i++)
                        {
                            JObject segJson = new JObject();
                            // Getting actual segment lengths of an instance requires more calculation.
                            // This provides definition.
                            // RebarSegment segment = defBySegments.GetSegment(i); - This is definition
                            // For instance specific segment lengths, it's more complex.
                            // For now, we'll just list parameters that could be set.
                            // Parameter lengthParam = rebar.LookupParameter(shape.GetParamIdForSegmentLength(i));
                            // if(lengthParam != null) segJson["segment_length_param_" + i] = lengthParam.AsDouble();
                            // else  segJson["segment_length_param_" + i] = "N/A";
                            // segmentsJson.Add(segJson);
                        }
                        if (segmentsJson.Any()) details["shape_definition_segments_params"] = segmentsJson;
                    }
                }


                result["success"] = true;
                result["rebar_details"] = details;
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error getting rebar details: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
