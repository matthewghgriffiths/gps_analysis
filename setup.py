#!/usr/bin/env python
from setuptools import setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name='gps_analysis',
    version='0.0.8',
    description='A python library for analysing gps data',
    author='Matthew Grifiths',
    author_email='matthewghgriffiths@gmail.com',
    url='https://github.com/matthewghgriffiths/gps_analysis',
    packages=['gps_analysis'],
    entry_points={
        'console_scripts': [
            'garmin = world_rowing.garmin:main [GARMIN]',
            'gpx = world_rowing.files:main'
        ]
    },
    license='MIT', 
    long_description=long_description, 
    install_requires=[
        'numpy',
        'pandas',
        'matplotlib',
        'gpxpy',
        'fitparse',
        'tqdm',
    ],
    extras_require={
        'GARMIN': ['garminconnect'],
    },
    python_requires=">=3.8",
    package_data={
        'gps_analysis': [
            'data/*.tsv', 
        ],
    }
)