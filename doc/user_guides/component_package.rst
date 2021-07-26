Create a component package
==========================

This is an example creating a hello world component installable
package. This is also an example of using ``MODULE`` instead of
``SCRIPT`` in the component configuration section.

The examples will be a simple hello world with one driver and one
worker. The only requirement of the package is ``ipsframework``. The
ipsframework should be automatically installed from pypi when install
ipsexamples but you can manually install it from pypi with

.. code-block:: bash

    python -m pip install ipsframework

Or to install it directly from github you can do

.. code-block:: bash

    python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git

To create this project locally, create the following file structure

.. code-block:: text

  helloworld
  ├── helloworld
  │   ├── __init__.py
  │   ├── hello_driver.py
  │   └── hello_worker.py
  └── setup.py

The file :download:`__init__.py <../examples/helloworld/helloworld/__init__.py>` is just
empty but turns the `helloworld` folder into a python module.

A simple :download:`setup.py <../examples/helloworld/setup.py>` would be

.. literalinclude:: ../examples/helloworld/setup.py

The :download:`hello_driver.py <../examples/helloworld/helloworld/hello_driver.py>` in the most simplest form would be

.. literalinclude:: ../examples/helloworld/helloworld/hello_driver.py

And the :download:`hello_worker.py <../examples/helloworld/helloworld/hello_worker.py>` is

.. literalinclude:: ../examples/helloworld/helloworld/hello_worker.py

This `helloworld` package can be installed with

.. code-block:: bash

  python -m pip install .

Or to install it in editable mode with

.. code-block:: bash

  python -m pip install -e .

With the components installed as a package you can reference them by
``MODULE`` instead of providing the full path with ``SCRIPT``. So to use
the `hello_driver` you do ``MODULE = helloworld.hello_driver``, and
for `hello_worker` you can do ``MODULE = helloworld.hello_worker``.

A simple config to run this is, :download:`helloworld.config <../examples/helloworld.config>`

.. literalinclude:: ../examples/helloworld.config
   :language: text

And you need a platform file, :download:`platform.conf <../examples/platform.conf>`

.. literalinclude:: ../examples/platform.conf
   :language: text

So after installing `ipsframework` and `helloworld` you can run it with

.. code-block:: bash

  ips.py --config=helloworld.config --platform=platform.conf

and you should get the output

.. code-block:: text

  Created <class 'helloworld.hello_driver.hello_driver'>
  Created <class 'helloworld.hello_worker.hello_worker'>
  hello_driver: beginning step call
  Hello from hello_worker
  hello_driver: finished step call

Using PYTHONPATH instead of installing the package
--------------------------------------------------

If you don't want to install the package, this can still work if you
set your ``PYTHONPATH`` correctly. In this case you don't need the
``setup.py`` either.

You can run the helloworld example from within the directory without installing by

.. code-block:: bash

  PYTHONPATH=$PWD ips.py --config=helloworld.config --platform=platform.conf
