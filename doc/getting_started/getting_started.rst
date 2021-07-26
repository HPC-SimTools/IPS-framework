===============
Getting Started
===============

This document will guide you through the process of running an IPS simulation and describe the overall structure of the IPS.  It is designed to help you build and run your first IPS simulation.  It will serve as a tutorial on how to get, build, and run your first IPS simulation, but not serve as a general reference for constructing and running IPS simulations.  See the :doc:`Basic User Guides<../user_guides/user_guides>` for a handy reference on running and constructing simulations in general, and for more in-depth explanations of how and why the IPS works.

.. warning::

   The were major changes in IPS from the old (up to July 2020) way of
   doing things to a new way. See :doc:`../user_guides/migration`.

Obtaining, Dependencies, Platforms
==================================

The IPS code is currently located on the GitHub repository. In order to checkout a copy, you must have git installed on the machine you will be using. Once you have git you can check out the IPS thusly::

      git clone https://github.com/HPC-SimTools/IPS-framework.git

Dependencies
------------

**IPS Proper**

The IPS framework is written in Python_, and requires Python 3.6+.  There are a few other packages that may be needed for certain components or utilities.  The framework does use the Python package ConfigObj_, however the source is already included and no package installation is necessary (likewise for Python 3.6 and the processing module).

Other Utilities
---------------

**Resource Usage Simulator (RUS)**
  This is a utility for simulation the execution of tasks in the IPS
  for research purposes.

  Requires: Matplotlib_ (which requires Numpy_/Scipy_)

  .. warning::
     The RUS (Resource Usage Simulator) has not been updated to python
     3 or for the changes in IPS and will not function in it current
     state.

**Documentation**
  The documentation you are reading now was created by a Python-based
  tool called Sphinx.

  Requires: Sphinx_


***Plus*** anything that the components or underlying codes that you are using need (e.g., MPI, math libraries, compilers).  For the example in this tutorial, all packages that are needed are already available on the target machines and the shell configuration script sets up your environment to use them.

.. _Sphinx: https://www.sphinx-doc.org
.. _Matplotlib: https://matplotlib.org
.. _Numpy: https://numpy.org
.. _Scipy: https://numpy.org
.. _ConfigObj: http://configobj.readthedocs.io
.. _Python: http://python.org

.. _installing-ips:

Building and Setting up Your Environment
========================================

IPS itself doesn't have any dependencies to run except python version
≥ 3.6. There is an optional dependency `dask <https://dask.org>` that
will enable dask to be used for task pool scheduling, see
:meth:`ipsframework.services.ServicesProxy.submit_tasks`. IPS is
tested to work with dask and distributed ≥ 2.5.2 but may work with
earlier versions.

It is recommend to install IPS in an conda environment, see
:ref:`create conda`.


It can be simply installed with

.. code-block:: bash

  python -m pip install ipsframework

The latest development version of IPS can be installed directly from github with pip

.. code-block:: bash

  python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git

You can install a specific version by, for examples version ``v0.3.0``

.. code-block:: bash

  python -m pip install ipsframework==0.3.0
  # or
  python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git@v0.3.0


Otherwise you can download the source code and install from there.

.. _source install:

Installing IPS from source
--------------------------

The source code can be cloned with git from
https://github.com/HPC-SimTools/IPS-framework with either ssh:

.. code::

   git clone git@github.com:HPC-SimTools/IPS-framework.git

of over https:

.. code::

   git clone https://github.com/HPC-SimTools/IPS-framework.git

Install in current python environment, from within the IPS-framework
source directory

.. code-block:: bash

   python -m pip install .

If you are using the system python and don't want to install as root
you can do a user only install with

.. code-block:: bash

   python -m pip install --user .

``ips.py`` should now be installed in your ``PATH`` and you should be
able to run
``ips.py --config=simulation.config --platform=platform.conf``

Install in editable mode
~~~~~~~~~~~~~~~~~~~~~~~~

Installing in editable allows you to modify the source code and use it
in from you source directory without reinstalling. This doesn’t
actually install the package but creates an egg link.

.. code-block:: bash

   python -m pip install -e .

.. note::
   You may need to use ``pip3`` and ``python3`` if you default
   ``python`` is not ``python3``.

.. _create conda:

Create and install in conda environment
---------------------------------------

.. note::

   For specific instruction on setting up conda environments on NERSC
   set :doc:`../user_guides/nersc_conda`.

First you need conda, you can either install the full `Anaconda
package <https://www.anaconda.com/downloads>`_ or `Minconda
<https://docs.conda.io/en/latest/miniconda.html>`_ (recommenced) which
is a minimal installer for conda.

First create a conda environment and activate it, this environment is named
``ips``. You can use any version of python >= 3.6

.. code-block:: bash

  conda create -n ips python=3.9
  conda activate ips

Next install IPS into this environment in the same way as above. *e.g.*

.. code-block:: bash

  python -m pip install ipsframework

And you are good to go.

To leave your conda environment

.. code-block:: bash

  conda deactivate
