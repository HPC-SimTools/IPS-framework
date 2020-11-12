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

:doc:`Platform Configuration File - Explained<platform>`:
    Annotated platform configuration file and explanation of the manual allocation specification interface.

**Advanced IPS Usage**

:doc:`The IPS for Driver and Component Developers<advanced_guide>`:
    This guide contains the elements of components and drivers, suggestions on how to construct a simulation, how to add the new component to a simulation and the repository, as well as, an IPS services guide to have handy when writing components and drivers.  This guide is for components and drivers based on the *generic driver* model.  More sophisticated logic and execution models are covered in the following document.

:doc:`Migration from old IPS to new IPS<migration>`
     A guide on converting from the old (up to July 2020) way of doing things to the new way.

:doc:`Setting up environment on NERSC<nersc_conda>`
     How to setup conda environments on NERSC for using IPS.

.. **User Guides Table of Contents**

.. toctree::
   :maxdepth: 1

   basic_guide
   config_file
   platform
   advanced_guide
   migration
   nersc_conda

