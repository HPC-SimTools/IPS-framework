#!/usr/bin/env python3
"""
 -------------------------------------------------------------------------------
 Copyright 2006-2025 UT-Battelle, LLC. See LICENSE for more information.
 -------------------------------------------------------------------------------

    Ensemble utilities for IPS framework.
"""
import csv
import json


def params_from_csv(infile):
    """
    Read a CSV file and return a dictionary of parameters suitable for
    passing to services.run_ensemble()

    For each simulation, A, with corresponding parameters, name1, name2, ...,
    create columns following the pattern A:name1, A:name2, ... in the CSV file.
    Each row will correspond to the parameter values used in each instance.

    So, for example, if the CSV file looks like this:

    ```
    a_sim_comp:A, a_sim_comp:B, a_sim_comp:C, another_sim_comp:D, another_sim_comp:B, another_sim_comp:F
    3, 2.34, bar, 7, 0.775, xyzzy
    2, 5.82, baz, 5, 0.080, plud
    4, 0.1, quux, 9, 29.2, thud
    ```

    The returned structure will look like this:

    ```
    variables = {'a_sim_comp': {'A': [3, 2, 4],
                                    'B': [2.34, 5.82, 0.1],
                                    'C': ['bar', 'baz', 'quux']},
                 'another_sim_comp': {'D': [7, 5, 9],
                                      'B': [0.775, 0.080, 29.2],
                                      'F': ['xyzzy', 'plud', 'thud']}}
    ```

    Note that the corresponding config template file will need to specify
    sections for `a_sim_comp` and `another_sim_comp` that have placeholders
    for A, B, C, D, and F.  The template file will be used to create the
    config files for each instance, of which there will be three from this
    example.

    :param infile: Path to the CSV file
    :return: Dictionary of parameters suitable for use in run_ensemble()
    """
    variables = {}

    with open(infile, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        # Get the names of the simulations and their parameters
        for col in header:
            sim_name, param_name = col.split(':')
            sim_name = sim_name.strip() # because there may be extraneous spaces
            param_name = param_name.strip()

            if sim_name not in variables:
                variables[sim_name] = {}
            if param_name not in variables[sim_name]:
                variables[sim_name][param_name] = []

        # Read the values for each simulation and parameter
        for row in reader:
            if row == []: # there was an extra space or return at the EOF
                break
            for i, col in enumerate(header):
                sim_name, param_name = col.split(':')
                sim_name = sim_name.strip()  # because there may be extraneous spaces
                param_name = param_name.strip()
                variables[sim_name][param_name].append(row[i].strip())

    return variables


if __name__ == '__main__':
    # test harness where a CSV file is passed in on the command line and
    # returns the dictionary of parameters
    import sys

    variables = params_from_csv(sys.argv[1])

    print(json.dumps(variables, indent=4))