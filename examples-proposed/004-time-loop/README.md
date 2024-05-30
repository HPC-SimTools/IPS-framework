# Task pool synchronous

This is an example which utilizes the time loop. The config file specifies that the script will execute all timestamps in the range of 1.0 to 100.0 (both inclusive), incrementing by 1.0 for each cycle.

For each timestep, the worker component will update the state file with random JSON data. Note that with this implementation, the state file is overridden on each new timestep (the final timestep called will persist after the application).

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
ips.py --config=sim.conf --platform=platform.conf
```
