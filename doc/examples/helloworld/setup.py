#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="helloworld",
    version="1.0.0",
    install_requires=["ipsframework==0.2.1"],
    packages=find_packages(),
)