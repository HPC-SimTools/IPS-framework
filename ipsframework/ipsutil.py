# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import csv
import functools
import glob
import operator
import os
import shutil
import sys
import time
from typing import Iterable, Optional, Union

try:
    import Pyro4
except ImportError:
    pass


def which(program, alt_paths: Optional[list[str]] = None):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

        # Trust locations in platform file over those in environment path
        if alt_paths:
            for path in alt_paths:
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file


def copyFiles(src_dir: str, src_file_list: Union[str, Iterable[str]], target_dir: str, prefix='', keep_old: bool = False):
    """
    Copy files in *src_file_list* from *src_dir* to *target_dir* with an
    optional prefix.  If *keep_old* is ``True``, existing files in
    *target_dir* will not be overridden, otherwise files can be clobbered
    (default).
    Wild-cards in file name specification are allowed.
    """

    use_data_server = os.getenv('USE_DATA_SERVER', 'DATA_SERVER_NOT_USED')
    if use_data_server != 'DATA_SERVER_NOT_USED':
        data_server = Pyro4.Proxy('PYRONAME:DataServer')
        data_server.copyFiles(src_dir, src_file_list, target_dir, prefix, keep_old)
        return

    try:
        file_list = src_file_list.split()
    except AttributeError:  # srcFileList is not a string
        file_list = src_file_list

    globbed_file_list = []
    for src_file in file_list:
        if not target_dir == src_dir:
            src_file_full = os.path.join(src_dir, src_file)

            if os.path.isfile(src_file_full):
                globbed_file_list += [src_file_full]
            else:
                globbed_files = glob.glob(src_file_full)
                if len(globbed_files) > 0:
                    globbed_file_list += globbed_files
                else:
                    raise Exception('No such file : %s' % (src_file_full))

    # ------------------------------------------------------------------#
    #  for each file in globbed_file_list, copy it from src_dir to target_dir #
    # ------------------------------------------------------------------#
    for src_file in globbed_file_list:
        target = prefix + os.path.basename(src_file)
        target_file = os.path.join(target_dir, target)
        if os.path.isfile(target_file) and os.path.samefile(src_file, target_file):
            continue
        # Do not overwrite existing target files.
        if keep_old and os.path.isfile(target_file):
            for i in range(1000):
                new_name = target_file + '.' + str(i)
                if os.path.isfile(new_name):
                    continue
                target_file = new_name
                break

        (head, _) = os.path.split(os.path.abspath(target_file))
        try:
            os.makedirs(head, exist_ok=True)
        except OSError as oserr:
            print('Error creating directory %s : %s' % (head, oserr.strerror), file=sys.stderr)
            raise
        try:
            shutil.copy(src_file, target_file)
        except Exception:
            raise


def getTimeString(timeArg: Optional[time.struct_time] = None):
    """
    Return a string representation of *timeArg*. *timeArg* is expected
    to be an appropriate object to be processed by :py:meth:`time.strftime`.
    If *timeArg* is ``None``, current time is used.
    """
    if timeArg is None:
        arg = time.localtime()
    else:
        arg = timeArg
    return time.strftime('%Y-%m-%d|%H:%M:%S%Z', arg)


