# Timesteps

This is a simple example showcasing that the driver is always free to dictate what timestep is exposed to the workers.

## Instructions

To install, you can run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the code, run:

```bash
ips.py --config=trace.conf --platform=platform.conf
```

## Expected result

The "myscript" script will be executed twice.
