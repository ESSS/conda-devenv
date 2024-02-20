=========
CHANGELOG
=========

UNRELEASED
----------

- Dependency order is no longer sorted automatically, instead the order is preserved as they are defined in the ``*.devenv.yml`` files.
  Usually this would not matter, but it is important for ``pip`` dependencies which declare development installations, as it is important
  that those happen in the specified order.


3.2.1 (2024-01-03)
------------------

* Fixed handling of `constraints` when processing lock files and `dependencies` include a `pip` section.

3.2.0 (2023-07-11)
------------------

* The ``CONDA_DEVENV_USE_LOCKS`` can be used to change the default value of ``--use-locks``. Useful to set on CI to ensure
  lock files are being used.

3.1.1 (2023-07-04)
------------------

* Fixed bug where the platform selectors of included ``devenv.yml`` files were not being honored when rendering lock files.

3.1.0 (2023-06-30)
------------------

* Added support for version constraints in ``devenv.yml`` files. Consult the `docs <https://conda-devenv.readthedocs.io/en/latest/usage.html#constraints>`__.
* Improved message with ``--use-locks=yes`` and no lock files are found.
* Force flush calls when reporting progress updates, which improves seeing these updates on CI.

3.0.0 (2023-06-19)
------------------

* New workflow to work with lock files, using `conda-lock <https://github.com/conda/conda-lock>`__. Consult the `docs <https://conda-devenv.readthedocs.io/en/latest/usage.html#locking>`__.
* Added full type annotations. Some of the parameters were changed from ``str`` to ``Path`` to make the API more clearer.
* Python 3.7, 3.8, and 3.9 are no longer supported. Note that ``conda-devenv`` installed in a Python 3.10+ conda root
  can still be used to work with environments in those versions.
* Dropped an internal hack that attempted to circumvent bugs in conda's ``--prune`` implementation by truncating the install history file: we suspect this is no longer needed and might cause more harm than good.


2.4.0 (2023-03-29)
------------------

* Added ``aarch64`` and ``arm64`` selectors (`#166`_).
* Fixed bug when an empty ``environment:`` key is declared in the ``environment.devenv.yml``file (`#164`_).

.. _`#164`: https://github.com/ESSS/conda-devenv/pull/164
.. _`#166`: https://github.com/ESSS/conda-devenv/pull/166

2.3.0 (2022-03-07)
------------------

* Now it is possible to use `mamba`_ with ``conda-devenv`` (`#134`_):
  - Pass ``--env-manager`` in the command-line.
  - Set the ``CONDA_DEVENV_ENV_MANAGER=mamba`` environment variable.

.. _`mamba`: https://github.com/mamba-org/mamba

.. _`#134`: https://github.com/ESSS/conda-devenv/pull/134


2.2.0 (2022-01-31)
------------------

* Add support for mamba (`#110`_).

.. _`#110`: https://github.com/ESSS/conda-devenv/issues/110


2.1.1 (2020-08-13)
------------------

* Correctly handle editable installs when using pip dependencies (`#113`_).

.. _`#113`: https://github.com/ESSS/conda-devenv/issues/113


2.1.0 (2020-06-26)
------------------

* New ``get_env`` function to handle environment variables in Jinja contexts so it conveys
  better error messages in case of missing/invalid environment variables.


2.0.0 (2020-06-08)
------------------

* Drop support for Python 2.7, 3.4, and 3.5.
* Correctly parse relative includes without jinja root.
* New ``--verbose`` flag which is passed on to ``conda``.


1.1.3 (2019-12-26)
------------------

* Accept package version specifiers containing upper case letters  (`#95`_).

.. _`#95`: https://github.com/ESSS/conda-devenv/issues/95


1.1.2 (2019-05-07)
------------------

* Correctly support git and mercurial repositories in ``pip`` dependencies (`#92`_).

.. _`#92`: https://github.com/ESSS/conda-devenv/pull/92


1.1.1 (2019-03-22)
------------------

* Remove yaml load warnings by using ``yaml.safe_load`` instead of ``yaml.load``.

