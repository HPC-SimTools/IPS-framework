Introduction
============

Welcome to the documentation for the Integrated Plasma Simulator (IPS).  The documents contained here will provide information regarding obtaining, using and developing the IPS and some associated tools.  

The IPS was originally developed for the SWIM project and is designed for coupling plasma physics codes to simulate the interactions of various heating methods on plasmas in a tokamak.  The physics goal of the project is to better understand how the heating changes the properties of the plasma and how these heating methods can be used to improve the stability of plasmas for fusion energy production.

The IPS framework is thus designed to couple standalone codes flexibly and easily using python wrappers and file-based data coupling.  These activities are not inherently plasma physics related and the IPS framework can be considered a general code coupling framework.  The framework provides services to manage:

* the orchestration of the simulation through component invocation, task launch and asynchronous event notification mechanisms, 
* configuration of complex simulations using familiar syntax, 
* file communication mechanisms for shared and internal (to a component) data, as well as checkpoint and restart capabilities,

The framework performs the task, configuration, file and resource management, along with the event service, to provide these features.

Where to Start?
---------------

For those who have never run the IPS before, you should start with :doc:`Getting Started<getting_started/getting_started>`.  It starts from the beginning with how to obtain the IPS code, build and run some sample simulations on two different platforms.

The :doc:`User Guides<user_guides/user_guides>` section has documents on
basic and advanced user topics.  For those who have used the IPS before
or have done the tutorial and are ready to create their own run, the
:doc:`Reference Guide for Running IPS
Simulations<user_guides/basic_guide>` document walks you through the
process of using the IPS to examine a computational or physics problem,
with practical hints on what to consider through out the preparation,
running and analysis/debugging processes.  Additional documentation for
basic simulation construction include :doc:`The Configuration File -
Explained<user_guides/config_file>`.  :doc:`The IPS for Driver and
Component Developers<user_guides/advanced_guide>` provides component
developers with basic information on the construction of a component and
integrating it into the IPS, guidance on how to construct drivers and
IPS services API reference.  Additional documents on advanced topics
such as multiple levels of parallelism, computational considerations,
fault tolerance and performance analysis are located in the :doc:`User
Guides<user_guides/user_guides>` chapter.

Developers of the IPS framework and services, or brave souls who wish to understand how these pieces work, should look at the :doc:`code listings<the_code>`.  The code listings here will include internal and external APIs.  The developer guides include information about the design of the IPS at a high level and the framework and managers at a lower level to acquaint developers with the structures and mechanisms that are used in the IPS framework source code.

Acknowledgments
---------------

This documentation has been primarily written or adapted from other sources by Samantha Foley, as part of the SWIM team.  Don Batchelor provided examples and documentation that provided the basis for the :doc:`Getting Started<getting_started/getting_started>` and :doc:`Basic IPS Usage<user_guides/basic_guide>` sections.  Wael Elwasif provided much of the code documentation and initial documents on the directory structure and build process.
