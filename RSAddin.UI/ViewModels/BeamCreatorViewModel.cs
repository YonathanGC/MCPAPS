using RSAddin.Core.Models;
using RSAddin.Core.Services.Interfaces;
using RSAddin.RobotService; // Para RobotConnectionManager
using RSAddin.RobotService.Implementations;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq; // Para .Cast<T>()
using System.Runtime.CompilerServices;
using System.Windows.Input;
using RobotOM; // Para IRobotApplication e IRobotCase


// Implementación simple de INotifyPropertyChanged y ICommand si no se usa un toolkit MVVM
public class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    protected bool SetProperty<T>(ref T field, T newValue, [CallerMemberName] string? propertyName = null)
    {
        if (!EqualityComparer<T>.Default.Equals(field, newValue))
        {
            field = newValue;
            OnPropertyChanged(propertyName);
            return true;
        }
        return false;
    }
}

public class RelayCommand : ICommand
{
    private readonly Action _execute;
    private readonly Func<bool>? _canExecute;

    public event EventHandler? CanExecuteChanged
    {
        add { CommandManager.RequerySuggested += value; }
        remove { CommandManager.RequerySuggested -= value; }
    }

    public RelayCommand(Action execute, Func<bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public bool CanExecute(object? parameter) => _canExecute == null || _canExecute();
    public void Execute(object? parameter) => _execute();
}


namespace RSAddin.UI.ViewModels
{
    public class BeamCreatorViewModel : ObservableObject
    {
        private BeamInputParameters _beamParams = new BeamInputParameters();
        public BeamInputParameters BeamParams
        {
            get => _beamParams;
            set => SetProperty(ref _beamParams, value);
        }

        private string _statusMessage = "Listo.";
        public string StatusMessage
        {
            get => _statusMessage;
            set => SetProperty(ref _statusMessage, value);
        }

        public ObservableCollection<LoadCaseType> AvailableLoadCaseTypes { get; }

        private readonly IRobotModellingService _modellingService;
        private readonly IRobotAnalysisService _analysisService;

        public ICommand CreateModelCommand { get; }
        public ICommand RunAnalysisCommand { get; }
        public ICommand GetDeflectionCommand { get; }

        public BeamCreatorViewModel()
        {
            _modellingService = new RobotModellingService();
            _analysisService = new RobotAnalysisService();

            CreateModelCommand = new RelayCommand(CreateModel);
            RunAnalysisCommand = new RelayCommand(ExecuteAnalysis);
            GetDeflectionCommand = new RelayCommand(GetDeflection);

            AvailableLoadCaseTypes = new ObservableCollection<LoadCaseType>(Enum.GetValues(typeof(LoadCaseType)).Cast<LoadCaseType>());
        }

        private void CreateModel()
        {
            StatusMessage = "Creando modelo...";
            bool success = _modellingService.CreateSimpleBeam(BeamParams);
            StatusMessage = success ? "Modelo creado exitosamente en Robot." : "Error al crear el modelo. Verifique la salida de depuración o los logs de Robot.";
        }

        private void ExecuteAnalysis()
        {
            StatusMessage = "Ejecutando análisis...";
            bool success = _analysisService.RunAnalysis();
            StatusMessage = success ? "Análisis completado." : "Error durante el análisis. Verifique la salida de depuración o los logs de Robot.";
        }

        private void GetDeflection()
        {
            StatusMessage = "Obteniendo deflexión...";
            int barNumber = 1;
            int loadCaseNumber = 1;

            IRobotApplication? robot = RobotConnectionManager.GetRobotApplication();
            if (robot != null)
            {
                try
                {
                    // Intentar obtener el número de caso real basado en el nombre del Enum
                    string caseName = BeamParams.LoadCaseForPointLoad.ToString();
                    IRobotCase? rCase = robot.Project.Structure.Cases.Get(caseName) as IRobotCase;
                    if (rCase != null)
                    {
                        loadCaseNumber = rCase.Number;
                    }
                    else
                    {
                        StatusMessage = $"Advertencia: Caso '{caseName}' no encontrado en Robot. Usando caso por defecto {loadCaseNumber}.";
                        // Continuar con el loadCaseNumber por defecto si no se encuentra
                    }
                }
                catch(Exception ex)
                {
                     StatusMessage = $"Error obteniendo número de caso: {ex.Message}. Usando caso por defecto {loadCaseNumber}.";
                }
            }
            else
            {
                StatusMessage = "Error: No se pudo conectar a Robot para obtener el número de caso.";
                return;
            }

            string result = _analysisService.GetSimpleBeamMidPointDeflection(barNumber, loadCaseNumber);
            StatusMessage = result;
        }
    }
}
