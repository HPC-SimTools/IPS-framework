Manual Platform Settings
========================

This document describes how to run the IPS on an arbitrary platform (such as your laptop) that does *not* have a platform file.  Note that you will need to insure that the environment is set up properly and all dependencies are satisfied.

The platform configuration file contains platform specific information that the framework needs.  Typically, it does not need to be changed from one user to another or one run to another.  For certain manual settings, it may need to be changed with each batch submission.

Example Platform Configuration File - Franklin
----------------------------------------------
::

  HOST = franklin
  MPIRUN = aprun
  PHYS_BIN_ROOT = /project/projectdirs/m876/phys-bin/phys/
  DATA_TREE_ROOT = /project/projectdirs/m876/data
  DATA_ROOT = /project/projectdirs/m876/data/
  PORTAL_URL = http://swim.gat.com:8080/monitor
  RUNID_URL = http://swim.gat.com:4040/runid.esp

**HOST**
	name of the platform.  Used by the resource manager to determine which resource detection strategy will work.
**MPIRUN**
	command to launch parallel applications.  Used by the task manager to launch parallel tasks on compute nodes.
**\*_ROOT**
	locations of data and binaries.  Used by the configuration file and components to run the tasks of the simulation.
**\*_URL**
	portal URLs.  Used to connect and communicate with the portal.

Machines that have platform configuration files or can be detected by the resource manager:

* franklin
* hopper
* odin
* stix
* pacman
* pingo
* jaguar
* viz
* mhd

Manual Allocation Specification
-------------------------------
::

  HOST = <anything but the machine names above!>
  NODES = 4
  CORES_PER_NODE = 4

If you are going to manually specify the number of nodes and processes per node, you are responsible for the accuracy of the information.  The resource manager will use the number of nodes and number of cores per node to manage the resource allocation for the simulation.  Currently, the IPS trunk implementation allocates only *whole nodes* to tasks, and the *cores per node* will be used as the maximum (default) *processes per node*.  There is a branch implementation that allows the allocation at the granularity of *cores* and *sockets* in addition to *nodes*, thus allowing multiple tasks executing on the same node.

The hostname should be a single string (no spaces) and needs to not be one of the names that have been ported.  The logic to detect the manual specification is only triggered when the hostname is not recognized.

This manual interface is useful for personal machines like laptops and desktops, as well as when you are working on porting to a new machine and it isn't quite right yet but you need to get some work done.  If you have trouble with this interface contact Samantha Foley or Wael Elwasif.