#!/usr/bin/env python
from setuptools import setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name='gps_analysis',
    version='0.0.1',
    description='A python library for analysing gps data',
    author='Matthew Grifiths',
    author_email='matthewghgriffiths@gmail.com',
    url='https://github.com/matthewghgriffiths/gps_analysis',
    packages=['gps_analysis'],
    entry_points={
        'console_scripts': [
            'gps_analysis = world_rowing.cli:run [CLI]'
        ]
    },
    license='MIT', 
    long_description=long_description, 
    install_requires=[
        'numpy',
        'scipy',
        'pandas',
        'matplotlib',
        'gpxpy',
        'fitparse',
    ],
    extras_require={
        'CLI': ['cmd2>=2.0.0'],
        'CLI': ['garminconnect'],
        'REQ': ['requests'], # Requests is not required if using pyodide
    },
    python_requires=">=3.8",
    package_data={
        'gps_analysis': [
            'data/*.tsv', 
        ],
    }
)