=======================
Installing IPS on NERSC
=======================

NERSC recommends the use of anaconda environments to manage python
installs, see `Brief introduction to Python at NERSC
<https://docs.nersc.gov/development/languages/python>`_.

There is a conda environment already constructed and maintained for
the *atom* project created using the `shareable environment`_
method. You can activate it and run IPS by:

.. code-block:: bash

   module load python
   source activate /global/common/software/atom/cori/ips-framework-new
   ips.py --config=simulation.config --platform=platform.conf

Creating you own conda environment
----------------------------------

This guide will go through creating a conda environment on NERSC and
installing the IPS Framework using `Option 2: Module + source activate
<https://docs.nersc.gov/development/languages/python/nersc-python/#option-2-module-source-activate>`_

First, you need to load the python module, then create and activate a
new conda environment. This will create the conda environment in your
home directory (``$HOME/.conda/envs``):

.. code-block:: bash

  module load python
  conda create --name my_ips_env python=3.8 # or any version of python >=3.6
  source activate my_ips_env

If you would like the same packages and versions in your conda
environment as found in the python modules on Cori, you can clone that
environment. In this case using ``python/3.7-anaconda-2019.10``.

.. code-block:: bash

  module load python/3.7-anaconda-2019.10
  conda create -n my_ips_env --clone base
  source activate my_ips_env

Next, install IPS-Framework into the conda environment

.. code-block:: bash

  python -m pip install ipsframework

To leave your environment

.. code-block:: bash

  conda deactivate

The example below shows how to select the newly create conda
environment in a batch script, see `Running Python in a batch job
<https://docs.nersc.gov/development/languages/python/#running-python-in-a-batch-job>`_

.. code-block:: bash

  #!/bin/bash
  #SBATCH --constraint=haswell
  #SBATCH --nodes=1
  #SBATCH --time=5

  module load python
  source activate my_ips_env
  ips.py --config=simulation.config --platform=platform.conf

.. _shareable environment:

Creating a shareable environment on /global/common/software
-----------------------------------------------------------

By default when you create a conda environment it will be created in
``$HOME/.conda/envs``, to create one elsewhere that can be used by
others you can use the ``--prefix`` option, see `Creating conda
environments
<https://docs.nersc.gov/development/languages/python/nersc-python/#creating-conda-environments>`_.

In this example we are cloning the conda environment from the
``python/3.7-anaconda-2019.10`` module and install ``ipsframework``.

.. code-block:: bash

  module load python/3.7-anaconda-2019.10
  conda create --prefix /global/common/software/myproject/env --clone base
  source activate /global/common/software/myproject/env
  python -m pip install ipsframework

The example below shows how to select the newly create conda
environment in you batch script, see `Running Python in a batch job
<https://docs.nersc.gov/development/languages/python/#running-python-in-a-batch-job>`_

.. code-block:: bash

  #!/bin/bash
  #SBATCH --constraint=haswell
  #SBATCH --nodes=1
  #SBATCH --time=5

  module load python
  source activate /global/common/software/myproject/env
  ips.py --config=simulation.config --platform=platform.conf

Installing dependencies
~~~~~~~~~~~~~~~~~~~~~~~

To see which packages are currently install in your environment run:

.. code-block:: bash

   conda list

You can install any other dependencies you need by

.. code-block:: bash

   conda install numpy matplotlib netcdf4 ...

User development
~~~~~~~~~~~~~~~~

You should keep your development environment separate from the
production environment. If you do development in your ``my_ips_env``
conda environment you can switch between that and the production
environment on the atom project by

.. code-block:: bash

   # switch to production environment
   source activate /global/common/software/atom/cori/ips-framework-new

   # switch bask to user development environment
   source activate my_ips_env

Your bash prompt should be updated to reflect which environment you
have active.
