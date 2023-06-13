import os
import platform
import sys
import textwrap
from pathlib import Path

import jinja2
import pytest

from conda_devenv.devenv import CondaPlatform
from conda_devenv.devenv import preprocess_selector_in_line
from conda_devenv.devenv import preprocess_selectors
from conda_devenv.devenv import render_jinja


def test_jinja_root() -> None:
    assert render_jinja(
        "{{root}}",
        filename=Path("path/to/file"),
        is_included=False,
    ) == os.path.abspath("path/to")


def test_jinja_os(monkeypatch) -> None:
    template = textwrap.dedent(
        """\
        {% if os.environ['ENV_VARIABLE'] == '1' -%}
        variable is set
        {%- else -%}
        variable is not set
        {%- endif %}
    """
    ).strip()

    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False)
        == "variable is not set"
    )

    monkeypatch.setenv("ENV_VARIABLE", "1")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False)
        == "variable is set"
    )

    monkeypatch.setenv("ENV_VARIABLE", "2")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False)
        == "variable is not set"
    )


def test_jinja_sys(monkeypatch) -> None:
    template = textwrap.dedent(
        """\
        {% if sys.platform.startswith('linux') -%}
        linux!
        {%- elif sys.platform.startswith('win') -%}
        windows!
        {%- else -%}
        others!
        {%- endif %}
    """
    ).strip()

    monkeypatch.setattr(sys, "platform", "linux")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "linux!"
    )

    monkeypatch.setattr(sys, "platform", "windows")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False)
        == "windows!"
    )

    monkeypatch.setattr(sys, "platform", "darwin")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "others!"
    )


def test_jinja_platform(monkeypatch) -> None:
    template = "{{ platform.python_revision() }}"
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False)
        == platform.python_revision()
    )


def test_jinja_aarch64(monkeypatch) -> None:
    template = "{{ aarch64 }}"

    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_arm64(monkeypatch) -> None:
    template = "{{ arm64 }}"

    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "win32")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_x86(monkeypatch) -> None:
    template = "{{ x86 }}"

    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_x86_64(monkeypatch) -> None:
    template = "{{ x86_64 }}"

    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"


def test_jinja_linux(monkeypatch) -> None:
    template = "{{ linux }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "win")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "darwin")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_linux32(monkeypatch) -> None:
    template = "{{ linux32 }}"

    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_linux64(monkeypatch) -> None:
    template = "{{ linux64 }}"

    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"


def test_jinja_osx(monkeypatch) -> None:
    template = "{{ osx }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "win")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"


def test_jinja_unix(monkeypatch) -> None:
    template = "{{ unix }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "win")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"


def test_jinja_win(monkeypatch) -> None:
    template = "{{ win }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(sys, "platform", "win")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_win32(monkeypatch) -> None:
    template = "{{ win32 }}"

    monkeypatch.setattr(sys, "platform", "win")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )


def test_jinja_win64(monkeypatch) -> None:
    template = "{{ win64 }}"

    monkeypatch.setattr(sys, "platform", "win")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert (
        render_jinja(template, filename=Path("foo.yml"), is_included=False) == "False"
    )

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "True"


def test_preprocess_selector_in_line() -> None:
    line = "  - ccache    # [linux or osx]"
    expected = f"{{% if linux or osx %}}{line}{{% endif %}}"
    assert preprocess_selector_in_line(line) == expected

    line = "  - clcache    # [ win ]"
    expected = f"{{% if win %}}{line}{{% endif %}}"
    assert preprocess_selector_in_line(line) == expected

    line = "  - boost"
    expected = line
    assert preprocess_selector_in_line(line) == expected

    line = "  - cmake  # cmake is a required dependency"
    expected = line
    assert preprocess_selector_in_line(line) == expected

    line = "  - cmake  # [linux] cmake is a required dependency in linux"
    expected = f"{{% if linux %}}{line}{{% endif %}}"
    assert preprocess_selector_in_line(line) == expected

    line = ""
    expected = line
    assert preprocess_selector_in_line(line) == expected


def test_preprocess_selectors() -> None:
    template = textwrap.dedent(
        """\
        name: lib
        dependencies:
          - cmake
          - ccache    # [unix]
          - clcache   # [win] Windows has clcache instead of ccache
    """
    ).strip()

    expected = textwrap.dedent(
        """\
        name: lib
        dependencies:
          - cmake
        {% if unix %}  - ccache    # [unix]{% endif %}
        {% if win %}  - clcache   # [win] Windows has clcache instead of ccache{% endif %}
    """
    ).strip()

    assert preprocess_selectors(template) == expected


@pytest.mark.parametrize("mode", ["patch-sys", "use-conda-platform"])
def test_render_jinja_with_preprocessing_selectors(monkeypatch, mode: str) -> None:
    template = textwrap.dedent(
        """\
        {% set name = 'mylib' %}
        name: {{ name }}
        dependencies:
          - cmake
          - ccache    # [unix]
          - clcache   # [win] Windows has clcache instead of ccache
        """
    ).strip()

    expected_unix = textwrap.dedent(
        """\
        name: mylib
        dependencies:
          - cmake
          - ccache    # [unix]
        """
    ).strip()

    expected_win = textwrap.dedent(
        """\
        name: mylib
        dependencies:
          - cmake

          - clcache   # [win] Windows has clcache instead of ccache
        """
    ).strip()

    def render_as_platform(platform: str, conda_platform: CondaPlatform | None) -> str:
        if mode == "patch-sys":
            monkeypatch.setattr(sys, "platform", platform)
            conda_platform = None
        else:
            assert mode == "use-conda-platform"
        return render_jinja(
            template,
            filename=Path("foo.yml"),
            is_included=False,
            conda_platform=conda_platform,
        ).strip()

    assert render_as_platform("linux", CondaPlatform.Linux64) == expected_unix
    assert render_as_platform("darwin", CondaPlatform.Osx64) == expected_unix
    assert render_as_platform("win32", CondaPlatform.Win64) == expected_win


def test_jinja_get_env(monkeypatch) -> None:
    template = "{{ get_env('PY', valid=['3.6']) }}"
    template_with_default = "{{ get_env('PY', default='3.6') }}"

    monkeypatch.setenv("PY", "3.6")
    assert render_jinja(template, filename=Path("foo.yml"), is_included=False) == "3.6"

    monkeypatch.setenv("PY", "3.7")
    with pytest.raises(ValueError):
        render_jinja(template, filename=Path("foo.yml"), is_included=False)

    monkeypatch.delenv("PY")
    with pytest.raises(ValueError):
        render_jinja(template, filename=Path("foo.yml"), is_included=False)

    monkeypatch.delenv("PY", raising=False)
    assert (
        render_jinja(template_with_default, filename=Path("foo.yml"), is_included=False)
        == "3.6"
    )


def test_jinja_invalid_template() -> None:
    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        render_jinja(
            textwrap.dedent(
                """\
                {%- if os.environ['ENV_VARIABLE'] == '1' %}
                {% %}
            """
            ),
            filename=Path("foo.yml"),
            is_included=False,
        )
