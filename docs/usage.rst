=====
Usage
=====

To use conda-devenv::

    conda devenv

In a directory containing a ``environment.devenv.yml`` file.

This will execute the following:

1. Generate an ``environment.yml`` file.
2. Call ``conda env update --prune --file environment.yml``

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

