import os
import textwrap

import jinja2
import platform
import pytest
import sys

from conda_devenv.devenv import render_jinja


def test_jinja_root():
    assert render_jinja("{{root}}", filename="path/to/file") == os.path.abspath("path/to")


def test_jinja_os(monkeypatch):
    template = textwrap.dedent("""\
        {% if os.environ['ENV_VARIABLE'] == '1' -%}
        variable is set
        {%- else -%}
        variable is not set
        {%- endif %}
    """).strip()

    assert render_jinja(template, filename="") == "variable is not set"

    monkeypatch.setenv('ENV_VARIABLE', '1')
    assert render_jinja(template, filename="") == "variable is set"

    monkeypatch.setenv('ENV_VARIABLE', '2')
    assert render_jinja(template, filename="") == "variable is not set"


def test_jinja_sys(monkeypatch):
    template = textwrap.dedent("""\
        {% if sys.platform.startswith('linux') -%}
        linux!
        {%- elif sys.platform.startswith('win') -%}
        windows!
        {%- else -%}
        others!
        {%- endif %}
    """).strip()

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert render_jinja(template, filename="") == "linux!"

    monkeypatch.setattr(sys, 'platform', 'windows')
    assert render_jinja(template, filename="") == "windows!"

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="") == "others!"


def test_jinja_platform(monkeypatch):
    template = "{{ platform.python_revision() }}"
    assert render_jinja(template, filename="") == platform.python_revision()


def test_jinja_invalid_template():
    # TODO: change this to pytest's nicer syntax: with pytest.raises()
    try:
        render_jinja(textwrap.dedent("""\
                {%- if os.environ['ENV_VARIABLE'] == '1' %}
                {% %}
            """), filename="")
        pytest.fail("Should raise an exception")
    except jinja2.exceptions.TemplateSyntaxError as e:
        pass
