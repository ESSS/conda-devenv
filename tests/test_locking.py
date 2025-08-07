import sys
from pathlib import Path
from textwrap import dedent
from typing import Literal

import pytest

from conda_devenv import devenv
from conda_devenv.devenv import CondaPlatform


@pytest.fixture(autouse=True)
def mock_which(mocker) -> None:
    mocker.patch("shutil.which", side_effect=lambda value: f"/path/to/{value}")


def test_create_and_update_lock_files(
    tmp_path: Path, mocker, monkeypatch, file_regression
) -> None:
    monkeypatch.chdir(tmp_path)

    base_env_file = tmp_path / "base.devenv.yml"
    base_env_file.write_text(
        dedent(
            """
            channels:
            - conda-forge
            platforms:
            - win-64
            - linux-64
            - osx-arm64
            dependencies:
            - pytest
            - wincom  # [win]
            - shmem  # [unix]
            - pip:
              - lupa
            """
        )
    )

    env_file = tmp_path / "environment.devenv.yml"
    env_file.write_text(
        dedent(
            """
            name: foo-py310
            includes:
            - {{ root }}/base.devenv.yml
            dependencies:
            - pytest
            - pywin32  # [win]
            - flock  # [unix]
            """
        )
    )

    # With --lock conda-devenv creates the .lock_environment.yml files and calls conda-lock
    # to solve them and generate the .conda-lock.yml files.
    subprocess_call_mock = mocker.patch(
        "subprocess.call", autospec=True, return_value=0
    )
    assert devenv.main(["--lock"]) == 0

    win_lock = tmp_path / ".foo-py310.win-64.lock_environment.yml"
    linux_lock = tmp_path / ".foo-py310.linux-64.lock_environment.yml"
    osx_arm64_lock = tmp_path / ".foo-py310.osx-arm64.lock_environment.yml"
    file_regression.check(
        win_lock.read_text(),
        basename="expected.win-64.lock_environment",
        extension=".yml",
    )
    file_regression.check(
        linux_lock.read_text(),
        basename="expected.linux-64.lock_environment",
        extension=".yml",
    )
    file_regression.check(
        linux_lock.read_text(),
        basename="expected.linux-64.lock_environment",
        extension=".yml",
    )
    file_regression.check(
        osx_arm64_lock.read_text(),
        basename="expected.osx-arm64.lock_environment",
        extension=".yml",
    )

    shell = sys.platform.startswith("win")
    expected_cmdline_win = [
        "conda",
        "lock",
        "--file",
        ".foo-py310.win-64.lock_environment.yml",
        "--platform",
        "win-64",
        "--lockfile",
        ".foo-py310.win-64.conda-lock.yml",
    ]
    expected_cmdline_linux = [
        "conda",
        "lock",
        "--file",
        ".foo-py310.linux-64.lock_environment.yml",
        "--platform",
        "linux-64",
        "--lockfile",
        ".foo-py310.linux-64.conda-lock.yml",
    ]
    expected_cmdline_osx_arm64 = [
        "conda",
        "lock",
        "--file",
        ".foo-py310.osx-arm64.lock_environment.yml",
        "--platform",
        "osx-arm64",
        "--lockfile",
        ".foo-py310.osx-arm64.conda-lock.yml",
    ]
    assert subprocess_call_mock.call_args_list == [
        mocker.call(
            expected_cmdline_win,
            shell=shell,
        ),
        mocker.call(
            expected_cmdline_linux,
            shell=shell,
        ),
        mocker.call(
            expected_cmdline_osx_arm64,
            shell=shell,
        ),
    ]

    # --update-locks calls conda-lock to update the .conda-lock.yml files.
    subprocess_call_mock.reset_mock()
    assert devenv.main(["--update-locks", "pytest", "--update-locks", "pywin32"]) == 0
    assert subprocess_call_mock.call_args_list == [
        mocker.call(
            [
                *expected_cmdline_win,
                "--update",
                "pytest",
                "--update",
                "pywin32",
            ],
            shell=shell,
        ),
        mocker.call(
            [
                *expected_cmdline_linux,
                "--update",
                "pytest",
                "--update",
                "pywin32",
            ],
            shell=shell,
        ),
        mocker.call(
            [
                *expected_cmdline_osx_arm64,
                "--update",
                "pytest",
                "--update",
                "pywin32",
            ],
            shell=shell,
        ),
    ]


