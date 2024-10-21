"""
NOTE: this is not intended to be a public API for framework users, use instead:
  - "services.initialize_jupyter_notebook" (to set up the JupyterHub interaction for a notebook, done only once)
  - "services.add_analysis_data_file" (each time you want to add or remove a data file from JupyterHub)

This module is designed to help generate JupyterNotebooks to be used with IPS Portal analysis.
Some parts of the script will need direction from users on the Framework side to generate.

Note that this module is currently biased towards working with NERSC (jupyter.nersc.gov), so will attempt to import specific libraries.

To see available libraries on NERSC, run:
  !pip list

...in a shell on Jupyter NERSC.
"""

import re
import shutil
from pathlib import Path
from typing import Optional

import nbformat as nbf

DIRECTORY_VARIABLE_NAME = 'DATA_DIR'
DATA_VARIABLE_NAME = 'DATA_FILES'
DATA_MODULE_NAME = 'data_listing'
CURRENT_API_VERSION = 'v1'


def replace_last(source_string: str, old: str, new: str) -> str:
    """Attempt to replace the last occurence of 'old' with 'new' in 'source_string', searching from the right.

    This should only be called if 'old' can effectively be guaranteed to exist in the string.
    """
    head, _sep, tail = source_string.rpartition(old)
    return f'{head}{new}{tail}'


def _initial_data_file_code() -> str:
    return f"""# This file should be imported by a jupyter notebook or the generated API. DO NOT EDIT UNTIL IPS RUN IS FINALIZED.

import os
import pathlib

{DIRECTORY_VARIABLE_NAME} = str(pathlib.Path(__file__).resolve().parent / 'data') + os.path.sep
{DATA_VARIABLE_NAME} = {{
}}
"""


def _jupyter_notebook_api_code() -> bytes:
    """Return the raw code of the JupyterNotebook file which will be placed in the JupyterHub multirun file directory."""
    return b"""
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## IPS workstation\n",
    "\n",
    "You can use this notebook to quickly generate a tarfile with desired runids for download. "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "from pathlib import Path\n",
    "\n",
    "import api_v1\n",
    "from IPython.display import display\n",
    "from ipywidgets import HTML, Button, Layout, Textarea\n",
    "\n",
    "widget1 = Textarea(\n",
    "    value='',\n",
    "    placeholder='Enter runids you want to download, delimited by either spaces or newlines',\n",
    "    description='Enter runids you want to download, delimited by either spaces or newlines',\n",
    "    layout=Layout(width='50%', display='flex', flex_flow='column')\n",
    ")\n",
    "\n",
    "widget2 = Button(\n",
    "    description='Generate tar from input',\n",
    "    layout=Layout(width='300px')\n",
    ")\n",
    "\n",
    "def generate_tarfile(_button_widget):\n",
    "    runids = [int(v) for v in widget1.value.split()]\n",
    "    display(f'Generating tar file from runids: {runids}')\n",
    "    \n",
    "    file = Path(api_v1.generate_tar_from_runids(runids))\n",
    "    display(f'Generated tar file {file.name} in directory {file.parent}, right click the file in the file browser to download it')\n",
    "\n",
    "widget2.on_click(generate_tarfile)\n",
    "\n",
    "display(widget1,widget2,HTML(\"\"\"<style>\n",
    "    .widget-label { width: unset !important; }\n",
    "</style>\"\"\"))"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""


def initialize_jupyter_python_api(jupyterhub_dir: str):
    """Set up the multirun API files."""
    source_dir = Path(__file__).parent
    dest_dir = Path(jupyterhub_dir)

    python_fname = f'api_{CURRENT_API_VERSION}.py'
    shutil.copyfile(
        source_dir / python_fname,
        dest_dir / python_fname,
    )


    with open(dest_dir / f'api_{CURRENT_API_VERSION}_notebook.ipynb', 'wb') as f:
        f.write(_jupyter_notebook_api_code())


def initialize_jupyter_notebook(notebook_dest: str, notebook_src: str):
    """Create a new notebook from an old notebook, copying the result from 'src' to 'dest'.

    This adds an additional cell which will import the data files. The notebook should not be written again after this function.

    Params:
      - notebook_dest - location of notebook to create on filesystem (absolute file path)
      - notebook_src - location of source notebook on filesystem (is not overwritten unless src == dest)
    """
    # to avoid conversion, use as_version=nbf.NO_CONVERT
    nb: nbf.NotebookNode = nbf.read(notebook_src, as_version=4)

    nb['cells'] = [
        # explicitly mark the IPS cell for users inspecting the file, unused programatically
        nbf.v4.new_markdown_cell("""## Next cell generated by IPS Framework

Execute this cell again to use new data during the simulation.
"""),
        nbf.v4.new_code_cell(f"""
import importlib

import {DATA_MODULE_NAME}
importlib.reload({DATA_MODULE_NAME})
{DATA_VARIABLE_NAME} = {DATA_MODULE_NAME}.{DATA_VARIABLE_NAME}

"""),
    ] + nb['cells'][:]

    nbf.validate(nb)
    with open(notebook_dest, 'w') as f:
        nbf.write(nb, f)


def initialize_jupyter_import_module_file(dest: str):
    """Create a new notebook from an old notebook, copying the result from 'src' to 'dest'.

    Params:
      - dest - directory where we will create the module file on filesystem (absolute file path)
    """

    dest = f'{dest}{DATA_MODULE_NAME}.py'
    with open(dest, 'w') as f:
        f.write(_initial_data_file_code())


def update_module_file_with_data_file(dest: str, data_file: str, replace: bool, timestamp: float = 0.0) -> Optional[str]:
    """
    Params:
      - dest: directory of the module file which will be modified
      - data_file: file which will be added to the module
      - replace: if True, we can update
      - timestamp: key we associate the data file with

    Returns:
      - if we replaced a file, the name of the file which was replaced; otherwise, None
    """
    dest = f'{dest}{DATA_MODULE_NAME}.py'
    with open(dest, 'r') as f:
        old_module_code = f.read()

    replaced_file_name = None

    timestamp_regex = str(timestamp).replace('.', '\\.')
    directory_str = '\{' + DIRECTORY_VARIABLE_NAME + '\}'

    search_pattern = f"{timestamp_regex}: f'{directory_str}(.*)',"

    found_match = re.search(search_pattern, old_module_code)
    if found_match:  # timestamp already exists
        if replace:
            replaced_file_name = found_match.group(1)
            if replaced_file_name == data_file:
                # in this case, we're not actually removing an obsolete file, so no need to write to the module file
                # return None because we've already directly replaced the file
                return None
            new_module_code = re.sub(search_pattern, f"{timestamp}: f'{{{DIRECTORY_VARIABLE_NAME}}}{data_file}',", old_module_code)
        else:
            raise ValueError(
                f"For timestamp entry {timestamp}, you are trying to replace '{found_match.group(1)}' with '{data_file}' . If this was intended, you must explicitly set 'replace=True' on the IPS function call."
            )
    else:  # timestamp does not exist, so add it
        # search from right of string for the '}' character, should work assuming user does not modify the cell past the variable definition
        new_module_code = replace_last(old_module_code, '}', f"{timestamp}: f'{{{DIRECTORY_VARIABLE_NAME}}}{data_file}',\n" + '}')

    with open(dest, 'w') as f:
        f.write(new_module_code)

    return replaced_file_name
