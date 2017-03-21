=====
Usage
=====

``conda-devenv`` works by creating ``conda`` environments from definitions found in ``environment.devenv.yml`` files.

``environment.devenv.yml`` files are similar to ``environment.yml`` files processed by ``conda env``, with
additional support for:

Jinja2
======

You can use `Jinja 2 <http://jinja.pocoo.org/docs/2.9/>`_ syntax at will, which lets you do all sort of things
like conditionally add dependencies based on the current platform, change the default environment name
based python version, etc. For example:

.. code-block:: yaml

    {% set conda_py = os.environ.get('CONDA_PY', '35') %}
    name: web-ui-py{{ conda_py }}

    dependencies:
      {% if sys.platform.startswith('linux') %}
      - gcc
      {% endif %}


The following variables are available in the Jira 2 namespace:

* ``root``: this is the full path to the directory containing the ``environment.devenv.yml`` file;
* ``os``;
* ``sys``;
* ``platform``;


Environment Variables
=====================

It is possible to define environment variables that should be configured in the environment when activated.

.. code-block:: yaml

    environment:
      PATH:
        - {{ root }}/bin
      PYTHONPATH:
        - {{ root }}/source/python
      DB_LOCATION: https://localhost/dev

Environment variables defined in *list form* (like ``PATH`` and ``PYTHONPATH`` above) will **append** to existing
variables, using the appropriate separator for the platform (``:`` on Linux and ``;`` on Windows).

Environment variables defined as a single string (like ``DB_LOCATION`` above) will **overwrite** an existing
variable with the same name.

``conda-devenv`` restores the variables of the environment to their original state upon deactivation.

Includes
========

It is possible to use *include* directives to include one or more ``environment.devenv.yml`` files. This merges all
``dependencies`` and ``environment`` definitions into a single environment, which makes it a good solution to work
in one or more repositories in development mode.

For example:

``/home/user/projects/core/environment.devenv.yml``:

.. code-block:: yaml

    name: core
    dependencies:
      - numpy
      - pandas
      - pytest
      - invoke
    environment:
      PYTHONPATH:
        - {{ root }}/source/python


``/home/user/projects/web-ui/environment.devenv.yml``:

.. code-block:: yaml

    name: web-ui
    includes:
      - {{ root }}/../core/environment.devenv.yml
    dependencies:
      - flask
      - jinja2
    environment:
      PYTHONPATH:
        - {{ root }}/source/python
      PATH:
        - {{ root }}/bin

In this setup, all the user has to do is executing ``conda devenv``:

.. code-block:: console

    $ cd ~/projects/web-ui
    $ conda devenv

This will create a ``conda`` environment named ``web-ui`` containing all the dependencies and environment variables
defined in both files.

How it works
============

Here's how ``conda-devenv`` works behind the scenes:

1. Generate an ``environment.yml`` file in the same directory as the ``environment.devenv.yml`` file. The generated
   ``environment.yml`` should **not** be added to VCS.
2. Call ``conda env update --prune --file environment.yml``.
3. Generate ``devenv-activate.sh/.bat`` and ``devenv-deactivate.sh/.bat`` scripts in ``$PREFIX/etc/conda/activate.d``
   and ``$PREFIX/etc/conda/deactivate.d`` respectively which will set/unset the environment variables.


Command-line reference
======================

Default options
---------------

- ``conda-devenv`` creates a file name ``environment.yml`` at the same directory of the ``environment.devenv.yml`` file.

Options
-------


.. code-block:: console

    $ conda devenv --help

    usage: conda-devenv [-h] [--file [FILE]] [--name [NAME]] [--print]
                        [--no-prune] [--output-file [OUTPUT_FILE]] [--force]

    Work with multiple conda-environment-like yaml files in dev mode.

    optional arguments:
      -h, --help            show this help message and exit
      --file [FILE], -f [FILE]
                            The environment.devenv.yml file to process.
      --name [NAME], -n [NAME]
                            Name of environment.
      --print               Only prints the rendered file to stdout and exits.
      --no-prune            Don't pass --prune flag to conda-env.
      --output-file [OUTPUT_FILE]
                            Output filename.
      --force               Overrides the output file, even if it already exists.


``--file``
~~~~~~~~~~

The input file to be processed

``--print``
~~~~~~~~~~~

Prints the contents of the generated file and exits.

``--no-prune``
~~~~~~~~~~~~~~

Don't pass the ``--prune`` flag when calling ``conda env update``

``--output-file``
~~~~~~~~~~~~~~~~~

Specifies the ``conda-env`` file which will be created.

