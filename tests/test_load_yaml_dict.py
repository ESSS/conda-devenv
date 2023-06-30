import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from conda_devenv.devenv import load_yaml_dict
from conda_devenv.devenv import process_constraints_into_dependencies


def test_load_yaml_dict(datadir) -> None:
    conda_yaml_dict = load_yaml_dict(datadir / "c.yml")
    environment = conda_yaml_dict["environment"]
    assert set(environment.keys()) == {"PATH"}
    assert set(environment["PATH"]) == {"b_path", "a_path"}


def test_load_yaml_dict_with_wrong_definition_at_environment_key(datadir) -> None:
    filename = datadir / "a_wrong_definition_at_environment.yml"
    with pytest.raises(ValueError) as e:
        load_yaml_dict(filename)

    exception_message_start = (
        "The 'environment' key is supposed to be a dictionary, but you have the type "
        "'<class 'list'>' at "
    )
    assert exception_message_start in str(e.value)


def test_load_yaml_dict_empty_environment_key(datadir) -> None:
    filename = datadir / "empty_environment.yml"
    d = load_yaml_dict(filename)
    assert d == {"name": "foo", "environment": {}}


def test_load_yaml_dict_with_wrong_definition_at_environment_key_will_add_wrong_file_to_exception_message(
    datadir,
):
    with pytest.raises(ValueError) as e:
        load_yaml_dict(datadir / "b_includes_wrong_definition_at_environment.yml")

    exception_message_start = (
        "The 'environment' key is supposed to be a dictionary, but you have the type "
        "'<class 'list'>' at "
    )

    assert exception_message_start in str(e.value)
    assert "a_wrong_definition_at_environment.yml" in str(e.value)


@pytest.mark.parametrize("cmd_line_name", [True, False])
def test_get_env_name(mocker, tmpdir, cmd_line_name) -> None:
    import textwrap

    filename = tmpdir.join("env.yml")
    filename.write(
        textwrap.dedent(
            """\
        name: bar
        dependencies:
          - a_dependency
    """
        )
    )

    args = mocker.Mock()
    if cmd_line_name:
        args.name = "foo"
    else:
        args.name = None

    from conda_devenv.devenv import get_env_name

    name = get_env_name(args, yaml.safe_load(filename.read()))
    if cmd_line_name:
        assert name == "foo"
    else:
        assert name == "bar"


def test_is_included_var(datadir) -> None:
    a_env_file = datadir / "a.devenv.yml"
    a_env_file.write_text(
        textwrap.dedent(
            """
            name: a
            includes:
              - {{root}}/b.devenv.yml
            environment:
              VARIABLE: value_a
              IS_A_INCLUDED: {{is_included}}
            """
        )
    )
    b_env_file = datadir / "b.devenv.yml"
    b_env_file.write_text(
        textwrap.dedent(
            """
            name: b
            environment:
              {% if not is_included %}
              VARIABLE: value_b
              {% endif %}
              IS_B_INCLUDED: {{is_included}}
            """
        )
    )

    conda_env = load_yaml_dict(a_env_file)
    assert conda_env == {
        "name": "a",
        "environment": {
            "IS_A_INCLUDED": False,
            "IS_B_INCLUDED": True,
            "VARIABLE": "value_a",
        },
    }


def test_downstream_overrides_channels(tmp_path) -> None:
    a_fn = tmp_path / "a.devenv.yml"
    a_fn.write_text(
        textwrap.dedent(
            """
            name: a
            channels:
            - a_channel
            """
        )
    )

    b_fn = tmp_path / "b.devenv.yml"
    b_fn.write_text(
        textwrap.dedent(
            """
            name: b
            includes:
              - {{ root }}/a.devenv.yml
            channels:
            - b1_channel
            - b2_channel
            """
        )
    )

    assert load_yaml_dict(b_fn) == {
        "name": "b",
        "channels": ["b1_channel", "b2_channel"],
        "environment": {},
    }


def test_downstream_overrides_platforms(tmp_path) -> None:
    a_fn = tmp_path / "a.devenv.yml"
    a_fn.write_text(
        textwrap.dedent(
            """
            name: a
            platforms:
            - linux-64
            - win-64
            """
        )
    )

    b_fn = tmp_path / "b.devenv.yml"
    b_fn.write_text(
        textwrap.dedent(
            """
            name: b
            includes:
              - {{ root }}/a.devenv.yml
            platforms:
            - win-64
            - osx-64
            """
        )
    )

    assert load_yaml_dict(b_fn) == {
        "name": "b",
        "platforms": ["win-64", "osx-64"],
        "environment": {},
    }


class TestConstraints:
    def test_no_constraints(self) -> None:
        data = {"dependencies": ["attrs >19", "boltons"]}
        process_constraints_into_dependencies(data)
        assert data == {"dependencies": ["attrs >19", "boltons"]}

        data = {
            "dependencies": ["attrs >19", "boltons"],
            "constraints": [],
        }
        process_constraints_into_dependencies(data)
        assert data == {
            "dependencies": ["attrs >19", "boltons"],
            "constraints": [],
        }

        data2 = {
            "dependencies": ["attrs >19", "boltons"],
            "constraints": None,
        }
        process_constraints_into_dependencies(data2)
        assert data2 == {
            "dependencies": ["attrs >19", "boltons"],
            "constraints": None,
        }

        data3: dict[str, Any] = {
            "dependencies": [],
            "constraints": None,
        }
        process_constraints_into_dependencies(data3)
        assert data3 == {
            "dependencies": [],
            "constraints": None,
        }

    def test_constraints_not_used(self) -> None:
        """
        We have a constraints section, but the constrained packages
        are not directly declared as dependency.
        """
        data = {
            "dependencies": ["attrs >19", "boltons"],
            "constraints": ["pytest"],
        }
        process_constraints_into_dependencies(data)
        assert data["dependencies"] == ["attrs >19", "boltons"]

    def test_constraints_respected(self) -> None:
        """
        Constraints are declared as dependency if they are explicitly declared.
        """
        data = {
            "dependencies": ["attrs >19", "boltons", "pytest>=6"],
            "constraints": ["pytest >7", "attrs >=20", "requests <2"],
        }
        process_constraints_into_dependencies(data)
        assert data["dependencies"] == [
            "attrs >19",
            "boltons",
            "pytest>=6",
            "pytest >7",
            "attrs >=20",
        ]

    def test_integration(self, tmp_path: Path) -> None:
        utils_fn = tmp_path / "common-utils.devenv.yml"
        utils_fn.write_text(
            textwrap.dedent(
                """
                name: common-utils
                dependencies:
                - attrs >19
                constraints:
                - pytest >7
                - ftputil >3
                """
            )
        )

        core_fn = tmp_path / "common-core.devenv.yml"
        core_fn.write_text(
            textwrap.dedent(
                """
                name: common-core
                includes:
                - {{ root }}/common-utils.devenv.yml
                dependencies:
                - boltons
                constraints:
                - requests >2
                - diff-cover >4
                """
            )
        )

        app_fn = tmp_path / "app.devenv.yml"
        app_fn.write_text(
            textwrap.dedent(
                """
                name: app
                includes:
                - {{ root }}/common-core.devenv.yml
                dependencies:
                - pyqt
                - requests
                - pytest >=6.2
                """
            )
        )

        assert load_yaml_dict(app_fn) == {
            "name": "app",
            "dependencies": [
                "attrs >19",
                "boltons",
                "pyqt",
                "pytest >=6.2,>7",
                "requests >2",
            ],
            "environment": {},
        }
