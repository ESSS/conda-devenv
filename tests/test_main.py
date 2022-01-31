import sys
import textwrap
from copy import deepcopy

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


@pytest.mark.parametrize(
    "input_name, write_scripts_call_count",
    [
        ("environment.devenv.yml", 1),
        ("environment.yml", 0),
    ],
)
@pytest.mark.parametrize("return_none", [True, False])
@pytest.mark.parametrize("no_prune, truncate_call_count", [(True, 0), (False, 1)])
@pytest.mark.usefixtures("patch_conda_calls")
@pytest.mark.parametrize("env_manager", ["conda", "mamba"])
def test_handle_input_file(
    tmpdir,
    input_name,
    write_scripts_call_count,
    return_none,
    no_prune,
    truncate_call_count,
    env_manager,
    monkeypatch,
):
    """
    Test how conda-devenv handles input files: devenv.yml and pure .yml files.
    """
    argv = []

    def call_conda_mock(env_manager):
        argv[:] = sys.argv[:]
        # conda's env main() function sometimes returns None and other times raises SystemExit
        if return_none:
            return None
        else:
            sys.exit(0)

    devenv._call_conda.side_effect = call_conda_mock

    filename = tmpdir.join(input_name)
    filename.write(
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
        tmpdir.join("environment.yml"),
        "--prune",
        "--quiet",
    ]
    if env_manager == "mamba":
        expected_conda_cmdline_args = [env_manager] + expected_conda_cmdline_args
        mock_argv = deepcopy(sys.argv)
        mock_argv[0] = env_manager
        monkeypatch.setattr("sys.argv", mock_argv)
    if no_prune:
        devenv_cmdline_args.append("--no-prune")
        expected_conda_cmdline_args.remove("--prune")

    assert devenv.main(devenv_cmdline_args) == 0
    assert devenv._call_conda.call_count == 1
    assert argv == expected_conda_cmdline_args
    assert (
        devenv.write_activate_deactivate_scripts.call_count == write_scripts_call_count
    )
    assert devenv.truncate_history_file.call_count == truncate_call_count


@pytest.mark.parametrize("input_name", ["environment.devenv.yml", "environment.yml"])
@pytest.mark.usefixtures("patch_conda_calls")
def test_print(tmpdir, input_name, capsys):
    """
    Test --print option for different types of inputs.
    """
    filename = tmpdir.join(input_name)
    filename.write(
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
def test_print_full(tmpdir, capsys):
    """
    Test --print option for different types of inputs.
    """
    filename = tmpdir.join("environment.devenv.yml")
    filename.write(
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


def test_min_version_failure(tmpdir, capsys):
    """
    Check the "min_conda_devenv_version()" fails with the expected message.
    """
    import conda_devenv

    filename = tmpdir.join("environment.devenv.yml")
    filename.write(
        textwrap.dedent(
            """\
        {{ min_conda_devenv_version("999.9") }}
        name: a
    """
        )
    )
    with pytest.raises(SystemExit) as e:
        devenv.main(["--file", str(filename)])
    assert e.value.code == 1
    out, err = capsys.readouterr()
    assert out == ""
    msg = "This file requires at minimum conda-devenv 999.9, but you have {ver} installed."
    assert msg.format(ver=conda_devenv.__version__) in err


def test_min_version_ok(tmpdir, capsys):
    """
    Check the "min_conda_devenv_version()" does not fail with current version.
    """
    import conda_devenv

    filename = tmpdir.join("environment.devenv.yml")
    filename.write(
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


def test_version(capsys):
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
    capsys, tmpdir, explicit_file, monkeypatch
):
    monkeypatch.chdir(str(tmpdir))
    args = ["--file", "invalid.devenv.yml"] if explicit_file else []
    expected_name = "invalid.devenv.yml" if explicit_file else "environment.devenv.yml"
    assert devenv.main(args) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == 'File "{}" does not exist.\n'.format(str(tmpdir / expected_name))


def test_get_env_directory(mocker, tmpdir):
    import os

    env_0 = tmpdir.join("0/envs/my_env").ensure(dir=1)
    conda_meta_env_0 = tmpdir.join("0/envs/my_env/conta-meta").ensure(dir=1)

    env_1 = tmpdir.join("1/envs/my_env").ensure(dir=1)
    conda_meta_env_1 = tmpdir.join("1/envs/my_env/conda-meta").ensure(dir=1)

    mocker.patch("subprocess.check_output", side_effect=AssertionError())
    mocker.patch.object(
        devenv,
        "_get_envs_dirs_from_conda",
        return_value=[
            str(tmpdir.join("0/envs")),
            str(tmpdir.join("1/envs")),
        ],
    )

    obtained = devenv.get_env_directory("my_env")
    assert obtained == str(env_1)

    env_1.remove()
    assert devenv.get_env_directory("my_env") is None


@pytest.mark.usefixtures("patch_conda_calls")
def test_verbose(mocker, tmp_path):
    argv = []

    def call_conda_mock(env_manager=""):
        argv[:] = sys.argv[:]
        return None

    devenv._call_conda.side_effect = call_conda_mock

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
    assert devenv._call_conda.call_count == 1
    assert argv == expected_conda_cmdline_args


def test_parse_env_var_args():
    """
    Test that env var args are parsed correctly.
    """
    assert devenv.parse_env_var_args(None) == {}
    assert devenv.parse_env_var_args(["DEV", "PY=3.6"]) == {"DEV": "", "PY": "3.6"}


@pytest.mark.usefixtures("patch_conda_calls")
def test_env_var_cmdline_args(tmpdir):
    """
    Test env vars passed via -e/--env_var.
    """
    import os

    filename = tmpdir.join("environment.devenv.yml")
    filename.write(
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
def test_get_env(tmpdir, monkeypatch):
    """
    Test get_env jinja function with required env var passed via command line.
    """
    filename = tmpdir.join("environment.devenv.yml")
    filename.write(
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
