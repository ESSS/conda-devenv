=================
Release Procedure
=================

1. Open a PR updating the CHANGELOG with the latest fixes.
2. Once the PR is approved and green, `create a new release <https://github.com/ESSS/conda-devenv/releases/new>`__, using a version in the format ``X.Y.Z`` and targetting the release branch above.
3. Merge the PR -- **do not squash**, to preserve the commit with the release tag.

That's it. Now we wait for conda-forge to pick up the new version, or alternatively, `create an issue requesting a bot update <https://github.com/conda-forge/conda-devenv-feedstock/issues/new/choose>`__.
