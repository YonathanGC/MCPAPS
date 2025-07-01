namespace RSAddin.Core.Services.Interfaces
{
    public interface IRobotAnalysisService
    {
        bool RunAnalysis();
        // Podríamos añadir métodos para obtener resultados aquí o en un IResultsService
        string GetSimpleBeamMidPointDeflection(int beamNumber, int loadCaseNumber);
    }
}
