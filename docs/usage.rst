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
  This is heavly inspired by `conda-build's preprocessing selectors <https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#preprocessing-selectors>`_.

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
   * - ``aarch64``
     - True if the platform is Linux on ARMv8 and the Python architecture is 64-bit.
   * - ``arm64``
     - True if the platform is macOS with Apple Silicon and the Python architecture is 64-bit.
   * - ``is_included``
     - True if the current file is processed because it was included by another file.


Using environment variables in the devenv file
----------------------------------------------

Environment variables that are defined when calling ``conda devenv`` can be read normally using ``os.environ``, but for convenience and better error messages, you can use the
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
environment variables with the values found in the ``.devenv.yml`` file, using the appropriate separator for the platform (``:`` on Linux/OSX and ``;`` on Windows).

Environment variables defined as a single string (like ``DB_LOCATION`` above) will **overwrite** an existing
environment variable with the value from the ``.devenv.yml`` file.

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
      DB_LOCATION: https://localhost/dev  # [not is_included]


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
      DB_LOCATION: https://localhost/dev

In this setup, all the user has to do is executing ``conda devenv``:

.. code-block:: console

    $ cd ~/projects/web-ui
    $ conda devenv

This will create a ``conda`` environment named ``web-ui`` merging all the dependencies and environment variables
defined in both files.

However, the same environment variable defined as a single string (like ``DB_LOCATION`` above) in both files will raise an error
unless it is not allowed to 'pass through' using the ``# [not is_included]`` selector above as an example.
In other words, an 'overwrite' situation is not allowed between files.

Constraints
===========

.. versionadded:: 3.1

In dependent repositories, it is common that a core/base repository only works with some specific versions of a
library, for example:

* A repository of common utilities contains tasks that only work with ``vtk >9`` or ``alive-progress <2``.
* Some framework code requires a specific version of another library, for example ``qt =5.12`` or ``pytest >7``.

The problem here is that those repositories do not really depend on those packages, because they
are actually *optional* -- for example, one can use the common repository but not depend on ``vtk``.
For this reason the common repository cannot declare the dependency directly, otherwise all
downstream ``devenv.yml`` files will inherit that dependency.

`Conda <https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#run-constrained>`__
and `pip <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`__ have the concept of *constraints*,
which are package version restrictions that do not cause a package to be included in the environment directly,
but if they are included in the environment by other means, then their version specifiers must be respected.

Constraints are optional and can be declared in the ``constraints`` key:

.. code-block:: yaml

    name: common-utils
    dependencies:
    - boltons
    - attrs
    constraints:
    - pytest >7

Running ``conda devenv`` in this file will install ``['boltons', 'attrs']``, but not ``pytest``.

Consider this downstream ``devenv.yml`` file:

.. code-block:: yaml

    name: app
    includes:
    - {{ root }}/../common-utils/environment.devenv.yml
    dependencies:
    - pyqt

This file includes ``common-utils/environment.devenv.yml``, and even thought ``common-utils/environment.devenv.yml``
has a ``pytest >7`` constraint, because ``app/environment.devenv.yml`` does not declare ``pytest`` as a
direct dependency, running ``conda devenv`` will install only ``['boltons', 'attrs', 'pyqt']``.

Consider another downstream ``devenv.yml`` file:

.. code-block:: yaml

    name: app2
    includes:
    - {{ root }}/../common-utils/environment.devenv.yml
    dependencies:
    - pyqt
    - pytest

In this case, ``pytest`` is directly declared, so the constraint will be respected and
``['boltons', 'attrs', 'pyqt', 'pytest >7']`` will be installed.

.. note::

    A known limitation is that the constraints will only be respected if a package is explicitly declared,
    so it will not work for *transitive dependencies*.

    For example, a constraint of ``pytest >7`` will only be respected if somebody includes ``pytest``
    as a direct dependency. If ``pytest`` is only included indirectly, for example via ``pytest-xdist``,
    then the constraint will not be honored.

    Support for this is currently out of scope for ``conda-devenv``, as it would need to solve
    the environment in order to realize all the actual packages that will be installed.

Locking
=======

.. versionadded:: 3.0

Lock files can be used to generate fully reproducible environments.

Locking support was designed to be non-intrusive and used seamlessly with the rest of ``conda-devenv`` features,
being built on the top of the excellent `conda-lock`_ tool.

`conda-lock`_ must be installed to use the locking features.

File changes
------------

Locking supports all the features normal ``.devenv.yml`` files support, except it requires two new keys:

* ``channels``: a list of valid channels for packages. These override the global configuration. If you are using
  private channels whose URL include authentication information, make sure to use them as environment variables
  (see `Authenticated channels <https://conda.github.io/conda-lock/authenticated_channels>`__).
