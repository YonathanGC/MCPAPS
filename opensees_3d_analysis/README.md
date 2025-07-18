# OpenSees 3D Analysis

This is a Python application that uses OpenSees to perform structural analysis of 3D frames and displays the results in a web interface.

## Project Structure

- `app.py`: The Flask web application.
- `main.py`: The main script to run the web application.
- `input/data.py`: Contains the input data for the structure.
- `materials/library.py`: Contains a library of common steel and concrete materials.
- `model/generate.py`: Generates the OpenSees model from the input data.
- `analysis/run.py`: Runs the structural analysis.
- `results/extract.py`: Extracts and prints the results.
- `visualization/plot.py`: Generates a 3D plot of the structure and diagrams.
- `templates/index.html`: The HTML template for the web interface.
- `requirements.txt`: The required Python packages.

## How to use

1.  **Install the dependencies:**
    ```
    pip install -r requirements.txt
    ```
2.  **Define the structure:**
    Modify the `input/data.py` file to define the nodes, materials, elements, loads, and supports of your structure. You can use the material library in `materials/library.py` to select common materials. The current example is an arch truss structure.
3.  **Run the web application:**
    ```
    python main.py
    ```
4.  **View the results:**
    Open your web browser and go to `http://127.0.0.1:5000/`. You will see an interactive 3D plot of the structure and tables with the nodal displacements and element forces.

## Example

The current example is an arch truss structure defined parametrically in `input/data.py`. You can modify this file to analyze your own structures.
