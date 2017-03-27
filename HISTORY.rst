=======
History
=======

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
