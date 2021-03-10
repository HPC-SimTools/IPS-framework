==========
IPS Portal
==========

The `IPS portal <http://lb.ipsportal.production.svc.spin.nersc.org/>`_
hosted on the `NERSC Spin <https://docs.nersc.gov/services/spin/>`_
service, shows the progress and status of IPS runs on a variety of
machines.  The simulation configuration file and platform
configuration file contain entries that allow the IPS to publish
events to the portal.

On the top-level page, you will see information about each run
including who ran it, the current status, physics time stamp, wall
time, and a descriptive comment.  From there you can click on a Run ID
to see the details of that run, including calls on components, data
movement events, task launches and finishes, and checkpoints.

To use the portal include

.. code-block:: text

   PORTAL_URL = http://lb.ipsportal.production.svc.spin.nersc.org

in either your :doc:`Platform Configuration File<platform>` or your
:doc:`Simulation Configuration File<config_file>`.
