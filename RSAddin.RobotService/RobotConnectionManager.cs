using RobotOM; // Asegúrate de tener la referencia a RobotOM.dll

namespace RSAddin.RobotService
{
    public class RobotConnectionManager
    {
        private static IRobotApplication? _robotApp;

        public static IRobotApplication? GetRobotApplication()
        {
            if (_robotApp == null || IsRobotClosed(_robotApp))
            {
                try
                {
                    // Intenta obtener una instancia existente de Robot
                    _robotApp = new RobotApplication();
                }
                catch (System.Runtime.InteropServices.COMException)
                {
                    // Robot no está abierto o no se pudo conectar
                    // En un Add-in real, esto podría manejarse mostrando un mensaje al usuario.
                    // Para este ejemplo, podríamos lanzar una excepción o devolver null.
                    System.Diagnostics.Debug.WriteLine("Robot Structural Analysis no está abierto o no se pudo conectar.");
                    return null;
                }
            }
            return _robotApp;
        }

        private static bool IsRobotClosed(IRobotApplication app)
        {
            try
            {
                // Intentar acceder a una propiedad simple para verificar si la conexión sigue viva
                _ = app.Project.CalcEngine.ToString(); // Cualquier acceso simple
                return false;
            }
            catch (System.Runtime.InteropServices.COMException)
            {
                return true; // La conexión COM está rota, Robot probablemente cerrado
            }
        }

        public static void ReleaseRobotApplication()
        {
            if (_robotApp != null)
            {
                // No se cierra Robot, solo se libera la instancia COM
                System.Runtime.InteropServices.Marshal.ReleaseComObject(_robotApp);
                _robotApp = null;
            }
        }
    }
}
