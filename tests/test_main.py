from __future__ import annotations

import json
import shutil
import sys
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

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


@pytest.mark.parametrize(
    "input_name, write_scripts_call_count",
    [
        ("environment.devenv.yml", 1),
        ("environment.yml", 0),
    ],
)
@pytest.mark.parametrize("no_prune, truncate_call_count", [(True, 0), (False, 1)])
@pytest.mark.usefixtures("patch_conda_calls")
def test_handle_input_file(
    tmp_path,
    input_name,
    write_scripts_call_count,
    no_prune,
    truncate_call_count,
    monkeypatch,
) -> None:
    """
    Test how conda-devenv handles input files: devenv.yml and pure .yml files.
    """
    argv: list[str] = []

    def call_conda_mock(env_manager: str, args: Sequence[str]) -> int:
        argv[:] = list(args)
        return 0

    cast(MagicMock, devenv._call_conda).side_effect = call_conda_mock

    filename = tmp_path / input_name
    filename.write_text(
        textwrap.dedent(
            """\
        name: a
        dependencies:
          - a_dependency
    """
        )
    )
    devenv_cmdline_args = ["--file", str(filename), "--quiet"]
    expected_conda_cmdline_args = [
        "env",
        "update",
        "--file",
        str(tmp_path / "environment.yml"),
        "--prune",
        "--quiet",
    ]
    if no_prune:
        devenv_cmdline_args.append("--no-prune")
        expected_conda_cmdline_args.remove("--prune")

    assert devenv.main(devenv_cmdline_args) == 0
    assert cast(MagicMock, devenv._call_conda).call_count == 1
    assert argv == expected_conda_cmdline_args
    assert (
        cast(MagicMock, devenv.write_activate_deactivate_scripts).call_count
        == write_scripts_call_count
    )
    assert (
        cast(MagicMock, devenv.truncate_history_file).call_count == truncate_call_count
    )


@pytest.mark.parametrize("input_name", ["environment.devenv.yml", "environment.yml"])
@pytest.mark.usefixtures("patch_conda_calls")
def test_print(tmp_path: Path, input_name, capsys) -> None:
    """
    Test --print option for different types of inputs.
    """
    filename = tmp_path / input_name
    filename.write_text(
        textwrap.dedent(
            """\
        name: a
        dependencies:
          - a_dependency
          - channel::another_dependency ==3.14
    """
        )
    )
    assert devenv.main(["--file", str(filename), "--quiet", "--print"]) == 0
    out, err = capsys.readouterr()
    assert "dependencies:" in out
    assert "- a_dependency" in out
    assert "- channel::another_dependency ==3.14" in out
    assert "name: a" in out


