#!/usr/bin/env python3
from setuptools import setup, find_packages
import versioneer

long_description = """# Integrated Plasma Simulator (IPS) Framework

The IPS was originally developed for the SWIM project and is designed
for coupling plasma physics codes to simulate the interactions of
various heating methods on plasmas in a tokamak. The physics goal of
the project is to better understand how the heating changes the
properties of the plasma and how these heating methods can be used to
improve the stability of plasmas for fusion energy production.

The IPS framework is thus designed to couple standalone codes flexibly
and easily using python wrappers and file-based data coupling. These
activities are not inherently plasma physics related and the IPS
framework can be considered a general code coupling framework. The
framework provides services to manage:

 - the orchestration of the simulation through component invocation,
    task launch and asynchronous event notification mechanisms
 - configuration of complex simulations using familiar syntax
 - file communication mechanisms for shared and internal (to a
    component) data, as well as checkpoint and restart capabilities

The framework performs the task, configuration, file and resource
management, along with the event service, to provide these features.
"""

setup(
    name="ipsframework",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url="https://ips-framework.readthedocs.io",
    project_urls={
        'Documentation': 'https://ips-framework.readthedocs.io',
        'Source': 'https://github.com/HPC-SimTools/IPS-framework',
        'Tracker': 'https://github.com/HPC-SimTools/IPS-framework/issues',
    },
    description="Integrated Plasma Simulator (IPS) Framework",
    license='BSD',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ips.py = ipsframework.ips:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    zip_safe=True
)
