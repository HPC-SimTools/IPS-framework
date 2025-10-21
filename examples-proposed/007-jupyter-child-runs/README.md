# Jupyter Notebook with child runs

This is an example run where we use the Jupyter workflow in conjunction with parent/child runs.

Note that the child runs are not considered part of an ensemble in this instance.

## Instructions

To install, you can run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the code against the development instance, you will need to set the PORTAL_API_KEY environment variable and run:

```bash
PORTAL_API_KEY=**** ./run.sh
```

To run the code against a local IPS Portal instance, change `PORTAL_URL` in `parent.conf` to your local address.
