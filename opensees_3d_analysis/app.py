from flask import Flask, render_template
from analysis.run import run_static_analysis
from visualization.plot import plot_model
from results.extract import extract_nodal_results, extract_element_results
import json

app = Flask(__name__)

@app.route('/')
def index():
    run_static_analysis()
    plot_json = plot_model(show_deformed=True, scale_factor=100)
    nodal_results = extract_nodal_results()
    element_results = extract_element_results()
    return render_template('index.html', plot_json=plot_json, nodal_results=nodal_results, element_results=element_results)

if __name__ == '__main__':
    app.run(debug=True)
