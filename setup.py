#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="ipsframework",
    version="0.1.0",
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
