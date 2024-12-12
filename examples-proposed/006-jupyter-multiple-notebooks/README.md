# Multiple Jupyter Notebooks workflow

This is an example which utilizes the time loop. The config file specifies that the script will execute all timestamps in the range of 1.0 to 100.0 (both inclusive), incrementing by 1.0 for each cycle.

For each timestep, the worker component will update the state file with random JSON data. Note that with this implementation, the state file is overridden on each new timestep (the final timestep called will persist after the application).

Additionally, the `Monitor` component in `component_monitor.py` showcases an example of integrating an IPS run with the IPS JupyterHub workflow. It requires a connection to the IPS web portal to be open to work, but the associated notebooks will show up on the portal. The JupyterHub workflow is designed to allow users to run custom visualizations during an IPS run; the framework can update the data in such a way that it will not interrupt the visualization process.

This example creates two notebooks: a simple one which prints out the data in a formatted manner (`sim/basic.ipynb`), and a notebook which generates a linear plot visualization (`sim/bokeh-plots.ipynb`).

## Instructions

Note that this example uses the module syntax, as opposed to the script syntax.

To install, you can run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the code, run:

```bash
./run.sh
```

By default, this example will always _append_ a state file. If you prefer to see an example of how to _replace_ a state file, run:

```bash
EXAMPLE_REPLACE=1 ./run.sh
```

There is also a script `run-delayed.sh` which you can use instead of `run.sh` if you would like to simulate a delay between monitor steps.

If executing `run.sh`, the script will output files into the directory defined by the `PSCRATCH` environment variable (or `/tmp` if this variable is not defined).
