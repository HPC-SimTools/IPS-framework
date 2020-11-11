Install IPS on NERSC
====================

NERSC recommends the use of anaconda environments to mange python
installs, see `Brief introduction to Python at NERSC
<https://docs.nersc.gov/development/languages/python/overview/>`_.

Creating you own conda environment
----------------------------------

This guide will go through creating a conda environment on NERSC
installing the IPS Framework using `Option 2: Module + source activate
<https://docs.nersc.gov/development/languages/python/nersc-python/#option-2-module-source-activate>`_

First, you need to load the python module, then create and activate a
new conda environment. This will create the conda environment in your
home directory

.. code-block:: bash

  module load python
  conda create --name my_ips_env python=3.8 # or any version of python >=3.6
  source activate my_ips_env

Next, get download the IPS Framework and install it into the conda
environment

.. code-block:: bash

  git clone https://github.com/HPC-SimTools/IPS-framework.git
  cd IPS-framework
  pip install .

To leave your environment

.. code-block:: bash

  conda deactivate

The example below show how to select the newly create conda
environment to run use, see `Running Python in a batch job
<https://docs.nersc.gov/development/languages/python/overview/#running-python-in-a-batch-job>`_

.. code-block:: bash

  #!/bin/bash
  #SBATCH --constraint=haswell
  #SBATCH --nodes=1
  #SBATCH --time=5

  module load python
  source activate my_ips_env
  ips.py --config=simulation.config --platform=platform.conf

Creating a shareable environment on /global/common/software
-----------------------------------------------------------

Creating an conda environment on /global/common/software is the
recommend way to have one environment shared between many uses, this
is covered by `Option 4a: Install your own Python without containers
<https://docs.nersc.gov/development/languages/python/nersc-python/#option-4a-install-your-own-python-without-containers>`_.
There may also be performance benefits to running from this location
instead of your home directory.

Following the instruction we do

.. code-block:: bash

  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash Miniconda3-latest-Linux-x86_64.sh -b -p /global/common/software/myproject/env
  source /global/common/software/myproject/env/bin/activate

Then install IPS into the environment, from within the IPS-framework
source directory::

  python setup.py install

The example below show how to select the newly create conda
environment to run use, see `Running Python in a batch job
<https://docs.nersc.gov/development/languages/python/overview/#running-python-in-a-batch-job>`_

.. code-block:: bash

  #!/bin/bash
  #SBATCH --constraint=haswell
  #SBATCH --nodes=1
  #SBATCH --time=5

  module load python
  source /global/common/software/myproject/env/bin/activate
  ips.py --config=simulation.config --platform=platform.conf
