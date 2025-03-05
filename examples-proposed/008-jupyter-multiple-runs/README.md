# Jupyter Multiple Runs example (Post-run analysis example)

This is an example showcasing how to analyze multiple runs in the post analysis.

To run the example, you should copy or mount this directory to a JupyterHub or JupyterLab filesystem.

All files in this directory and subdirectories (except for `analysis_example.ipynb` and this README) will be automatically created via the IPS portal; this specific directory is meant to represent a specific IPS Portal location.

## analysis_example.ipynb

This is an example file that you would construct in anticipation of inspecting the data.

The JupyterNotebook environment will need to have `bokeh` installed for this example to work.

This example collects all y1, y2, y3... values across multiple runs, and for each property constructs multiple line plots across runs.

## portability

The provided API allows you to quickly save selected runs and the API into a tarball. You can extract this tarball on your own JupyterHub or JupyterLab instance and run the analysis exactly as you ran it on the original JupyterHub/JupyterLab server.
