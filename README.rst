============
conda-devenv
============


.. image:: https://img.shields.io/pypi/v/conda-devenv.svg
        :target: https://pypi.python.org/pypi/conda-devenv

.. image:: https://img.shields.io/travis/ESSS/conda-devenv.svg
        :target: https://travis-ci.org/ESSS/conda-devenv

.. image:: https://readthedocs.org/projects/conda-devenv/badge/?version=latest
        :target: https://conda-devenv.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/esss/conda-devenv/shield.svg
     :target: https://pyup.io/repos/github/esss/conda-devenv/
     :alt: Updates


A tool to work with multiple projects in develop-mode using conda-env.

.. code-block:: console

    $ cat environment.devenv.yml
    {% set CONDA_PY = os.environ.get('CONDA_PY', '27') %}
    name: awesome-project-py{{ CONDA_PY }}

    includes:
      - {{ root }}/../other-project/environment.devenv.yml

    dependencies:
      {% if sys.platform.startswith('linux') %}
      - gcc
      - ccache
      {% else %}
      - clcache=3*

    environment:
      PYTHONPATH:
        - {{ root }}/source/python

      {% if sys.platform.startswith('linux') %}
      CCACHE_BASEDIR: {{ os.path.abspath(os.path.join(root, '..', '..')) }}
      CC: ccache gcc
      CXX: ccache g++
      LD_LIBRARY_PATH:
        - {{ root }}/artifacts-py{{ CONDA_PY }}/libs

      {% else %}
      PATH:
        - {{ root }}\artifacts-py{{ CONDA_PY }}\libs
      CLCACHE_BASEDIR: {{ os.path.abspath(os.path.join(root, '..', '..')) }}
      CLCACHE_NODIRECT: 1
      CLCACHE_OBJECT_CACHE_TIMEOUT_MS: 3600000
      CC: clcache
      CXX: clcache

      {% endif %}

    $ cat ../other-project/environment.devenv.yml
    name: other-project
    dependencies:
      - jinja2

    environment:
      PYTHONPATH:
        - {{ root }}/source/python

    $ conda devenv
    > Executing: conda env update --file environment.yml --prune
    Fetching package metadata .........
    Solving package specifications: ..........
    Linking packages ...
    [      COMPLETE      ]|#################################################################################################################################################################| 100%
    #
    # To activate this environment, use:
    # > source activate awesome-project-py27
    #
    # To deactivate this environment, use:
    # > source deactivate awesome-project-py27
    #

    $ source activate awesome-project-py27

    $ env PYTHONPATH
    env PYTHONPATH
    /home/muenz/Projects/temp/other-project/source/python
    /home/muenz/Projects/temp/awesome-project/source/python

    $ echo $CC
    ccache gcc


Features
--------

* Jinja2 support
* Include other *.devenv.yml files
* Environment variables

License
-------
Free software: MIT license

Documentation
-------------

https://conda-devenv.readthedocs.io.
