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
      - boost
      - cmake
      - gcc     # [linux]
      - ccache  # [not win]
      - clcache # [win] Windows has clcache

Note that in the example above, we are able to define dependency requirements
that are specific to Linux, macOS, and Windows (e.g., ``ccache`` is needed in
Linux and macOS, whereas ``clcache`` is needed in Windows). This is one of the
most useful capabilities of ``conda-devenv``.

.. tip::

  You can actually write any Python expression that evaluates to a boolean
  inside the brackets following the YAML comment mark ``#``. For example,
  ``# [linux]`` could be replaced with ``# [sys.platform.startswith('linux')]``.

The following variables are available in the Jinja 2 namespace:

.. list-table::
   :widths: 20 80

   * - ``root``
     - The full path to the directory containing the ``environment.devenv.yml`` file.
   * - ``os``
     - The standard Python module object ``os`` obtained with ``import os``.
   * - ``sys``
     - The standard Python module object ``sys`` obtained with ``import sys``.
   * - ``platform``
     - The standard Python module object ``platform`` obtained with ``import platform``.
   * - ``x86``
     - True if the system architecture is x86, both 32-bit and 64-bit, for Intel or AMD chips.
   * - ``x86_64``
     - True if the system architecture is x86_64, which is 64-bit, for Intel or AMD chips.
   * - ``linux``
     - True if the platform is Linux.
   * - ``linux32``
     - True if the platform is Linux and the Python architecture is 32-bit.
   * - ``linux64``
     - True if the platform is Linux and the Python architecture is 64-bit.
   * - ``osx``
     - True if the platform is macOS.
   * - ``unix``
     - True if the platform is either macOS or Linux.
   * - ``win``
     - True if the platform is Windows.
   * - ``win32``
     - True if the platform is Windows and the Python architecture is 32-bit.
   * - ``win64``
     - True if the platform is Windows and the Python architecture is 64-bit.
   * - ``is_included``
     - True if the current file is processed because it was included by another file.


Using environment variables in the devenv file
----------------------------------------------

Environment variables that are defined when calling ``conda devenv`` can be read and checked with the
``get_env`` function:

.. code-block:: yaml

    dependencies:
      - python ={{ get_env("PY") }}

This will raise an error if ``PY`` is not defined. Alternatively, it is also possible to set a default value:

.. code-block:: yaml

    dependencies:
      - python ={{ get_env("PY", default="3.6") }}

You can also provide a list of allowed or supported values:

.. code-block:: yaml

    dependencies:
      - python ={{ get_env("PY", valid=["3.6", "3.7"]) }}

This will raise an error if ``PY`` is set to a different value.

.. note::

    Environment variables can also be set with the ``-e/--env-var`` command line option,
    see the `Command-line reference`_ section.


Checking minimum conda-devenv version
-------------------------------------

If your ``environment.devenv.yml`` files make use of features available only in later ``conda-devenv`` versions,
you can specify a minimum  version using the ``min_conda_devenv_version`` function at the top of your file:

.. code-block:: yaml

    {{ min_conda_devenv_version("1.1") }}
    name: web-ui


If users are using an old version, they will get then an error message indicating that they should update
their ``conda-devenv`` version.

It is recommended to use this setting to avoid confusing errors of users updating your software when new
``conda-devenv`` features are used.

.. note::

    Unfortunately this feature was added in ``conda-devenv 1.1``, so ``1.0`` users will get a more cryptic message
    about ``min_conda_devenv_version`` not being defined.


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
variables, using the appropriate separator for the platform (``:`` on Linux/OSX and ``;`` on Windows).

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
3. Generate ``devenv-activate{.sh,.bat}`` and ``devenv-deactivate{.sh,.bat}`` scripts in ``$PREFIX/etc/conda/activate.d``
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
                        [--print-full] [--no-prune] [--output-file [OUTPUT_FILE]]
                        [--quiet] [--env-var ENV_VAR] [--verbose] [--version]

    Work with multiple conda-environment-like yaml files in dev mode.

    optional arguments:
      -h, --help            show this help message and exit
      --file [FILE], -f [FILE]
                            The environment.devenv.yml file to process. The
                            default value is 'environment.devenv.yml'.
      --name [NAME], -n [NAME]
                            Name of environment.
      --print               Prints the rendered file as will be sent to conda-env
                            to stdout and exits.
      --print-full          Similar to --print, but also includes the
                            'environment' section.
      --no-prune            Don't pass --prune flag to conda-env.
      --output-file [OUTPUT_FILE]
                            Output filename.
      --quiet               Do not show progress
      --env-var ENV_VAR, -e ENV_VAR
                            Define or override environment variables in the form
                            VAR_NAME or VAR_NAME=VALUE.
      --verbose, -v         Use once for info, twice for debug, three times for
                            trace.
      --version             Show version and exit



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

``--env-var``
~~~~~~~~~~~~~~~~~

Define or override environment variables in the form ``VAR_NAME`` or ``VAR_NAME=VALUE``.
Can be used multiple times for different variables.
