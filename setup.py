#!/usr/bin/env python
from setuptools import setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.rst") as changelog_file:
    changelog = changelog_file.read()

requirements = [
    "packaging",
    "pyyaml",
    "jinja2",
    "colorama",
    "typing_extensions",
]


setup(
    name="conda-devenv",
    description="Work with multiple projects in develop-mode using conda-env",
    long_description=readme + "\n\n" + changelog,
    author="ESSS",
    url="https://github.com/ESSS/conda-devenv",
    packages=[
        "conda_devenv",
    ],
    entry_points={
        "console_scripts": [
            "conda-devenv = conda_devenv.devenv:main",
            "mamba-devenv = conda_devenv.devenv:mamba_main",
        ]
    },
    use_scm_version={"write_to": "src/conda_devenv/_version.py"},
    setup_requires=["setuptools_scm"],
    package_dir={"": "src"},
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords="conda_devenv",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    test_suite="tests",
)
