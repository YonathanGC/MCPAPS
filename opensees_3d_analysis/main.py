from analysis.run import run_static_analysis, run_modal_analysis
from results.extract import extract_nodal_results, extract_element_results, calculate_drifts
from input.data import get_arch_truss_data
from visualization.plot import plot_model

def main():
    """
    Main function to run the OpenSees analysis.
    """
    get_arch_truss_data()
    run_static_analysis()
    extract_nodal_results()
    extract_element_results()
    calculate_drifts()

    print("\nRunning modal analysis...")
    periods, frequencies = run_modal_analysis(num_modes=3)
    print("Periods (s):", periods)
    print("Frequencies (Hz):", frequencies)

    print("\nPlotting the model...")
    plot_model()


if __name__ == "__main__":
    main()