* ``platforms``: a list of platforms to generate lock files for.
  Because of Jinja2, different platforms might have different lock files, and this list will control
  which lock files will be generated.

  The supported platforms are:

  * ``win-32``
  * ``win-64``
  * ``linux-32``
  * ``linux-64``
  * ``osx-32``
  * ``osx-64``

Example of a file that can be used with locking.

.. code-block:: yaml

    name: core
    channels:
      - https://host.tld/t/$QUETZ_API_KEY/channel_name
      - conda-forge
    platforms:
      - win-64
      - linux-64
    dependencies:
      - numpy
      - pandas
      - pytest
      - pywin32  # [win]
      - flock  # [unix]
      - invoke
    environment:
      PYTHONPATH:
        - {{ root }}/source/python


Generating
----------

To start using locks:

.. code-block:: console

    $ conda devenv --lock

This will generate one lock file for each platform defined in ``platforms``:

::

    .core.linux-64.conda-lock.yml
    .core.win-64.conda-lock.yml


The ``core`` part of the name comes from the ``name`` definition. These files should be
committed to version control.

This command will also generate other ``*.lock_environment.yml`` in the same directory,
however those are not supposed to be committed to version control
and should be ignored.

Using
-----

With lock files in the current directory, the usual ``conda-devenv`` command will automatically use them:

.. code-block:: console

    $ conda devenv

No other changes are required.

You can control if ``devenv`` should use lock files using the ``--use-locks {auto,yes,no}`` command-line option.

Updating
--------

If you add or remove dependencies, or change version requirements, you can update the locks with:

.. code-block:: console

    $ conda devenv --lock

This will attempt to keep the existing pins as much as possible.

To update to the latest version of one or more libraries, for all platforms:

.. code-block:: console

    $ conda devenv --update-locks pytest --update-locks boltons

If you want to update all libraries to the latest version, pass an ``""`` (empty) value:

.. code-block:: console

    $ conda devenv --update-locks ""


.. note::

    Currently the following selectors likely will not work properly when
    used to generate lock files for multiple platforms:

    * ``aarch64``
    * ``arm64``
    * ``x86``
    * ``x86_64``

    The reason for that is that this information is not encoded in the
    conda platform convention (``win-64``, ``linux-64``, etc).

    There is no known workaround for this at the moment.

.. _conda-lock: https://github.com/conda/conda-lock

Command-line reference
======================

Default options
---------------

- ``conda-devenv`` creates a file name ``environment.yml`` at the same directory of the ``environment.devenv.yml`` file.

Options
-------

.. To generate the output below, set COLUMNS=80 before calling `conda devenv --help`.

.. code-block:: console

    $ conda devenv --help
    usage: devenv [-h] [--file [FILE]] [--name [NAME]] [--print] [--print-full]
                  [--no-prune] [--output-file [OUTPUT_FILE]] [--quiet]
                  [--env-var ENV_VAR] [--verbose] [--version]
                  [--env-manager ENV_MANAGER] [--lock] [--use-locks {auto,yes,no}]
                  [--update-locks PACKAGE]

    Work with multiple conda-environment-like yaml files in dev mode.

    options:
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
      --env-manager ENV_MANAGER, -m ENV_MANAGER
                            The environment manager to use. Default to 'conda' or
                            the value of 'CONDA_DEVENV_ENV_MANAGER' environment
                            variable if set.

    Locking:
      Options related to creating and using lockfiles. Requires conda-lock
      installed.

      --lock                Create one or more lock files for the
                            environment.devenv.yml file, or other file given by '
                            --file'.
      --use-locks {auto,yes,no}
                            How to use lock files: 'auto' will use them if
                            available, 'yes' will try to use and fail if not
                            available, 'no' skip lockfiles always.
      --update-locks PACKAGE
                            Update the given package in all lock files, while
                            still obeying the pins in the devenv.yml file. Can be
                            passed multiple times. Pass '' (empty) to update all
                            packages.



How it works
============

Here's how ``conda-devenv`` works behind the scenes:

1. Generate an ``environment.yml`` file in the same directory as the ``environment.devenv.yml`` file. The generated
   ``environment.yml`` should **not** be added to VCS.
2. Call ``conda env update --prune --file environment.yml``.
3. Generate ``devenv-activate{.sh,.bat}`` and ``devenv-deactivate{.sh,.bat}`` scripts in ``$PREFIX/etc/conda/activate.d``
   and ``$PREFIX/etc/conda/deactivate.d`` respectively which will set/unset the environment variables.
