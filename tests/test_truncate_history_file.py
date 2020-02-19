from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from conda_devenv import devenv
from conda_devenv.devenv import ensure_history


@pytest.fixture
def patch_regenerate_history(mocker):
    """
    Patches all necessary functions so that we can do integration testing without actually calling
    conda.
    """
    mocker.patch.object(devenv, "regenerate_history", autospec=True)


def test_ensure_history_does_not_touch_history_if_it_contains_anything(
    patch_regenerate_history, tmpdir
):
    conda_meta_dir = tmpdir.join("conda-meta")
    conda_meta_dir.ensure(dir=True)  # Just meta folder no history.
    history = conda_meta_dir.join("history")
    history.ensure()

    with history.open("w") as h:
        print("anything", file=h)

    ensure_history(str(tmpdir))

    assert devenv.regenerate_history.call_count == 0


def test_ensure_history_file_regenerates_truncated_history(
    patch_regenerate_history, tmpdir
):
    conda_meta_dir = tmpdir.join("conda-meta")
    conda_meta_dir.ensure(dir=True)  # Just meta folder no history.
    history = conda_meta_dir.join("history")
    history.ensure()

    ensure_history(str(tmpdir))

    assert devenv.regenerate_history.call_count == 1


def test_ensure_history_file_does_not_ignore_missing(patch_regenerate_history, tmpdir):
    conda_meta_dir = tmpdir.join("conda-meta")
    conda_meta_dir.ensure(dir=True)  # Just meta folder no history.

    ensure_history(str(tmpdir))

    assert devenv.regenerate_history.call_count == 1
