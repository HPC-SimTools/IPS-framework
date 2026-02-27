.. _ips-portal:

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

To use the portal on your local cluster, include the following variables in your configuration file or as environment variables:

.. code-block:: text

   # make sure to set this if you actually want to use the portal
   USE_PORTAL = true
   # stable version
   PORTAL_URL = http://lb.ipsportal.production.svc.spin.nersc.org
   # or, for the latest version
   # PORTAL_URL = http://lb.ipsportal.development.svc.spin.nersc.org
   # The API key is required for certain interactions with the portal, and will eventually become mandatory. This key should generally be set as an environment variable, and not saved to version control.
   PORTAL_API_KEY = "YOUR_PORTAL_API_KEY"  # change this

NOTE: On shared clusters, i.e. Perlmutter, there will generally be specific files that you can source in Slurm scripts which will automatically configure the Portal credentials for you, so you can skip settings these variables yourself. Please see the appropriate project documentation for information on how to configure this.

The source code for the portal can be found on `GitHub
<https://github.com/HPC-SimTools/IPS-portal>`_ and issues can be
reported using `GitHub issues
<https://github.com/HPC-SimTools/IPS-portal/issues>`_.

in either your :doc:`Platform Configuration File<platform>` or your
:doc:`Simulation Configuration File<config_file>`.


Tracing
-------

.. note::

   New in IPS-Framework 0.6.0

IPS has the ability to capture a trace of the
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


Child Runs
----------

.. note::

   New in IPS-Framework 0.7.0

If you have a workflow where you are running ``ips`` as a task of
another IPS simulation you can create a relation between them that
will allow it to be viewed together in the IPS-portal and get a single
trace for the entire collection.

To setup the hierarchical structure between different IPS runs, so if
one run starts other runs as a separate simulation, you can set the
``PARENT_PORTAL_RUNID`` parameter in the child simulation
configuration. This can be done dynamically from the parent simulation
like:

.. code-block:: python

  child_conf['PARENT_PORTAL_RUNID'] = self.services.get_config_param("PORTAL_RUNID")

This is automatically configured when running
``ips_dakota_dynamic.py`` or when using the ``run_ensemble`` API.

The child runs will not appear on the main runs list but will appear
on a tab next to the events.

.. image:: child_runs.png

The trace of the primary simulation will contain the traces from all
the simulations:

.. image:: child_runs_trace.png

IPS-Framework APIs
------------------

Provided that the Portal has been enabled, the following APIs allow for interaction with the web portal:

Events API
==========

.. automethod:: ipsframework.services.ServicesProxy.send_portal_event
    :noindex:

This function can be used to send custom events to the Portal if the Portal is enabled; if the Portal is not enabled, the event will still be logged locally.

The events API does not currently require an API key to utilize, but this is expected to change in the future.

Jupyter API
===========

.. automethod:: ipsframework.services.ServicesProxy.initialize_jupyter_notebook
    :noindex:

.. automethod:: ipsframework.services.ServicesProxy.add_analysis_data_files
    :noindex:

All Jupyter APIs require that the Portal API key is set in order to utilize them.

If calling either of these APIs when the Portal is disabled, a warning will be logged and the call will be skipped.

Please see the `Jupyter <jupyter.html>`_ page for specifics on using the Jupyter APIs.

Ensembles API
=============

.. automethod:: ipsframework.services.ServicesProxy.run_ensemble
    :noindex:

If the Portal is enabled and the API key has been set, ``run_ensemble`` will automatically interact with the Portal to send appropriate files. 

If the Portal is disabled, ``run_ensemble`` will skip the Portal interaction, but will otherwise behave normally.

Please see the `Ensembles <ensembles.html>`_ page for specifics on using the Ensembles API.
