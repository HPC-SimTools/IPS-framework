User Guides
===========

This directory has all of the user guides for using the IPS (see the component and portal user guides for further information pertaining to those topics).  It is organized in a series of *basic IPS usage* topics and *advanced IPS usage* topics, both are chock-full of examples and skeletons.

**How do I know if I am a Basic or Advanced user?**
  Basic IPS usage documents contain information that is intended for those who have run a few simulations and need a refresher on how to set up and run an existing simulation.  These documents will help users run or make small modifications to existing simulations, including ways the IPS and other utilities can be used to examine scientific problems.

  Advanced IPS usage documents contain information for *writers* of drivers and components.  These documents will help those who wish to make new components and drivers, make significant changes to an existing component or driver, examine the performance of the IPS and components, or those who would like to understand how to use the multiple levels of parallelism and asynchronous communication mechanisms effectively.

**Basic IPS Usage**

:doc:`Introduction to the IPS<basic_guide>`
    A handy reference for constructing and running applications, this document helps users through the process of running a simulation based on existing components.  It also includes: terminology, examples, and guidance on how to translate a computational or scientific question into a series of IPS runs.

:doc:`The Configuration File - Explained<config_file>`:
    Annotated version of the configuration file with explanations of how and why the values are used in the framework and components.

:doc:`Using the Plasma State<plasma_state>`:
    Essential guide to what the Plasma State is, the data it contains, and how to use it.  This will go more in-depth than the component and driver writing guide, but less than the developers guide.  It should contain how the PS is supposed to be used in various coupled simulation scenarios.

:doc:`Platform Configuration File - Explained<platform>`:
    Annotated platform configuration file and explanation of the manual allocation specification interface.

:doc:`Examples<examples_listing>`:
    Sets of config files, batch scripts and more for users to use and modify for their own purposes.


**Advanced IPS Usage**

:doc:`The IPS for Driver and Component Developers<advanced_guide>`:
    This guide contains the elements of components and drivers, suggestions on how to construct a simulation, how to add the new component to a simulation and the repository, as well as, an IPS services guide to have handy when writing components and drivers.  This guide is for components and drivers based on the *generic driver* model.  More sophisticated logic and execution models are covered in the following document.

:doc:`The New IPS for Driver and Component Developers<advanced_guide_new>`:
    This guide contains the elements of a simulation and an introduction to complex workflow management and the use of the Framework for managing multiple runs.

:doc:`Developing against the Framework Application Programming Interface<api_guide>`:
    Explanation of the various API features the Framework uses and offers. The Services API provides access to the Component Invocation API, Task Launch API, Data Management API, Configuration Parameter Access API, Logging API, Fault Tolerance API, Event Service API, and other miscilaneous interfaces.

:doc:`Developing Drivers and Components for IPS Simulations<component_guide>`:
    Explanations of the design of components, how to write components to include new physics binaries and manage data coupling, how to write a component and add it to the build system, and how to test and debug a component. Further explanations on driver development are also included.

:doc:`Fundamentals of the Advanced Features of the IPS<advanced_parallelism>`:
    Explanation of the different levels of parallelism, and other advanced features of the IPS in abstract terms, followed by examples.  This is for the planning stages of simulation composition.

:doc:`Performance Analysis<perf_anal>`:
    How to gather performance data for the IPS and its constituent tasks using Tau.

:doc:`Examples<examples_listing>`:
    A listing of example files mentioned in this section.


.. **User Guides Table of Contents**

.. toctree::
   :maxdepth: 1
   :hidden:

   basic_guide
   advanced_guide
   config_file
   platform
   plasma_state
   advanced_parallelism
   perf_anal
   examples_listing

