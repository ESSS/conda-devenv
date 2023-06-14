import pytest

from conda_devenv import devenv


@pytest.fixture
def patch_conda_calls(mocker):
    """
    Patches all necessary functions so that we can do integration testing without actually calling
    conda.
    """
    mocker.patch.object(devenv, "get_env_directory", autospec=True)
    mocker.patch.object(devenv, "truncate_history_file", autospec=True)
    mocker.patch.object(devenv, "_call_conda", autospec=True, return_value=0)
    mocker.patch.object(devenv, "write_activate_deactivate_scripts", autospec=True)
    mocker.patch("shutil.which", return_value=f"path/to/conda")
