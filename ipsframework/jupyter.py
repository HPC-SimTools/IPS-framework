"""
This module is designed to help generate JupyterNotebooks to be used with IPS Portal analysis.
Some parts of the script will need direction from users on the Framework side to generate.

Note that this module is currently biased towards working with NERSC (jupyter.nersc.gov), so will attempt to import specific libraries.

To see available libraries on NERSC, run:
  !pip list

...in a shell on Jupyter NERSC.
"""

from os.path import sep
from pathlib import Path
from typing import Optional

import nbformat as nbf

HOOK = '### This cell autogenerated by IPS Framework. DO NOT EDIT UNTIL IPS RUN IS FINALIZED. ###'
"""This hook is used to determine which "cell" the IPS framework should work with.

It is written to a notebook cell on initializing it, and is searched for when adding a data file to it.
"""

DIRECTORY_VARIABLE_NAME = 'DATA_DIR'


def replace_last(source_string: str, old: str, new: str) -> str:
    """Attempt to replace the last occurence of 'old' with 'new' in 'source_string', searching from the right.

    This should only be called if 'old' can effectively be guaranteed to exist in the string.
    """
    head, _sep, tail = source_string.rpartition(old)
    return f'{head}{new}{tail}'


def _initial_jupyter_file_notebook_cell(dest: str, files_variable_name: str) -> str:
    return f"""{HOOK}

import os

# NOTE: directory should be sim_name plus the run id from the Portal
{DIRECTORY_VARIABLE_NAME} = '{str(Path(dest).parent / 'data') + sep}'
# Uncomment below line to implicitly use any state files saved in the data directory, note that the IPS framework explicitly lists out each file used
#{files_variable_name} = os.listdir('data')
# files created during the run
{files_variable_name} = [
]
"""


def initialize_jupyter_notebook(dest: str, src: str, variable_name: str, index: int):
    """Create a new notebook from an old notebook, copying the result from 'src' to 'dest'.

    Params:
      - dest - location of notebook to create on filesystem (absolute file path)
      - src - location of source notebook on filesystem (is not overwritten unless src == dest)
      - variable_name: what to call the variable
      - index: insert new cells at position before this value (will not remove preexisting cells)
      - initial_data_files: optional list of files to initialize the notebook with

    """
    # to avoid conversion, use as_version=nbf.NO_CONVERT
    nb: nbf.NotebookNode = nbf.read(src, as_version=4)

    nb['cells'] = (
        # warning notification for users inspecting the file, unused programatically
        [nbf.v4.new_markdown_cell('# WARNING: Do not manually modify this file until the IPS simulation is complete.')]
        + nb['cells'][:index]
        + [
            # explicitly mark the IPS cell for users inspecting the file, unused programatically
            nbf.v4.new_markdown_cell('## Next cell generated by IPS Framework'),
            nbf.v4.new_code_cell(_initial_jupyter_file_notebook_cell(dest, variable_name)),
        ]
        + nb['cells'][index:]
    )

    nbf.validate(nb)
    with open(dest, 'w') as f:
        nbf.write(nb, f)


def add_data_file_to_notebook(dest: str, data_file: str, index: Optional[int] = None):
    """Add data file to notebook list.

    Params:
      - dest: path to notebook which will be modified
      - data_file: data file we add to the notebook
      - index: optional index of the IPS notebook cell. If not provided, search through the notebook via an expected string hook.
    """
    nb: nbf.NotebookNode = nbf.read(dest, as_version=4)
    if index is None:
        index = next((i for i, e in enumerate(nb['cells']) if HOOK in e['source']), -1)
    if index < 0:
        raise Exception('Cannot find IPS notebook node')
    ips_cell: str = nb['cells'][index]['source']

    if ips_cell.find(f"f'{{{DIRECTORY_VARIABLE_NAME}}}{data_file}',\n]") != -1:
        # The data file is already referenced in the notebook, so there's nothing else to do
        return

    # data file does not exist, so we need to add it
    # search from right of string for the ']' character, should work assuming user does not modify the cell past the variable definition
    result = replace_last(ips_cell, ']', f"f'{{{DIRECTORY_VARIABLE_NAME}}}{data_file}',\n]")
    nb['cells'][index]['source'] = result

    with open(dest, 'w') as f:
        nbf.write(nb, f)


def remove_data_file_from_notebook(dest: str, data_file: str, index: Optional[int] = None):
    """Remove a specific data file from the notebook list.

    Params:
      - dest: path to notebook which will be modified
      - data_file: data file we remove from the notebook
      - index: optional index of the IPS notebook cell. If not provided, search through the notebook via an expected string hook.
    """
    nb: nbf.NotebookNode = nbf.read(dest, as_version=4)
    if index is None:
        index = next((i for i, e in enumerate(nb['cells']) if HOOK in e['source']), -1)
    if index < 0:
        raise Exception('Cannot find IPS notebook node')
    ips_cell: str = nb['cells'][index]['source']

    head, sep, tail = ips_cell.rpartition(f"f'{{{DIRECTORY_VARIABLE_NAME}}}{data_file}',\n")
    if sep == '':
        # existing match not found, so there's nothing left to remove
        return
    result = f'{head}\n{tail}'
    nb['cells'][index]['source'] = result

    with open(dest, 'w') as f:
        nbf.write(nb, f)


def remove_last_data_file_from_notebook(dest: str, index: Optional[int] = None) -> Optional[str]:
    """Obtain the last data file entry in a notebook, remove it, and then return the name of the file.

    Note that this function assumes the notebook maintains a specific format.

    Returns:
      - None if there were no data entries in the notebook, the name of the file removed (without the directory) as a string if there was
    """
    nb: nbf.NotebookNode = nbf.read(dest, as_version=4)
    if index is None:
        index = next((i for i, e in enumerate(nb['cells']) if HOOK in e['source']), -1)
    if index < 0:
        raise Exception('Cannot find IPS notebook node')
    ips_cell: str = nb['cells'][index]['source']

    search_hook = f"f'{{{DIRECTORY_VARIABLE_NAME}}}"

    start_index = ips_cell.rfind(search_hook)
    if start_index == -1:
        # no data files have been added, nothing to do
        return None

    ret = None
    file_name_start_index = start_index + len(search_hook)
    end_index = file_name_start_index
    while True:
        try:
            end_char = ips_cell[end_index]
            end_index += 1
            if end_char == '\n':
                # each entry gets its own "line", so we don't need to search anymore
                break
            if ips_cell[end_index] == "'" and ips_cell[end_index - 1] != '\\':
                # we have found the name of the file
                ret = ips_cell[file_name_start_index:end_index]
        except IndexError:
            # improperly formatted file (reached EOF), fall back to just removing everything after the break
            return None

    result = ips_cell[:start_index] + ips_cell[end_index:]
    nb['cells'][index]['source'] = result

    with open(dest, 'w') as f:
        nbf.write(nb, f)

    return ret
