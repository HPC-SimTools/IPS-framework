# Hello world

This is the simplest possible example of utilizing the IPS framework. It contains a basic driver component and one supplemental worker component.

The framework will initially call `hello_driver.py` . For each step `hello_driver.py` takes, it will make a call into all worker classes (in this case `hello_worker.py`). In this application, only one task is spawned from the driver component.

## Instructions

To install, you can run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the code, run:

```bash
ips.py --config=helloworld.conf --platform=platform.conf
```

## Expected output

```
Created <class 'helloworld.hello_driver.hello_driver'>
Created <class 'helloworld.hello_worker.hello_worker'>
hello_driver: beginning step call
Hello from hello_worker
hello_driver: finished step call
```
