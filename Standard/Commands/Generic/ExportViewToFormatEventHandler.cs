// Standard/Commands/Generic/ExportViewToFormatEventHandler.cs
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Handlers;
using System;
using System.Collections.Generic; // For ICollection, IList
using System.IO; // For Path
using System.Linq;

namespace Standard.Commands.Generic
{
    public class ExportViewToFormatEventHandler : WaitableExternalEventHandlerBase<ExportViewToFormatCommand>
    {
        public override string GetName() => "ExportViewToFormatEventHandler";

        protected override void Execute(UIApplication app, ExportViewToFormatCommand command)
        {
            UIDocument uidoc = app.ActiveUIDocument;
            Document doc = uidoc.Document;
            JObject result = new JObject();

            try
            {
                if (string.IsNullOrEmpty(command.ViewId) || string.IsNullOrEmpty(command.OutputFilePath) || string.IsNullOrEmpty(command.ExportFormat))
                {
                    result["success"] = false; result["message"] = "ViewId, OutputFilePath, and ExportFormat are required.";
                    SetResult(result.ToString()); return;
                }

                ElementId viewEid;
                try { viewEid = new ElementId(long.Parse(command.ViewId)); }
                catch { result["success"] = false; result["message"] = $"Invalid ViewId: {command.ViewId}"; SetResult(result.ToString()); return; }

                ViewExport viewToExport = doc.GetElement(viewEid) as ViewExport; // Use ViewExport if targeting view for export, or ViewSheet for sheets
                if (viewToExport == null) {
                    // Try if it's a ViewSheet
                    ViewSheet sheetToExport = doc.GetElement(viewEid) as ViewSheet;
                    if (sheetToExport == null) {
                        result["success"] = false; result["message"] = $"View or Sheet with ID '{command.ViewId}' not found or not exportable.";
                        SetResult(result.ToString()); return;
                    }
                    // If it's a sheet, the export command might need to handle it slightly differently or ensure it's a printable sheet for PDF.
                    // For now, we'll assume `doc.Export` handles View and ViewSheet appropriately based on options.
                }


                string outputFolder = Path.GetDirectoryName(command.OutputFilePath);
                string outputFileName = Path.GetFileName(command.OutputFilePath);

                if (!Directory.Exists(outputFolder))
                {
                    try { Directory.CreateDirectory(outputFolder); }
                    catch (Exception dirEx) {
                        result["success"] = false; result["message"] = $"Failed to create output directory '{outputFolder}': {dirEx.Message}";
                        SetResult(result.ToString()); return;
                    }
                }

                // Use a ViewSet for export, containing just the single view/sheet
                ViewSet viewSet = new ViewSet();
                viewSet.Insert(doc.GetElement(viewEid) as View); // Needs to be a View, ViewSheet inherits from View.

                bool exportSuccessful = false;

                // Transaction is often not needed for export operations, but some specific options might require it.
                // For safety or if any pre-export modifications were needed, a transaction could wrap parts.
                // using (Transaction tx = new Transaction(doc, "MCP Export View")) { tx.Start(); ... tx.Commit(); }

                switch (command.ExportFormat.ToUpperInvariant())
                {
                    case "DWG":
                    case "DXF":
                        DWGExportOptions dwgOptions = new DWGExportOptions();
                        if (command.Options.DwgVersion != null) { /* TODO: Map string to ACADVersion enum */ }
                        // dwgOptions.FileVersion = ACADVersion.R2013; // Example
                        // Set other DWG options from command.Options
                        exportSuccessful = doc.Export(outputFolder, outputFileName, viewSet, dwgOptions);
                        break;

                    case "PDF":
                        PDFExportOptions pdfOptions = new PDFExportOptions();
                        // pdfOptions.FileName = outputFileName; // Often set by the Export method itself based on input name
                        if (command.Options.PaperSize != null) { /* TODO: Map to PaperSize enum or specific PaperFormat */ }
                        if (command.Options.Orientation != null) { /* TODO: Map to PageOrientationType */ }
                        pdfOptions.ZoomToFit = command.Options.ZoomToFit ?? true;
                        pdfOptions.HideScopeBoxes = command.Options.HideScopeBoxes ?? false;
                        pdfOptions.HideUnreferencedViewTags = command.Options.HideUnreferencedViewTags ?? false;
                         if (command.Options.PaperPlacement != null && Enum.TryParse<PaperPlacementType>(command.Options.PaperPlacement, true, out PaperPlacementType ppt)) {
                            pdfOptions.PaperPlacement = ppt;
                        }
                        if (command.Options.RasterQuality != null && Enum.TryParse<RasterQualityType>(command.Options.RasterQuality, true, out RasterQualityType rqt)) {
                            pdfOptions.RasterQuality = rqt;
                        }
                        // For PDF, often you export a list of ViewSheet Ids.
                        // If viewEid is a ViewPlan, it might need to be on a sheet first for reliable PDF export.
                        // If viewEid is a ViewSheet, it should work.
                        IList<ElementId> viewsToExportPdf = new List<ElementId> { viewEid };
                        doc.Export(outputFolder, viewsToExportPdf, pdfOptions); // Different overload for PDF
                        exportSuccessful = File.Exists(Path.Combine(outputFolder, pdfOptions.GetRealFileName(doc, viewEid))); // Verify file creation
                        break;

                    case "PNG":
                    case "JPG":
                        ImageExportOptions imgOptions = new ImageExportOptions();
                        imgOptions.FilePath = command.OutputFilePath; // ImageExportOptions takes full path
                        imgOptions.ExportRange = ExportRange.CurrentView; // Or SetOfViews if viewSet is used.

                        if (command.Options.PixelWidth.HasValue) imgOptions.ImageWidth = command.Options.PixelWidth.Value;
                        if (command.Options.PixelHeight.HasValue) imgOptions.ImageHeight = command.Options.PixelHeight.Value;

                        if(command.Options.FitDirection != null && Enum.TryParse<FitDirectionType>(command.Options.FitDirection, true, out FitDirectionType fdt)) {
                            imgOptions.FitDirection = fdt;
                            if (command.Options.PixelSize.HasValue) imgOptions.PixelSize = command.Options.PixelSize.Value;
                        }

                        if (command.Options.ImageResolutionDPI.HasValue) imgOptions.ImageResolution = (ImageResolution)command.Options.ImageResolutionDPI.Value; // Direct cast if values match enum

                        if(command.Options.ShadingMode != null && Enum.TryParse<RasterVisualStyle>(command.Options.ShadingMode, true, out RasterVisualStyle rvs)) {
                           // imgOptions.VisualStyle = rvs; // VisualStyle is on ViewDisplayStyles, not directly on ImageExportOptions in older APIs
                           // This might need setting on the view temporarily or using different options.
                           // For newer APIs, check if ImageExportOptions has a VisualStyle property.
                        }
                        imgOptions.HLRandWFViewsFileType = command.ExportFormat.ToUpperInvariant() == "PNG" ? ImageFileType.PNG : ImageFileType.JPEGLossless; // Or JPEGMedium etc.

                        // doc.ExportImage(imgOptions); // This is one way.
                        // Or if using the general export method:
                        // doc.Export(outputFolder, outputFileName, viewSet, imgOptions); -> This might not be the correct overload for images.
                        // Exporting images usually involves `doc.ExportImage(options)` after setting options.FilePath and options.ViewId (or current view)
                        // For now, we will assume `doc.ExportImage` is the way.
                        // The view to export must be the active view or specified in options.
                        // This command structure might need adjustment for ExportImage.
                        // Let's assume the viewSet approach for consistency if possible, otherwise, this needs a specific path.
                        // For `doc.ExportImage`, the ViewSet is not used. It exports the current view or a specific view if set in options.
                        // This part is tricky. For simplicity, let's assume it exports the view in the viewset.
                        // This will likely fail for ExportImage. A separate handler path might be needed.
                        // A common pattern is to make the view active then export.
                        // For now, this will be a conceptual placeholder.
                        // A more robust solution for images:
                        uidoc.ActiveView = doc.GetElement(viewEid) as View; // Make view active (dangerous if not handled well)
                        doc.ExportImage(imgOptions);
                        exportSuccessful = File.Exists(command.OutputFilePath);

                        break;

                    case "IFC":
                        IFCExportOptions ifcOptions = new IFCExportOptions();
                        if (command.Options.IfcVersionString != null) { /* TODO: Map to IFCVersion enum */ }
                        // ifcOptions.FileVersion = IFCVersion.IFC2x3; // Example
                        // Set other IFC options
                        exportSuccessful = doc.Export(outputFolder, outputFileName, viewSet, ifcOptions);
                        break;

                    case "NWC": // Navisworks Cache
                        NavisworksExportOptions nwcOptions = new NavisworksExportOptions();
                        nwcOptions.ExportScope = NavisworksExportScope.View; // Or .Model, .Selection
                        if (command.Options.ExportScope != null && Enum.TryParse<NavisworksExportScope>(command.Options.ExportScope, true, out NavisworksExportScope nes)) {
                            nwcOptions.ExportScope = nes;
                        }
                        nwcOptions.ExportElementProperties = command.Options.ConvertElementProperties ?? true;
                        nwcOptions.ExportLinks = command.Options.ExportLinks ?? false;
                        nwcOptions.ViewId = viewEid; // Set the view to export

                        // NWC export doesn't use the standard doc.Export overload. It's usually a method on Document.
                        // doc.Export(string folder, string name, NavisworksExportOptions options);
                        doc.Export(outputFolder, outputFileName, nwcOptions); // This is the correct overload for NWC
                        exportSuccessful = File.Exists(Path.Combine(outputFolder, outputFileName));
                        break;

                    default:
                        result["success"] = false; result["message"] = $"ExportFormat '{command.ExportFormat}' is not supported.";
                        SetResult(result.ToString()); return;
                }

                if (exportSuccessful)
                {
                    result["success"] = true;
                    result["message"] = $"View '{doc.GetElement(viewEid).Name}' exported successfully to '{command.OutputFilePath}'.";
                    result["exported_file_path"] = Path.Combine(outputFolder, outputFileName); // Ensure this is the actual path
                }
                else
                {
                    // If exportSuccessful wasn't set by a specific path (like PDF/NWC which have their own export calls)
                    // or if doc.Export returned false.
                    if (! (bool)(result["success"] ?? false) ) // Check if success wasn't already set to false by a specific error
                    {
                        result["success"] = false;
                        result["message"] = $"Export failed for format '{command.ExportFormat}'. Check Revit logs or view compatibility.";
                    }
                }
            }
            catch (Exception ex)
            {
                result["success"] = false;
                result["message"] = $"Error exporting view: {ex.ToString()}";
            }
            finally
            {
                SetResult(result.ToString());
            }
        }
    }
}
