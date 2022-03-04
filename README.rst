============
conda-devenv
============

.. image:: https://github.com/ESSS/conda-devenv/workflows/main/badge.svg
    :target: https://github.com/ESSS/conda-devenv/actions

.. image:: https://readthedocs.org/projects/conda-devenv/badge/?version=latest
    :target: https://conda-devenv.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/conda/vn/conda-forge/conda-devenv.svg
    :target: https://anaconda.org/conda-forge/conda-devenv

.. image:: https://anaconda.org/conda-forge/conda-devenv/badges/downloads.svg
    :target: https://anaconda.org/conda-forge/conda-devenv

.. image:: https://anaconda.org/conda-forge/conda-devenv/badges/installer/conda.svg
    :target: https://anaconda.org/conda-forge/conda-devenv


``conda-devenv`` is ``conda`` extension to work with multiple projects in development mode.

It works by processing ``environment.devenv.yml`` files, similar to how ``conda env``
processes ``environment.yml`` files, with this additional features:

* `Jinja 2 <http://jinja.pocoo.org/docs/2.9/>`_ support: gives more flexibility to the environment
  definition, for example making it simple to conditionally add dependencies based on platform.

* ``include`` other ``environment.devenv.yml`` files: this allows you to easily work in several
  dependent projects at the same time, managing a single ``conda`` environment with your dependencies.

* **Environment variables**: you can define a ``environment:`` section with environment variables
  that should be defined when the environment is activated.

Here's a simple ``environment.devenv.yml`` file:

.. code-block:: yaml

    {% set conda_py = os.environ.get('CONDA_PY', '35') %}
    name: web-ui-py{{ conda_py }}

    includes:
      - {{ root }}/../core-business/environment.devenv.yml

    dependencies:
      - gcc  # [linux]

    environment:
      PYTHONPATH:
        - {{ root }}/src
      STAGE: DEVELOPMENT


To use this file, execute:

.. code-block:: console

    $ cd ~/projects/web-ui
    $ conda devenv
    > Executing: conda env update --file environment.yml --prune
    Fetching package metadata .........
    Solving package specifications: ..........
    Linking packages ...
    [      COMPLETE      ]|############################| 100%
    #
    # To activate this environment, use:
    # > source activate web-ui-py35
    #
    # To deactivate this environment, use:
    # > source deactivate web-ui-py35
    #

    $ source activate web-ui-py35

    $ env PYTHONPATH
    /home/user/projects/web-ui/src

    $ echo $STAGE
    DEVELOPMENT

mamba support
-------------

``conda-devenv`` also supports `mamba <https://mamba.readthedocs.io/en/latest/>`_.

As of today ``mamba`` is not auto detected and to use it with ``conda-devenv`` you can:

* Use the ``--env-manager`` (short version ``-e``), like ``mamba devenv -e mamba`` or ``conda devenv -e mamba``.

* Define the environment variable ``CONDA_DEVENV_ENV_MANAGER=mamba``.

* Call directly ``mamba-devenv`` (this normally work just in the conda's base envaronment).


Documentation
-------------

https://conda-devenv.readthedocs.io.

Development
-----------

Please see `CONTRIBUTING <CONTRIBUTING.rst>`_.


License
-------

Free software: MIT license
