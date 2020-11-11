Installing IPS
==============

Download IPS from source

.. code-block:: bash

  git clone https://github.com/HPC-SimTools/IPS-framework.git

Install in current python environment, from within the IPS-framework
source directory

.. code-block:: bash

  pip install .
  # or
  python setup.py install

If you are using the system python and don't want to install as root
you can do a user only install with

.. code-block:: bash

  python setup.py install --user

Install in develop mode (this doesn't actually install the package but
creates an egg link)

.. code-block:: bash

  python setup.py develop
  # or
  pip install -e .

``ips.py`` should now be installed in your ``PATH`` and you should be
able to run
``ips.py --config=simulation.config --platform=platform.conf``


Note: you may need to use ``pip3`` and ``python3`` if you default
python is not python3.

Create and install in conda environment
---------------------------------------

First you need conda, you can either install the full `Anaconda
package <https://www.anaconda.com/downloads>`_ or `Minconda
<https://docs.conda.io/en/latest/miniconda.html>`_ (recommenced) which
is a minimal installer for conda.

First create a conda environment and activate it, this environment is named
``ips``. You can use any version of python >= 3.6

.. code-block:: bash

  conda create -n ips python=3.9
  conda activate ips

Next install IPS into this environment. From within the IPS-framework
source directory

.. code-block:: bash

  python setup.py install

And you are good to go.

To leave your conda environment

.. code-block:: bash

  conda deactivate
