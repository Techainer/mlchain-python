#!/usr/bin/env python
import pkg_resources
import setuptools
import pathlib
import os
from setuptools import setup, find_packages

__version__ = "0.3.0"

project = "mlchain"

def readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
        return f.read()


with pathlib.Path('requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]

setup(
    name=project,
    version=__version__,
    description='MLchain Python Library',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='http://github.com/Techainer/mlchain-python',
    author='Techainer Inc.',
    author_email='admin@techainer.com',
    package_data={'mlchain.cli': ['mlconfig.yaml', 'mlchain_server.py'],'mlchain.server':['static/*','templates/*','templates/swaggerui/*']},
    include_package_data=True,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=install_requires,
    keywords=['mlchain', 'development', 'deployment ai', 'ai', 'artificial neural network', 'training', 'deploy',
              'deployment', 'monitoring', 'model', 'deep learning', 'machine learning'],
    zip_safe=False,
    setup_requires=[],
    dependency_links=[],
    python_requires='>=3',
    tests_require=[
        "pytest",
        "mock>=1.0.1",
    ],
    py_modules=['mlchain'],
    entry_points={"console_scripts": ["mlchain = mlchain.cli.main:main"]},

    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
