from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "Papaya",
    version = "0.0.1pre1",
    install_requires = ['BytecodeAssembler>=0.3'],
)