def test_locking_requires_channels_key(
    tmp_path: Path, patch_conda_calls: None, capsys
) -> None:
    env_file = tmp_path / "environment.devenv.yml"
    env_file.write_text(
        dedent(
            """
            name: foo-py310
            platforms:
            - win-64
            - linux-64
            """
        )
    )

    assert devenv.main(["--lock", "-f", str(env_file)]) == 2
    out, err = capsys.readouterr()
    assert (
        "ERROR: Locking requires key 'channels' defined in the starting devenv.yml file"
        in err
    )
    assert out == ""


def test_locking_requires_platforms_key(
    tmp_path: Path, patch_conda_calls: None, capsys
) -> None:
    env_file = tmp_path / "environment.devenv.yml"
    env_file.write_text(
        dedent(
            """
            name: foo-py310
            channels:
            - conda-forge
            """
        )
    )

    assert devenv.main(["--lock", "-f", str(env_file)]) == 2
    out, err = capsys.readouterr()
    assert (
        "ERROR: Locking requires key 'platforms' defined in the starting devenv.yml file"
        in err
    )
    assert out == ""


def test_locking_requires_devenv_files(
    tmp_path: Path, patch_conda_calls: None, capsys
) -> None:
    env_file = tmp_path / "environment.yml"
    env_file.write_text(
        dedent(
            """
            name: foo-py310
            channels:
            - conda-forge
            platforms:
            - win-64
            """
        )
    )

    assert devenv.main(["--lock", "-f", str(env_file)]) == 2
    out, err = capsys.readouterr()
    assert "ERROR: Locking requires a .devenv.yml file" in err
    assert out == ""


def test_auto_use_lock_files(
    tmp_path: Path, mocker, monkeypatch, file_regression
) -> None:
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / "environment.devenv.yml"
    env_name = "foo"
    env_file.write_text(
        dedent(
            f"""
            name: {env_name}
            channels:
            - conda-forge
            platforms:
            - win-64
            - linux-64
            dependencies:
            - pytest
            """
        )
    )

    # Create the env directory because we need it to exist to create the activate/deactivate scripts.
    env_dir = tmp_path / "envs"
    env_dir.joinpath(f"{env_name}/conda-meta").mkdir(parents=True)
    env_dirs = [env_dir]
    mocker.patch.object(
        devenv, "_get_envs_dirs_from_conda", autospec=True, return_value=env_dirs
    )

    lock_file = tmp_path / f".{env_name}.{CondaPlatform.current().value}.conda-lock.yml"
    lock_file.touch()
    subprocess_call_mock = mocker.patch(
        "subprocess.call", autospec=True, return_value=0
    )
    assert devenv.main([]) == 0

    shell = sys.platform.startswith("win")
    assert subprocess_call_mock.call_args_list == [
        mocker.call(
            ["conda", "lock", "install", "--name", "foo", lock_file.name],
            shell=shell,
        ),
    ]

    # Use locks again but create an environment different from the one defined
    # in environment.devenv.yml.
    subprocess_call_mock.reset_mock()
    env_dir2 = tmp_path / "envs"
    env_dir2.joinpath(f"_env-ci/conda-meta").mkdir(parents=True)
    env_dirs.append(env_dir2)
    assert devenv.main(["-n", "_env-ci"]) == 0

    shell = sys.platform.startswith("win")
    assert subprocess_call_mock.call_args_list == [
        mocker.call(
            ["conda", "lock", "install", "--name", "_env-ci", lock_file.name],
            shell=shell,
        ),
    ]

    # Not using locks should call conda env update normally.
    subprocess_call_mock.reset_mock()
    assert devenv.main(["--use-locks=no"]) == 0
    assert subprocess_call_mock.call_args_list == [
        mocker.call(
            ["conda", "env", "update", "--file", "environment.yml", "--prune"],
            shell=shell,
        ),
    ]


@pytest.mark.parametrize("mode", ["cmd-line", "env-var"])
def test_use_locks_is_yes_but_no_lock_file(
    tmp_path: Path,
    monkeypatch,
    patch_conda_calls: None,
    capsys,
    mode: Literal["cmd-line", "env-var"],
) -> None:
    if mode == "cmd-line":
        cmdline = ["--use-locks=yes"]
    else:
        assert mode == "env-var"
        monkeypatch.setenv("CONDA_DEVENV_USE_LOCKS", "yes")
        cmdline = []
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / "environment.devenv.yml"
    env_file.write_text(
        dedent(
            f"""
                name: foo
                channels:
                - conda-forge
                platforms:
                - win-64
                - linux-64
                dependencies:
                - pytest
                """
        )
    )

    assert devenv.main(cmdline) == 2
    out, err = capsys.readouterr()
    platform = CondaPlatform.current().value
    assert (
        f"ERROR: lock file .foo.{platform}.conda-lock.yml not found and --use-locks=yes, aborting."
        in err
    )
    assert out == ""
