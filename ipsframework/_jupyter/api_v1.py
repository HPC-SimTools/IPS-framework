"""This file is meant to be directly imported and utilized in the Jupyter analysis stage when comparing multiple runs."""

import datetime
import importlib.util
import os
import tarfile
from pathlib import Path
from typing import Dict, Iterable, Union

THIS_DIR = Path(__file__).resolve().parent


def get_data_from_runid(runid: int) -> Dict[float, str]:
    """Load all data associated with a single runid into a dictionary.

    Params:
      - runid: the run id we're working with

    Returns:
      - a dictionary mapping timesteps to associated data file paths.
    """
    spec = importlib.util.spec_from_file_location('', f'{os.path.join(THIS_DIR, str(runid), "data_listing.py")}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DATA_FILES


def get_data_from_runids(runids: Iterable[int]) -> Dict[int, Dict[float, str]]:
    """Load all data associated with multiple runids into a common data structure.

    Params:
      - runids: iterable of existing runids (note that it is the caller's responsibility to verify uniqueness)

    Returns:
      - a dictionary of runids to the common runid data structure. This data structure is a mapping of timesteps to associated data file paths.
    """
    return {runid: get_data_from_runid(runid) for runid in runids}


def generate_tar_from_runids(runids: Union[Iterable[int], int]) -> str:
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
        for api_file in THIS_DIR.glob('api_v*.py'):
            archive.add(api_file, arcname=os.path.join(tarball_name, api_file.name))

        if isinstance(runids, int):
            runids = [runids]

        # add runids in directory
        for runid in runids:
            arcname = os.path.join(tarball_name, str(runid))
            archive.add(os.path.join(THIS_DIR, str(runid)), arcname=arcname)

    return str(tarball)
