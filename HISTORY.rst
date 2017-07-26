=======
History
=======

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
