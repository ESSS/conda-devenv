#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'pyyaml',
    'jinja2',
]

test_requirements = [
    'pytest',
    'pytest-datadir',
]

setup(
    name='conda_devenv',
    version='0.8.1',
    description="Work with multiple projects in develop-mode using conda-env",
    long_description=readme + '\n\n' + history,
    author="Edison Gustavo Muenz",
    author_email='edisongustavo@gmail.com',
    url='https://github.com/ESSS/conda-devenv',
    packages=[
        'conda_devenv',
    ],
    entry_points={
        'console_scripts': [
            'conda-devenv = conda_devenv.devenv:main',
        ]
    },
    package_dir={'conda_devenv':
                 'conda_devenv'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='conda_devenv',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
