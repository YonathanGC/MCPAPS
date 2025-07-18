# OpenSees 3D Analysis

This is a Python application that uses OpenSees to perform structural analysis of 3D frames.

## Project Structure

- `main.py`: The main script to run the analysis.
- `input/data.py`: Contains the input data for the structure.
- `materials/library.py`: Contains a library of common steel and concrete materials.
- `model/generate.py`: Generates the OpenSees model from the input data.
- `analysis/run.py`: Runs the structural analysis.
- `results/extract.py`: Extracts and prints the results.
- `visualization/plot.py`: Generates a 3D plot of the structure and diagrams.
- `requirements.txt`: The required Python packages.

## How to use

1.  **Install the dependencies:**
    ```
    pip install -r requirements.txt
    ```
2.  **Define the structure:**
    Modify the `input/data.py` file to define the nodes, materials, elements, loads, and supports of your structure. You can use the material library in `materials/library.py` to select common materials. The current example is an arch truss structure.
3.  **Run the analysis:**
    ```
    python3 main.py
    ```
4.  **View the results:**
    The results will be printed to the console. The following image files will be generated in the project directory:
    - `model.png`: A 3D plot of the structure, including the deformed shape and color-coded elements based on axial force.
    - `shear_diagram.png`: A shear force diagram for the upper chord of the first truss.
    - `moment_diagram.png`: A moment diagram for the upper chord of the first truss.

## Example

The current example is an arch truss structure defined parametrically in `input/data.py`. You can modify this file to analyze your own structures.
