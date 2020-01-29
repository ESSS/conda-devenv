import os
import textwrap

import jinja2
import platform
import pytest
import sys

from conda_devenv.devenv import preprocess_selector_in_line
from conda_devenv.devenv import preprocess_selectors
from conda_devenv.devenv import render_jinja


def test_jinja_root():
    assert render_jinja(
        "{{root}}", filename="path/to/file", is_included=False,
    ) == os.path.abspath("path/to")


def test_jinja_os(monkeypatch):
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
        render_jinja(template, filename="", is_included=False) == "variable is not set"
    )

    monkeypatch.setenv("ENV_VARIABLE", "1")
    assert render_jinja(template, filename="", is_included=False) == "variable is set"

    monkeypatch.setenv("ENV_VARIABLE", "2")
    assert (
        render_jinja(template, filename="", is_included=False) == "variable is not set"
    )


def test_jinja_sys(monkeypatch):
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
    assert render_jinja(template, filename="", is_included=False) == "linux!"

    monkeypatch.setattr(sys, "platform", "windows")
    assert render_jinja(template, filename="", is_included=False) == "windows!"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename="", is_included=False) == "others!"


def test_jinja_platform(monkeypatch):
    template = "{{ platform.python_revision() }}"
    assert (
        render_jinja(template, filename="", is_included=False)
        == platform.python_revision()
    )


def test_jinja_x86(monkeypatch):
    template = "{{ x86 }}"

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert render_jinja(template, filename="", is_included=False) == "False"


def test_jinja_x86_64(monkeypatch):
    template = "{{ x86_64 }}"

    monkeypatch.setattr(platform, "machine", lambda: "x86")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    assert render_jinja(template, filename="", is_included=False) == "True"


def test_jinja_linux(monkeypatch):
    template = "{{ linux }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "win")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename="", is_included=False) == "False"


def test_jinja_linux32(monkeypatch):
    template = "{{ linux32 }}"

    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "False"


def test_jinja_linux64(monkeypatch):
    template = "{{ linux64 }}"

    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "True"


def test_jinja_osx(monkeypatch):
    template = "{{ osx }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(sys, "platform", "win")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename="", is_included=False) == "True"


def test_jinja_unix(monkeypatch):
    template = "{{ unix }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "win")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename="", is_included=False) == "True"


def test_jinja_win(monkeypatch):
    template = "{{ win }}"

    monkeypatch.setattr(sys, "platform", "linux")
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(sys, "platform", "win")
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(sys, "platform", "darwin")
    assert render_jinja(template, filename="", is_included=False) == "False"


def test_jinja_win32(monkeypatch):
    template = "{{ win32 }}"

    monkeypatch.setattr(sys, "platform", "win")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "True"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "False"


def test_jinja_win64(monkeypatch):
    template = "{{ win64 }}"

    monkeypatch.setattr(sys, "platform", "win")

    monkeypatch.setattr(platform, "architecture", lambda: ("32bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "False"

    monkeypatch.setattr(platform, "architecture", lambda: ("64bit", ""))
    assert render_jinja(template, filename="", is_included=False) == "True"


def test_preprocess_selector_in_line():
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


def test_preprocess_selectors():
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


def test_render_jinja_with_preprocessing_selectors(monkeypatch):
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

    monkeypatch.setattr(sys, "platform", "linux")
    actual_linux = render_jinja(template, filename="", is_included=False).strip()

    monkeypatch.setattr(sys, "platform", "darwin")
    actual_osx = render_jinja(template, filename="", is_included=False).strip()

    monkeypatch.setattr(sys, "platform", "win")
    actual_win = render_jinja(template, filename="", is_included=False).strip()

    assert actual_linux == expected_unix
    assert actual_osx == expected_unix
    assert actual_win == expected_win


def test_jinja_invalid_template():
    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        render_jinja(
            textwrap.dedent(
                """\
                {%- if os.environ['ENV_VARIABLE'] == '1' %}
                {% %}
            """
            ),
            filename="",
            is_included=False,
        )
