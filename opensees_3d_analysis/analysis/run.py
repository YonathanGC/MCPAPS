import openseespy.opensees as ops
import numpy as np

def run_static_analysis():
    """
    Runs the OpenSees static analysis.
    """
    ops.wipe()
    from model.generate import generate_model
    generate_model()

    # Create the analysis
    ops.system("BandGeneral")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")

    # Run the analysis
    ops.analyze(1)

    print("Static analysis complete.")

def run_modal_analysis(num_modes):
    """
    Runs the OpenSees modal analysis.
    """
    # Run a static analysis first to build the model
    run_static_analysis()

    # Get the eigenvalues
    eigenvalues = ops.eigen(num_modes)

    # Calculate periods and frequencies
    periods = [2 * np.pi / np.sqrt(lam) for lam in eigenvalues]
    frequencies = [1 / p for p in periods]

    print("Modal analysis complete.")
    return periods, frequencies
