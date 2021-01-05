#!/usr/bin/env python3
from setuptools import setup, find_packages
import versioneer

setup(
    name="ipsframework",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url="https://github.com/HPC-SimTools/IPS-framework",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ips.py = ipsframework.ips:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
