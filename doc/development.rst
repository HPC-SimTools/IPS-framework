Developer Guide
===============

This document is for the development of IPS itself, if you want to
develop drivers and components for IPS simulations see :doc:`The IPS
for Driver and Component Developers<user_guides/advanced_guide>`.

Contributing
------------

You can report bugs (including security bugs) using `GitHub issues
<https://github.com/HPC-SimTools/IPS-framework/issues>`_.

Alternatively the developers can be contacted at `discussions
<https://github.com/HPC-SimTools/IPS-framework/discussions>`_.

Change requests can be made using `GitHub pull request
<https://github.com/HPC-SimTools/IPS-framework/pulls>`_.


Getting and installing IPS from source code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To get started you first need to obtain the source code, I suggest
installing in editable mode, see :ref:`source install`.

Development environment
~~~~~~~~~~~~~~~~~~~~~~~

IPS-framework doesn't have any required dependencies. It has an
optional dependency `Dask <https://dask.org>`_ that will enable Dask
to be used for task pool scheduling, see
:meth:`~ipsframework.services.ServicesProxy.submit_tasks`.

IPS-framework will work with python version ≥ 3.6. It is tested to work with
Dask and distributed ≥ 2.5.2 but may work with earlier versions.

IPS-framework will work on Linux and macOS. It won't work on Windows
directly but will work in the `Windows Subsystem for Linux
<https://docs.microsoft.com/en-us/windows/wsl>`_.

To run the tests requires ``pytest``, ``pytest-cov`` and
``psutil``. Optional dependencies are ``dask``/``distributed`` and
``mpirun``/``mpi4py`` which are needed to run all the tests.

It is recommend that you use conda but you also just install
dependencies using system packages or with PyPI in an virtual
environment.

Conda
^^^^^

To create a Conda environment with all testing dependencies run:

.. code-block:: bash

   conda create -n ips python=3.8 pytest pytest-cov psutil dask mpi4py sphinx
   conda activate ips

Code review expectations
------------------------

Code will need to conform to the style as enforced by flake8 and
should not introduce any new warnings or error from the static
analysis, see :ref:`Static Analysis`.

All new features should have an accompanying test where it should try
to include complete code coverage of the changes, see :ref:`testing`.

All new functionality should have complete docstrings. If appropriate,
further documentation or usage examples should be added, see
:ref:`docs`.

.. _testing:

Testing
-------

Running Tests
~~~~~~~~~~~~~

The `pytest <https://pytest.org>`_ framework is used for finding and
executing tests in IPS-framework.

To run the tests

.. code-block:: bash

   python -m pytest

To run test showing code coverage, install `pytest-cov` and run

.. code-block:: bash

   python -m pytest --cov

and the output will look like

.. code::

   ----------- coverage: platform linux, python 3.7.8-final-0 -----------
   Name                                    Stmts   Miss  Cover
   -----------------------------------------------------------
   ipsframework/__init__.py                   11      0   100%
   ipsframework/cca_es_spec.py                62     10    84%
   ipsframework/component.py                 105     19    82%
   ipsframework/componentRegistry.py         105     25    76%
   ipsframework/configurationManager.py      510    103    80%
   ipsframework/convert_log_function.py       29      1    97%
   ipsframework/dataManager.py                72     15    79%
   ipsframework/debug.py                       3      0   100%
   ipsframework/eventService.py              137     53    61%
   ipsframework/eventServiceProxy.py         118     49    58%
   ipsframework/ips.py                       360     51    86%
   ipsframework/ipsExceptions.py              61      2    97%
   ipsframework/ipsLogging.py                 92      8    91%
   ipsframework/ips_es_spec.py                43      7    84%
   ipsframework/ipsutil.py                    73     26    64%
   ipsframework/messages.py                   58      0   100%
   ipsframework/node_structure.py            193     31    84%
   ipsframework/platformspec.py               18      4    78%
   ipsframework/portalBridge.py              205     36    82%
   ipsframework/resourceHelper.py            304     59    81%
   ipsframework/resourceManager.py           340     69    80%
   ipsframework/runspaceInitComponent.py      88     31    65%
   ipsframework/sendPost.py                   41      2    95%
   ipsframework/services.py                 1200    234    80%
   ipsframework/taskManager.py               322     74    77%
   ipsframework/topicManager.py               59      5    92%
   -----------------------------------------------------------
   TOTAL                                    4609    914    80%


You can then also run ``python -m coverage report -m`` to show exactly
which lines are missing test coverage.


Writing Tests
~~~~~~~~~~~~~

The `pytest <https://pytest.org>`_ framework is used for finding and
executing tests in IPS-framework.

Tests should be added to ``tests`` directory. If writing component to
use for testing that should go into ``tests/components`` and any
executable should go into ``tests/bin``.

Continuous Integration (CI)
---------------------------

`GitHub Actions <https://docs.github.com/en/actions>`_ is used for `CI
<https://github.com/HPC-SimTools/IPS-framework/blob/main/.github/workflows/workflows.yml>`_
and will run on all pull requests and any branch including once a pull
request is merged into ``main``. Static analysis checks and the test
suite will run and report the code coverage to `Codecov
<https://app.codecov.io/gh/HPC-SimTools/IPS-framework>`_.

.. _static analysis:

Static Analysis
~~~~~~~~~~~~~~~

The following static analysis is run as part of CI

* `flake8 <https://flake8.pycqa.org>`_ - Style guide enforcement
* `pylint <https://pylint.org>`_ - Code analysis
* `bandit <https://bandit.readthedocs.io>`_ - Find common security issues
* `codespell <https://github.com/codespell-project/codespell>`_ - Check code for common misspellings

The configuration of these tools can be found in `setup.cfg
<https://github.com/HPC-SimTools/IPS-framework/blob/main/setup.cfg>`_.

Tests
~~~~~

The test suite runs on Linux and macOS with python versions from 3.6
up to 3.9. It is also tested with 3 different version of Dask,
``2.5.2``, ``2.30.0`` and the most recent version. The ``2.5.2``,
``2.30.0`` versions of Dask where chosen to match what is available on
Cori at NERSC in the modules ``python/3.7-anaconda-2019.10`` and
``python/3.8-anaconda-2020.11``.

The test suite also runs as part of the CI on Windows using WSL
(Ubuntu 20.04) just using the default system python version.

.. _docs:

Documentation
-------------

`sphinx <https://www.sphinx-doc.org>`_ is used to generate the
documentation for IPS. The docs are found in the ``doc`` directory and
the docstrings from the source code can included in the
documentation. The documentation can be built by running ``make html``
within the ``doc`` directory, the output will go to
``doc/_build/html``.

The docs are automatically build by `Read the Docs
<https://readthedocs.org>`_ when merged into ``main`` and deployed to
http://ips-framework.readthedocs.io. You can see the status of the
docs build by going to `here
<https://readthedocs.org/projects/ips-framework/>`_

Release process
---------------

We have no set release schedule and will create minor (add
functionality in a backwards compatible manner) and patch (bug fixes)
releases as needed following `Semantic Versioning
<https://semver.org>`_.

The deployment to `PyPI <https://pypi.org/project/ipsframework>`_ will
happen automatically by a GitHub Actions `workflow
<https://github.com/HPC-SimTools/IPS-framework/blob/main/.github/workflows/publish-to-test-pypi.yml>`_
whenever a tag is created.

Release notes should be added to
https://github.com/HPC-SimTools/IPS-framework/releases

We will publish a release candidate versions for any major or minor
release before the full release to allow feedback from users. Patch
versions will not normally have an release candidate.