def params_from_csv(infile: Union[str, os.PathLike]) -> dict[str, dict[str, list[str]]]:
    """
    Read a CSV file and return a dictionary of parameters suitable for
    passing to services.run_ensemble()

    For each simulation, A, with corresponding parameters, name1, name2, ...,
    create columns following the pattern A:name1, A:name2, ... in the CSV file.
    Each row will correspond to the parameter values used in each instance.

    So, for example, if the CSV file looks like this:

        a_comp:A, a_comp:B, a_comp:C, another_comp:D, another_comp:B, another_comp:F
        3, 2.34, bar, 7, 0.775, xyzzy
        2, 5.82, baz, 5, 0.080, plud
        4, 0.1, quux, 9, 29.2, thud

    The returned structure will look like this:

        variables = {'a_comp': {'A': [3, 2, 4],
                                'B': [2.34, 5.82, 0.1],
                                'C': ['bar', 'baz', 'quux']},
                     'another_comp': {'D': [7, 5, 9],
                                      'B': [0.775, 0.080, 29.2],
                                      'F': ['xyzzy', 'plud', 'thud']}}

    Note that the corresponding config template file will need to specify
    sections for `a_comp` and `another_comp` that have placeholders
    for A, B, C, D, and F.  The template file will be used to create the
    config files for each instance, of which there will be three from this
    example.

    :param infile: Path to the CSV file
    :returns: Dictionary of parameters suitable for use in run_ensemble()
    """
    variables: dict[str, dict[str, list[str]]] = {}

    with open(infile, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        # Get the names of the components and their parameters
        for col in header:
            comp_name, param_name = col.split(':')
            comp_name = comp_name.strip()  # because there may be extraneous spaces
            param_name = param_name.strip()

            if comp_name not in variables:
                variables[comp_name] = {}
            if param_name not in variables[comp_name]:
                variables[comp_name][param_name] = []

        # Read the values for each simulation and parameter
        for row in reader:
            if row == []:  # there was an extra space or return at the EOF
                break
            for i, col in enumerate(header):
                comp_name, param_name = col.split(':')
                comp_name = comp_name.strip()  # because there may be extraneous spaces
                param_name = param_name.strip()
                variables[comp_name][param_name].append(row[i].strip())

    return variables


def group_ensemble_variables_into_instances(variables: dict[str, dict[str, list[str]]], name: str):
    """convert component variables into something like this:

    [['prefix_0', [['a_sim_comp', {'A': 3, 'B': 2.34, 'C': 'bar'}],
                        ['another_sim_comp', {'D': 7, 'B': 0.775, 'F': 'xyzzy'}]]],
        ['prefix_1', [['a_sim_comp', {'A': 2, 'B': 5.82, 'C': 'baz'}],
                        ['another_sim_comp', {'D': 5, 'B': 0.08, 'F': 'plud'}]]],
        ['prefix_2', [['a_sim_comp', {'A': 4, 'B': 0.1, 'C': 'quux'}],
                        ['another_sim_comp', {'D': 9, 'B': 29.2, 'F': 'thud'}]]]]

        prefix_n corresponds to a specific ensemble instance and will
        be used for a unique subdir name.  That, in turn, references a
        list of lists where each list element is a component that, in
        turn, has a dict mapping component variables to values that will
        then be later used to flesh out a config file from a config
        template file.
    """
    # Transpose the data for each simulation component; essentially
    # convert the list of variable values into corresponding dicts
    # mapping the variables to specific values.  Sorta like a
    # column-wise to row-wise transposition.
    transposed = {key: [dict(zip(inner.keys(), values)) for values in zip(*inner.values())] for key, inner in variables.items()}

    # Build the final structure where each instance is named
    # {prefix}_n
    result = [
        (f'{name}{i}', [(sim_name, sim_data) for sim_name, sim_data_list in transposed.items() for sim_data in [sim_data_list[i]]])
        for i in range(len(next(iter(transposed.values()))))
    ]

    return result


def ensemble_instances_to_csv(instances: list[tuple[str, list[tuple[str, dict[str, object]]]]], path: Union[str, os.PathLike]) -> None:
    """
    Take in a structure of variables suitable for passing to services.run_ensemble(), and write a CSV file from it.

    So, for example, if the structure looks like this:

        variables = {'a_comp': {'A': [3, 2, 4],
                                'B': [2.34, 5.82, 0.1],
                                'C': ['bar', 'baz', 'quux']},
                     'another_comp': {'D': [7, 5, 9],
                                      'B': [0.775, 0.080, 29.2],
                                      'F': ['xyzzy', 'plud', 'thud']}}

    The written CSV file will look like this:
        a_comp:A,a_comp:B,a_comp:C,another_comp:D,another_comp:B,another_comp:F
        3,2.34,bar,7,0.775,xyzzy
        2,5.82,baz,5,0.080,plud
        4,0.1,quux,9,29.2,thud

    The generated CSV file follows RFC-4180 precisely.

    :param variables: dictionary of parameters identical to the return value of params_from_csv
    :param path: Path to the CSV file
    """
    with open(path, 'w') as fd:
        writer = csv.writer(fd)
        # header row
        writer.writerow(
            functools.reduce(
                operator.iconcat, [[f'{instance[0]}:{component}' for component in list(instance[1].keys())] for instance in instances[0][1]], ['sim_name']
            )
        )
        # data rows
        writer.writerows(
            [functools.reduce(operator.iconcat, [list(component[1].values()) for component in instance[1]], [instance[0]]) for instance in instances]
        )


if __name__ == '__main__':
    # test harness where a CSV file is passed in on the command line and
    # returns the dictionary of parameters
    import json
    import sys

    variables = params_from_csv(sys.argv[1])

    print(json.dumps(variables, indent=4))
