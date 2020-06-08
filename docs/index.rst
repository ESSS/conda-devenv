Welcome to conda-devenv's documentation!
========================================

Overview
--------

With ``conda-devenv``, we help you manage software dependencies across Linux, Windows, and macOS
operating systems using a *single conda dependency file* ``environment.devenv.yml``
instead of multiple ``environment.yml`` files.

See example below:

.. code-block:: yaml

    name: mylib

    dependencies:
      - cmake
      - eigen
      - pip:
        - sphinx
      - gxx_linux-64=7.3.0  # [linux]
      - ccache              # [unix]
      - clcache             # [win]

    environment:
      CPATH:
        - $CONDA_PREFIX/include           # [unix]
        - $CONDA_PREFIX/Library/include   # [win]

      LD_LIBRARY_PATH: $CONDA_PREFIX/lib  # [unix]

By executing:

.. code::

    conda devenv

in the root of the project directory, an ``environment.yml`` file is produced.
We can now activate the conda environment ``mylib`` as follows:

.. code::

    conda activate mylib

This will not only resolve the dependencies for the current operating system,
but also set environment variables ``CPATH`` and ``LD_LIBRARY_PATH`` to the
list of paths specified in the ``environment.devenv.yml`` file. Note, however,
that ``LD_LIBRARY_PATH`` will only be set in Linux and macOS (Unix) whereas
``CPATH`` will be set differently in Linux and macOS compared to Windows.

Continue reading to learn more about the full capabilities of ``conda-devenv``!


Contents:
---------

.. toctree::
   :maxdepth: 2

   readme
   installation
   usage
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
