# Timesteps

This is a simple example showcasing that the driver is always free to dictate what timestep is exposed to the workers.

In this case, we are using the timesteps from the IPS config variable TIME_LOOP.

This is also an example of how subcomponents are able to accept any arbitrary keywords as parameters (only `timestamp` is a reserved keyword).

## Instructions

This example uses the script syntax, so to run it you only need to be in an environment where the ipsframework itself has been installed.

To run the code, run:

```bash
ips.py --config=trace.conf --platform=platform.conf
```