@pytest.mark.usefixtures("patch_conda_calls")
def test_print_full(tmp_path: Path, capsys) -> None:
    """
    Test --print option for different types of inputs.
    """
    filename = tmp_path / "environment.devenv.yml"
    filename.write_text(
        textwrap.dedent(
            """\
        name: a
        dependencies:
          - a_dependency
          - channel::another_dependency ==3.14
        environment:
          PYTHONPATH: {{ root }}/source
    """
        )
    )
    assert devenv.main(["--file", str(filename), "--quiet", "--print-full"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert "dependencies:" in out
    assert "- a_dependency" in out
    assert "- channel::another_dependency ==3.14" in out
    assert "name: a" in out
    assert "environment:" in out
    assert "PYTHONPATH:" in out


def test_min_version_failure(tmp_path: Path, capsys, mocker) -> None:
    """
    Check the "min_conda_devenv_version()" fails with the expected message.
    """
    import conda_devenv

    filename = tmp_path / "environment.devenv.yml"
    filename.write_text(
        textwrap.dedent(
            """\
        {{ min_conda_devenv_version("999.9") }}
        name: a
    """
        )
    )
    mocker.patch("shutil.which", return_value="/path/to/conda")
    assert devenv.main(["--file", str(filename)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    msg = f"This file requires at minimum conda-devenv 999.9, but you have {conda_devenv.__version__} installed."
    assert msg in err


def test_no_name(tmp_path: Path, capsys, mocker) -> None:
    """
    Check the "min_conda_devenv_version()" fails with the expected message.
    """
    mocker.patch("shutil.which", return_value="/path/to/conda")
    filename = tmp_path / "environment.devenv.yml"
    filename.write_text("foo: something")
    mocker.patch("shutil.which", return_value="/path/to/conda")
    assert devenv.main(["--file", str(filename)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "ERROR: file environment.devenv.yml has no 'name' key defined." in err


def test_min_version_ok(tmp_path: Path, capsys, mocker) -> None:
    """
    Check the "min_conda_devenv_version()" does not fail with current version.
    """
    import conda_devenv

    mocker.patch("shutil.which", return_value="/path/to/conda")
    filename = tmp_path / "environment.devenv.yml"
    filename.write_text(
        textwrap.dedent(
            """\
        {{{{ min_conda_devenv_version("{}") }}}}
        name: a
    """.format(
                conda_devenv.__version__
            )
        )
    )
    assert devenv.main(["--file", str(filename), "--print-full"]) == 0


def test_version(capsys) -> None:
    """
    Test --version flag.
    """
    from conda_devenv import __version__ as version

    assert devenv.main(["--version"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert version in out


@pytest.mark.parametrize("explicit_file", [True, False])
def test_error_message_environment_file_not_found(
    capsys, tmp_path: Path, explicit_file, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    args = ["--file", "invalid.devenv.yml"] if explicit_file else []
    expected_name = "invalid.devenv.yml" if explicit_file else "environment.devenv.yml"
    assert devenv.main(args) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert f'file "{str(expected_name)}" does not exist.' in err


def test_get_env_directory(mocker, tmp_path: Path) -> None:
    env_0 = tmp_path / "0/envs/my_env"
    env_0.mkdir(parents=True)
    conda_meta_env_0 = tmp_path / "0/envs/my_env/invalid"
    conda_meta_env_0.mkdir(parents=True)

    env_1 = tmp_path / "1/envs/my_env"
    env_1.mkdir(parents=True)
    conda_meta_env_1 = tmp_path / "1/envs/my_env/conda-meta"
    conda_meta_env_1.mkdir(parents=True)

    conda_info_json = {
        "envs_dirs": [
            str(tmp_path / "0/envs"),
            str(tmp_path / "1/envs"),
        ]
    }
    check_output_mock = mocker.patch(
        "subprocess.check_output", return_value=json.dumps(conda_info_json)
    )

    obtained = devenv.get_env_directory("mamba", "my_env")
    assert obtained == Path(env_1)
    assert check_output_mock.call_args == mocker.call(
        ["mamba", "info", "--json"], text=True, shell=sys.platform.startswith("win")
    )

    shutil.rmtree(env_1)
    assert devenv.get_env_directory("mamba", "my_env") is None


@pytest.mark.usefixtures("patch_conda_calls")
def test_verbose(mocker, tmp_path) -> None:
    argv: list[str] = []

    def call_conda_mock(env_manager: str, args: Sequence[str]) -> int:
        argv[:] = list(args)
        return 0

    cast(MagicMock, devenv._call_conda).side_effect = call_conda_mock

    filename = tmp_path.joinpath("environment.yml")
    filename.write_text("name: a")
    devenv_cmdline_args = ["--file", str(filename), "-v", "--verbose"]
    expected_conda_cmdline_args = [
        "env",
        "update",
        "--file",
        str(filename),
        "--prune",
        "-vv",
    ]
    assert devenv.main(devenv_cmdline_args) == 0
    assert cast(MagicMock, devenv._call_conda).call_count == 1
    assert argv == expected_conda_cmdline_args


@pytest.mark.parametrize("option", ("-m", "--env-manager", "ENV_VAR"))
def test_unknown_env_manager_option(option, capsys, monkeypatch, tmp_path) -> None:
    env_manager = "foo"
    if option == "ENV_VAR":
        monkeypatch.setenv("CONDA_DEVENV_ENV_MANAGER", env_manager)
        env_manager_args = []
        config_source = "environment variable"
    else:
        monkeypatch.delenv("CONDA_DEVENV_ENV_MANAGER", raising=False)
        env_manager_args = [option, env_manager]
        config_source = "'--env-manager' ('-m') option"

    filename = tmp_path.joinpath("environment.yml")
    filename.write_text("name: a")
    devenv_cmdline_args = ["--file", str(filename)] + env_manager_args

    assert devenv.main(devenv_cmdline_args) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert (
        f'conda-devenv does not know the environment manager "foo" obtained from {config_source}.'
        in err.strip()
    )


@pytest.mark.usefixtures("patch_conda_calls")
@pytest.mark.parametrize("option", (None, "-m", "--env-manager"))
@pytest.mark.parametrize("env_manager", ("conda", "mamba"))
def test_env_manager_option(option, env_manager, mocker, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CONDA_DEVENV_ENV_MANAGER", raising=False)
    if option is None:
        env_manager_args = []
        if env_manager != "conda":
            pytest.skip("Without env-manager option use defaults to conda")
    else:
        env_manager_args = [option, env_manager]

    filename = tmp_path.joinpath("environment.yml")
    filename.write_text("name: a")
    devenv_cmdline_args = ["--file", str(filename)] + env_manager_args

    assert devenv.main(devenv_cmdline_args) == 0
    assert cast(MagicMock, devenv._call_conda).call_args == mocker.call(
        env_manager, ["env", "update", "--file", str(filename), "--prune"]
    )


def test_parse_env_var_args() -> None:
    """
    Test that env var args are parsed correctly.
    """
    assert devenv.parse_env_var_args(None) == {}
    assert devenv.parse_env_var_args(["DEV", "PY=3.6"]) == {"DEV": "", "PY": "3.6"}


@pytest.mark.usefixtures("patch_conda_calls")
def test_env_var_cmdline_args(tmp_path: Path) -> None:
    """
    Test env vars passed via -e/--env_var.
    """
    import os

    filename = tmp_path / "environment.devenv.yml"
    filename.write_text(
        textwrap.dedent(
            """\
        name: a
        dependencies:
          - python ={{ os.environ["PY"] }}
    """
        )
    )
    assert (
        devenv.main(
            ["--file", str(filename), "--quiet", "-e", "DEV", "--env-var", "PY=3.6"]
        )
        == 0
    )
    assert os.environ["DEV"] == ""
    assert os.environ["PY"] == "3.6"


@pytest.mark.usefixtures("patch_conda_calls")
def test_get_env(tmp_path: Path, monkeypatch) -> None:
    """
    Test get_env jinja function with required env var passed via command line.
    """
    filename = tmp_path / "environment.devenv.yml"
    filename.write_text(
        textwrap.dedent(
            """\
        name: a
        dependencies:
          - python ={{ get_env("PY", valid=["3.6"]) }}
    """
        )
    )
    monkeypatch.delenv("PY", raising=False)
    assert devenv.main(["--file", str(filename), "--quiet", "-e", "PY=3.6"]) == 0
