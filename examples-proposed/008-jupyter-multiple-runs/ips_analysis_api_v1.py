"""DO NOT MODIFY OR RENAME THIS FILE YOURSELF.

This file consists of APIs meant to be utilized by Jupyter Notebooks."""

from __future__ import annotations

import datetime
import json
import os
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

THIS_DIR = Path(__file__).resolve().parent

ips_analysis_data_LIST_FILE = 'ips_analysis_api_data_listing.json'
IPS_CHILD_RUNS_FILE = 'ips_analysis_api_child_runs.txt'


class IpsRunApi:
    """This class should get used directly by notebooks directly associated with a run.

    The IPS Portal will insert a new code cell prior to your actual cells; this cell will initialize the `ips_analysis_api` object, an instance of this class.
    This object can be used in your own code to look up information about the run by calling various methods.
    None of the methods called should mutate any state.
    """

    def __init__(self, run_directory: Path):
        self._run_directory = run_directory

    def get_data(self) -> dict[float, list[str]]:
        """This returns a mapping of timesteps to a list of data filepaths associated with the timestep.

        Note that it is your responsibility to handle loading the actual data itself.
        """
        return _get_data_from_directory(self._run_directory)

    def get_child_data(self) -> dict[int, dict[float, list[str]]]:
        """This returns a mapping of this run's child runids to an additional mapping of timesteps to a list of data filepaths associated with the timestep.

        Note that it is your responsibility to handle loading the actual data itself.
        """
        child_runids = _get_children_ids_from_directory(self._run_directory)
        return get_data_from_runids(child_runids)


### FUNCTIONS - these can be used if making multi-run notebooks or if using the provided ips_analysis_api Jupyter notebook ###


def _normalize_data_filepaths(base_dir: Path, data: dict[str, list[str]]) -> dict[float, list[str]]:
    """Normalizes the data in the following ways:

    - Make sure the Python dictionary uses floating point keys (since JSON requires keys to be strings), and that the keys are in ascending order
    - Make sure all path strings in "data" are absolute paths instead of relative paths.
    """
    new_dict: dict[float, list[str]] = {}
    for str_timestep, file_path_list in data.items():
        timestep = float(str_timestep)
        new_dict[timestep] = file_path_list
        for idx, file_path in enumerate(file_path_list):
            new_dict[timestep][idx] = str(base_dir / Path(file_path))
    return {key: new_dict[key] for key in sorted(new_dict.keys())}


def _get_data_from_directory(directory: Path) -> dict[float, list[str]]:
    """'directory' should be an absolute path, not a relative path."""
    with open(directory / ips_analysis_data_LIST_FILE, 'rb') as f:
        data: dict[str, list[str]] = json.load(f)
    return _normalize_data_filepaths(directory, data)


def get_data_from_runid(runid: int) -> dict[float, list[str]]:
    """Load all data associated with a single runid into a dictionary.

    Params:
      - runid: the run id we're working with

    Returns:
      - a dictionary mapping timesteps to associated data file paths.
    """
    return _get_data_from_directory(THIS_DIR / str(runid))


def get_data_from_runids(runids: Iterable[int]) -> dict[int, dict[float, list[str]]]:
    """Load all data associated with multiple runids into a common data structure.

    Params:
      - runids: iterable of existing runids (note that it is the caller's responsibility to verify uniqueness)

    Returns:
      - a dictionary of runids to the common runid data structure. This data structure is a mapping of timesteps to associated data file paths.
    """
    return {runid: get_data_from_runid(runid) for runid in runids}


def _get_children_ids_from_directory(directory: Path) -> list[int]:
    with open(directory / IPS_CHILD_RUNS_FILE) as f:
        raw_data = f.read()
    return sorted(int(runid) for runid in raw_data.split())


def get_children_ids_by_parent_id(parent_runid: int) -> list[int]:
    """Get the runids of all child runs of the parent"""
    return _get_children_ids_from_directory(THIS_DIR / str(parent_runid))


def generate_tar_from_runids(runids: Iterable[int] | int) -> str:
    """
    Generate a tarball containing all data from the provided runs

    Params:
      - runids: list of runids where we want to include the data

    Returns:
      - the absolute path of the tarball generated
    """
    tarball_name = f'{datetime.datetime.now(datetime.timezone.utc).isoformat().replace(":", "-").replace("+", "_")}__ips_runs'
    tarball = THIS_DIR / f'{tarball_name}.tar.gz'
    with tarfile.open(tarball, 'w:gz') as archive:
        # add API files inside the tarball
        for api_file in THIS_DIR.glob('ips_analysis_api_v*'):
            if api_file.suffix in ('.py', '.ipynb'):
                arcname = os.path.join(tarball_name, api_file.name)
                archive.add(api_file, arcname=arcname)

        if isinstance(runids, int):
            runids = [runids]

        # add runids in directory
        for runid in runids:
            arcname = os.path.join(tarball_name, str(runid))
            archive.add(os.path.join(THIS_DIR, str(runid)), arcname=arcname)

    return str(tarball)