* Fix ``NoneType object is not iterable`` error when ``includes`` is empty.


1.1.0 (2019-02-14)
------------------

* New ``is_included`` jinja variable which is a boolean indicating if the current file was included by
  another ``devenv.yml`` file (``True``) or it is the original file passed to ``conda devenv`` (``False``) (`#72`_).

* Added shortcuts to common jinja 2 checks, for example ``win`` which is equal to ``sys.platform.startswith("win")`` (`#75`_).

* Added support conda-build-style YAML line comments (`` # [win]``) (`#79`_).

* New ``min_conda_devenv_version`` jinja2 function that can be used to specify a minimum conda-devenv version:

  .. code-block:: yaml

      {{ min_conda_devenv_version("1.1") }}
      name: my-environment

  This is recommended when using new features so users will be shown a descriptive error message instead of subtle failures (`#81`_).

.. _`#72`: https://github.com/ESSS/conda-devenv/pull/72
.. _`#75`: https://github.com/ESSS/conda-devenv/pull/75
.. _`#79`: https://github.com/ESSS/conda-devenv/pull/79
.. _`#81`: https://github.com/ESSS/conda-devenv/pull/81


1.0.4 (2018-09-20)
------------------


* Do not fail if history file does not exists (`#66`_).

* Obtain  ``envs_dir`` without using a subprocess (`#67`_).

.. _`#66`: https://github.com/ESSS/conda-devenv/issues/66
.. _`#67`: https://github.com/ESSS/conda-devenv/issues/67


1.0.3 (2018-06-20)
------------------

* Find correct env directory through ``envs_dir`` instead of matching first in ``envs``. This makes
  environment directory location more reliable in newer conda versions.


1.0.2 (2018-06-07)
------------------

* Fix problem with channel specification being wrongly exported (`#62`_).


.. _`#62`: https://github.com/ESSS/conda-devenv/issues/62


1.0.1 (2018-06-04)
------------------

* Truncate the environment's history file to have the old "prune" behavior when needed (`#59`_).


.. _`#59`: https://github.com/ESSS/conda-devenv/issues/59


1.0.0 (2017-09-19)
------------------

* Add --version flag (`#47`_).
* Provide a better error message when 'environment.devenv.yml' file is not found (`#48`_).
* Support for pip on dependencies section (`#55`_).


.. _`#47`: https://github.com/ESSS/conda-devenv/issues/53
.. _`#48`: https://github.com/ESSS/conda-devenv/issues/48
.. _`#55`: https://github.com/ESSS/conda-devenv/issues/55


0.9.6 (2017-07-24)
------------------

* Applies an "AND" when merging dependencies (`#53`_).
* On Mac generates the same scripts as for Linux (no longer ``.bat`` files).

.. _`#53`: https://github.com/ESSS/conda-devenv/issues/53


0.9.5 (2017-04-24)
------------------

* Handle ``None`` correctly, which actually fixes (`#49`_).


0.9.4 (2017-04-20)
------------------

* Fixed major bug where activate/deactivate scripts were not being generated (`#49`_).

.. _`#49`: https://github.com/ESSS/conda-devenv/issues/49


0.9.3 (2017-04-10)
------------------

* ``conda-devenv`` no longer requires ``conda`` to be on ``PATH`` to work (`#45`_).

.. _`#45`: https://github.com/ESSS/conda-devenv/issues/45


0.9.2 (2017-03-27)
------------------

* Fix conda-forge package.

0.9.1 (2017-03-22)
------------------

* Fix activate and deactivate ``bash`` scripts: variables not in the environment before activation
  are now properly unset after deactivation.

* Fix activate and deactivate ``bash`` scripts: quote variables when exporting them.


0.9.0 (2017-03-17)
------------------

* New option ``--print-full``, which also prints the expanded ``environment:`` section.

0.8.1 (2017-03-16)
------------------

* Fix entry point call to ``main``.


0.8.0 (2017-03-16)
------------------

* ``conda-devenv`` now can receive standard ``environment.yml`` files, in which case the file
  will just be forwarded to ``conda env update`` normally.
