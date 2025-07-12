// Standard/Commands/Generic/ExportViewToFormatCommand.cs
using Newtonsoft.Json.Linq;
using RevitMCP.SDK.Core.Commands;
using System.Collections.Generic; // For ICollection in options

namespace Standard.Commands.Generic
{
    // Define specific options classes if they become complex, or use JObject for flexibility
    public class ExportOptionsContainer
    {
        // DWG/DXF specific
        public string DwgVersion { get; set; } // e.g., "ACAD2013"
        public string ExportLayers { get; set; } // e.g., "ByLayer"

        // PDF specific
        public string PaperSize { get; set; } // e.g., "Letter", "A4"
        public string Orientation { get; set; } // e.g., "Landscape"
        public bool? ZoomToFit { get; set; }
        public bool? HideScopeBoxes { get; set; }
        public bool? HideUnreferencedViewTags { get; set; }
        public string PaperPlacement { get; set; } // "Center", "LowerLeft"
        public string RasterQuality { get; set; } // "Low", "Medium", "High", "Presentation"


        // Image specific (PNG/JPG)
        public int? ImageResolutionDPI { get; set; }
        public int? PixelWidth { get; set; } // Either use PixelWidth/Height or FitDirection/PixelSize
        public int? PixelHeight { get; set; }
        public string FitDirection { get; set; } // "Horizontal", "Vertical"
        public int? PixelSize { get; set; } // Used with FitDirection
        public string ShadingMode { get; set; } // "HiddenLine", "Shaded", "Realistic"
        public bool? ExportህንጻViewsAsLinks { get; set; } // For image export, typically false for direct image.

        // IFC specific
        public string IfcVersionString { get; set; } // e.g., "IFC2x3", "IFC4"
        // Many more IFC options exist

        // NWC specific
        public bool? ConvertElementProperties { get; set; }
        public bool? ExportLinks { get; set; }
        public string ExportScope { get; set; } // "CurrentView", "EntireProject", "SelectedElements"
    }


    public class ExportViewToFormatCommand : ExternalEventCommandBase
    {
        public string ViewId { get; private set; }
        public string OutputFilePath { get; private set; }
        public string ExportFormat { get; private set; } // "DWG", "PDF", "PNG", "IFC", "NWC" etc.
        public ExportOptionsContainer Options { get; private set; }

        public ExportViewToFormatCommand(JObject commandParameters) : base(commandParameters)
        {
            ViewId = commandParameters.Value<string>("view_id");
            OutputFilePath = commandParameters.Value<string>("output_file_path");
            ExportFormat = commandParameters.Value<string>("export_format");
            Options = commandParameters["options"]?.ToObject<ExportOptionsContainer>() ?? new ExportOptionsContainer();
        }
    }
}
