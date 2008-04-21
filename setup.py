from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "Papaya",
    version = "0.1pre1",
    install_requires = ['BytecodeAssembler>=0.3'],
    
    author = "Paul Bonser",
    author_email = "pib@paulbonser.com",
    description = "A Python bytecode assembler",
    license = "GPL",
    keywords = "python assembler papaya",
    url = "http://git.paulbonser.com/?p=ppya.git;a=summary",
    
    scripts = ['ppya.py'],
    
    entry_points = {
        'console_scripts': [
            'pyasm = ppya:main',
            'pydis = ppya:main',
        ],
    }
)
