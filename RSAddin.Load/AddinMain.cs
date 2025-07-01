using RobotOM;
using RSAddin.UI.Views;
using System;
using System.Runtime.InteropServices;
using System.Windows;
using RSAddin.RobotService; // Para RobotConnectionManager

namespace RSAddin.Load
{
    // ¡¡GENERAR UN NUEVO GUID para producción!! Ejemplo:
    [Guid("A1B2C3D4-E5F6-7890-1234-567890ABCDEF")]
    [ComVisible(true)]
    public class AddinMain : IRobotAddIn
    {
        private BeamCreatorView? _beamCreatorView;
        private static Application? _wpfApp; // Para mantener la aplicación WPF viva

        public int Connect(IRobotApplication robotApplication, int addInId, bool firstTime)
        {
            // Guardar la instancia de robotApplication si es necesario globalmente
            // RobotConnectionManager ya la gestiona, así que no es estrictamente necesario aquí.
            // System.Diagnostics.Debug.WriteLine($"Add-in Connected: ID {addInId}, FirstTime: {firstTime}");

            ShowBeamCreatorWindow();
            return 1;
        }

        public int Disconnect(int addInId, bool lastTime)
        {
            // System.Diagnostics.Debug.WriteLine($"Add-in Disconnecting: ID {addInId}, LastTime: {lastTime}");
            // Limpiar recursos, cerrar ventanas, etc.
            if (_wpfApp != null)
            {
                 _wpfApp.Dispatcher.Invoke(() =>
                 {
                    if (_beamCreatorView != null)
                    {
                        _beamCreatorView.Close();
                        _beamCreatorView = null;
                    }
                    // Considerar cerrar la App WPF si este Add-in es el único que la usa
                    // if (lastTime) { _wpfApp.Shutdown(); _wpfApp = null; }
                 });
            }
            RobotConnectionManager.ReleaseRobotApplication();
            return 1;
        }

        public void ShowBeamCreatorWindow()
        {
            // Necesario para ejecutar una aplicación WPF desde un host no WPF como Robot
            if (_wpfApp == null)
            {
                _wpfApp = new Application();
                // No llamar a _wpfApp.Run(), ya que bloquearía.
                // El ShutdownMode se puede configurar si es necesario, pero OnExplicitShutdown
                // o OnLastWindowClose son comunes. Si Robot maneja el ciclo de vida,
                // podríamos no necesitar cerrarla explícitamente aquí.
                _wpfApp.ShutdownMode = ShutdownMode.OnExplicitShutdown;
            }

            _wpfApp.Dispatcher.Invoke(() =>
            {
                if (_beamCreatorView == null || !_beamCreatorView.IsLoaded) // IsLoaded es mejor que IsVisible para saber si está realmente cerrada
                {
                    _beamCreatorView = new BeamCreatorView();
                    _beamCreatorView.Closed += (s, e) =>
                    {
                        _beamCreatorView = null;
                        // System.Diagnostics.Debug.WriteLine("BeamCreatorView closed.");
                        // Si esta es la última ventana y el add-in se está desconectando,
                        // se podría considerar cerrar la app WPF.
                    };
                    // System.Diagnostics.Debug.WriteLine("Showing BeamCreatorView...");
                    _beamCreatorView.Show();
                }
                else
                {
                    // System.Diagnostics.Debug.WriteLine("Activating existing BeamCreatorView...");
                    _beamCreatorView.Activate();
                }
            });
        }
    }
}
