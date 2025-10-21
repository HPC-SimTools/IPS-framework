# Examples

This directory is meant to showcase concrete code examples on how to use the IPS framework.

Each example folder contains specific instructions on how to run it. Each example is standalone and can be copy/pasted into its own file.

Note that each example will explicitly need to be installed into its own virtual environment - this is because the IPS framework needs all of your Components to be contained in a valid Python package.

## Summary of examples

- `001-helloworld` - an example which demonstrates the bare minimum example of running an IPS simulation. Demonstrates a worker component in addition to a driver component.
- `002-same-timestep` - this is an example which demonstrates manual usage of the IPS timesteps from the driver.
- `003-different-timestep` - this example showcases a definition of the time loop in the config file
- `004-jupyter-append` - this is a straightforward example of utilizing the IPS Portal to save output files by timestep and Jupyter notebooks. 
- `005-jupyter-replace` - same as the `004-jupyter-append` example, but assumes that you'll be overwriting data instead of appending data.
- `006-jupyter-multiple-notebooks` - example which shows how you can save multiple notebooks
- `007-jupyter-child-runs` - example which shows how to run child simulations from parent simulations (note: this example does NOT showcase how to run ensembles)
- `008-jupyter-multiple-runs` - This is not an IPS framework example itself, but an example of how the results of a parent/child run would be stored on a Jupyter instance, and how you can analyze this data.
- `009-task-pool-sync` - showcases a simple example utilizing `dask` to simulate parallelism
- `010-adios-example` - meant to be a hello-world example for utilizing ADIOS files with the IPS Portal API.
- `020-simple-ensemble` - simple example of how to run an ensemble of simulations
- `020-simple-ensemble-with-portal` - same as the `020-simple-ensemble` example, but with IPS Portal integration.