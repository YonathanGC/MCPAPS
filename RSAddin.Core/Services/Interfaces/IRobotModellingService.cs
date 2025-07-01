using RSAddin.Core.Models;

namespace RSAddin.Core.Services.Interfaces
{
    public interface IRobotModellingService
    {
        bool CreateSimpleBeam(BeamInputParameters parameters);
    }
}
