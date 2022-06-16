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

   USE_PORTAL = True
   PORTAL_URL = http://lb.ipsportal.production.svc.spin.nersc.org


The source code for the portal can be found one `GitHub
<https://github.com/HPC-SimTools/IPS-portal>`_ and issues can be
reported using `GitHub issues
<https://github.com/HPC-SimTools/IPS-portal/issues>`_.

in either your :doc:`Platform Configuration File<platform>` or your
:doc:`Simulation Configuration File<config_file>`.


Tracing
-------

IPS (version >= 0.6.0) has the ability to capture a trace of the
workflow to allow analysis and visualizations. The traces are captured
in the `Zipkin Span format <https://zipkin.io/zipkin-api/>`_ and
viewed within IPS portal using `Jaeger
<https://www.jaegertracing.io/>`_.

After selecting a run in the portal there will be a link to the trace:

.. image:: run_list.png

.. image:: trace_link.png

The default view is the Trace Timeline but other useful views are
Trace Graph and Trace Statistic which can be selected from the menu in
the top-right:

.. image:: jaeger_options.png

The statistics can be further broken down by operation.

.. image:: statistics_sub_group.png

.. note::

   Self time (ST) is the total time spent in a span when it was not waiting on children. For example, a 10ms span with two 4ms non-overlapping children would have self-time = 10ms - 2 * 4ms = 2ms.
