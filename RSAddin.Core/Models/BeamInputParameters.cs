namespace RSAddin.Core.Models
{
    public class Point3D
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
    }

    public class BeamInputParameters
    {
        public Point3D StartNode { get; set; } = new Point3D { X = 0, Y = 0, Z = 0 };
        public Point3D EndNode { get; set; } = new Point3D { X = 5, Y = 0, Z = 0 }; // Viga de 5m por defecto
        public string SectionName { get; set; } = "IPE 200"; // Sección por defecto

        // Apoyos (simplificado: true = fijo en XYZ, false = libre)
        public bool SupportStartNodeFixed { get; set; } = true;
        public bool SupportEndNodeFixed { get; set; } = false; // Un apoyo fijo y uno simple por defecto

        // Carga (simplificado: una carga puntual uniforme en el centro)
        public double PointLoadValue { get; set; } = -10000; // N (hacia abajo)
        public LoadCaseType LoadCaseForPointLoad { get; set; } = LoadCaseType.Dead; // Caso de carga por defecto
    }

    public enum LoadCaseType
    {
        Dead,
        Live
        // Añadir más según sea necesario
    }
}
