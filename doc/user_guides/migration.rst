========================================
Migrating from old IPS v0.1.0 to new IPS
========================================

This is a guide on converting from the old (up to July 2020) way of
doing things to the new way.

The old version of IPS can be found at
https://github.com/HPC-SimTools/IPS-framework/releases/tag/v0.1.0 and
you can check it out by

.. code-block:: bash

  git clone -b v0.1.0 https://github.com/HPC-SimTools/IPS-framework.git

IPS was originally run in a mode where either it was install into a
directory with cmake or run from the source directory. The PYTHONPATH
and PATH was set to point to the framework/src directory. Thing where
imported directly from the modules.

Thing have changed, the package install is now managed with python
setuptools and the IPS framework is install as a package called
ipsframework, see :ref:`installing-ips`. The ips.py executable is also
installed in you current PATH. This means that you no longer need to
set PYTHONPATH or PATH when the IPS framework is installed. This
required a rearrangement of the source code.

Also with this change in the way the package is install there are
required code changes need to use it. The main one is that since this
is now a package everything must be imported from ipsframework, so
when writing components you can no longer do ``from component import
Component`` and must do ``from ipsframework import
Component``. Similarly if importing the framework directly you can not
do ``from ips import Framework`` and now must do ``from
ipsframework import Framework``.

Additionally the following changes have been made
 - These unused options have been remove from ips.py (``--component``,
   ``--clone``, ``--sim_name``, ``--create-runspace``,
   ``--run-setup``, ``--run``, ``--all``)
 - A new option for components ports now allows you to specify a
   ``MODULE`` instead of a ``SCRIPT``, this allows easy use of
   component that have been installed in the python environment.

These deprecated API will soon be removed and you should update you code:

+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
| class                                                              | deprecated API                                                             | new API                                                                     |
+====================================================================+============================================================================+=============================================================================+
|:py:class:`~ipsframework.configurationManager.ConfigurationManager` | :py:meth:`~ipsframework.configurationManager.ConfigurationManager.getPort` | :py:meth:`~ipsframework.configurationManager.ConfigurationManager.get_port` |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.getGlobalConfigParameter`   | :py:meth:`~ipsframework.services.ServicesProxy.get_config_param`            |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.getPort`                    | :py:meth:`~ipsframework.services.ServicesProxy.get_port`                    |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.getTimeLoop`                | :py:meth:`~ipsframework.services.ServicesProxy.get_time_loop`               |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.merge_current_plasma_state` | :py:meth:`~ipsframework.services.ServicesProxy.merge_current_state`         |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.stageCurrentPlasmaState`    | :py:meth:`~ipsframework.services.ServicesProxy.stage_plasma_state`          |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.stageInputFiles`            | :py:meth:`~ipsframework.services.ServicesProxy.stage_input_files`           |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.stageOutputFiles`           | :py:meth:`~ipsframework.services.ServicesProxy.stage_output_files`          |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.updatePlasmaState`          | :py:meth:`~ipsframework.services.ServicesProxy.update_plasma_state`         |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+
|:py:class:`~ipsframework.services.ServicesProxy`                    | :py:meth:`~ipsframework.services.ServicesProxy.updateTimeStamp`            | :py:meth:`~ipsframework.services.ServicesProxy.update_time_stamp`           |
+--------------------------------------------------------------------+----------------------------------------------------------------------------+-----------------------------------------------------------------------------+

These simulation configuration fields are deprecated and should be updated.

+---------------------------+--------------------+
| deprecated field          | new field          |
+===========================+====================+
| ``PLASMA_STATE_FILES``    | ``STATE_FILES``    |
+---------------------------+--------------------+
| ``PLASMA_STATE_WORK_DIR`` | ``STATE_WORK_DIR`` |
+---------------------------+--------------------+

The RUS (Resource Usage Simulator) has not been updated to python 3 or
for the changes in IPS and will not function in it current state.
