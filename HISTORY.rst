=======
History
=======

1.0.3 (2018-06-20)
------------------

* Find correct env directory through 'envs_dir' instead of matching first in 'envs'


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
