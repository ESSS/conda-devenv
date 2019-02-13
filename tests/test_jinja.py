import os
import textwrap

import jinja2
import platform
import pytest
import sys

from conda_devenv.devenv import render_jinja


def test_jinja_root():
    assert render_jinja(
        "{{root}}",
        filename="path/to/file",
        is_included=False,
    ) == os.path.abspath("path/to")


def test_jinja_os(monkeypatch):
    template = textwrap.dedent("""\
        {% if os.environ['ENV_VARIABLE'] == '1' -%}
        variable is set
        {%- else -%}
        variable is not set
        {%- endif %}
    """).strip()

    assert render_jinja(template, filename="", is_included=False) == "variable is not set"

    monkeypatch.setenv('ENV_VARIABLE', '1')
    assert render_jinja(template, filename="", is_included=False) == "variable is set"

    monkeypatch.setenv('ENV_VARIABLE', '2')
    assert render_jinja(template, filename="", is_included=False) == "variable is not set"


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
    assert render_jinja(template, filename="", is_included=False) == "linux!"

    monkeypatch.setattr(sys, 'platform', 'windows')
    assert render_jinja(template, filename="", is_included=False) == "windows!"

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="", is_included=False) == "others!"


def test_jinja_platform(monkeypatch):
    template = "{{ platform.python_revision() }}"
    assert render_jinja(template, filename="", is_included=False) == platform.python_revision()


def test_jinja_x86(monkeypatch):
    template = "{{ x86 }}"

    platform_bkp = platform

    platform.machine = lambda : 'x86'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.machine = lambda : 'x86_64'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform = platform_bkp


def test_jinja_x86_64(monkeypatch):
    template = "{{ x86_64 }}"

    platform_bkp = platform

    platform.machine = lambda : 'x86'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.machine = lambda : 'x86_64'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform = platform_bkp


def test_jinja_linux(monkeypatch):
    template = "{{ linux }}"

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    monkeypatch.setattr(sys, 'platform', 'win')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="", is_included=False) == 'False'


def test_jinja_linux32(monkeypatch):
    template = "{{ linux32 }}"

    monkeypatch.setattr(sys, 'platform', 'linux')

    platform_bkp = platform

    platform.architecture = lambda : ('32bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.architecture = lambda : ('64bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform = platform_bkp


def test_jinja_linux64(monkeypatch):
    template = "{{ linux64 }}"

    monkeypatch.setattr(sys, 'platform', 'linux')

    platform_bkp = platform

    platform.architecture = lambda : ('32bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.architecture = lambda : ('64bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform = platform_bkp


def test_jinja_armv6l(monkeypatch):
    template = "{{ armv6l }}"
    pass

def test_jinja_armv7l(monkeypatch):
    template = "{{ armv7l }}"
    pass


def test_jinja_ppc64le(monkeypatch):
    template = "{{ ppc64le }}"
    pass


def test_jinja_osx(monkeypatch):
    template = "{{ osx }}"

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    monkeypatch.setattr(sys, 'platform', 'win')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="", is_included=False) == 'True'


def test_jinja_unix(monkeypatch):
    template = "{{ unix }}"

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    monkeypatch.setattr(sys, 'platform', 'win')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="", is_included=False) == 'True'


def test_jinja_win(monkeypatch):
    template = "{{ win }}"

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    monkeypatch.setattr(sys, 'platform', 'win')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert render_jinja(template, filename="", is_included=False) == 'False'


def test_jinja_win32(monkeypatch):
    template = "{{ win32 }}"

    monkeypatch.setattr(sys, 'platform', 'win')

    platform_bkp = platform

    platform.architecture = lambda : ('32bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.architecture = lambda : ('64bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform = platform_bkp


def test_jinja_win64(monkeypatch):
    template = "{{ win64 }}"

    monkeypatch.setattr(sys, 'platform', 'win')

    platform_bkp = platform

    platform.architecture = lambda : ('32bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.architecture = lambda : ('64bit', '')
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform = platform_bkp


def test_jinja_py(monkeypatch):
    template = "{{ py }}"

    platform_bkp = platform

    platform.python_version = lambda : '2.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == '27'

    platform.python_version = lambda : '3.4.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == '34'

    platform.python_version = lambda : '3.5.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == '35'

    platform.python_version = lambda : '3.6.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == '36'

    platform.python_version = lambda : '3.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == '37'

    platform = platform_bkp


def test_jinja_py2k(monkeypatch):
    template = "{{ py2k }}"

    platform_bkp = platform

    platform.python_version = lambda : '2.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.python_version = lambda : '3.4.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.python_version = lambda : '3.5.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.python_version = lambda : '3.6.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.python_version = lambda : '3.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform = platform_bkp


def test_jinja_py3k(monkeypatch):
    template = "{{ py3k }}"

    platform_bkp = platform

    platform.python_version = lambda : '2.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'False'

    platform.python_version = lambda : '3.4.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.python_version = lambda : '3.5.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.python_version = lambda : '3.6.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform.python_version = lambda : '3.7.XYZ+'
    assert render_jinja(template, filename="", is_included=False) == 'True'

    platform = platform_bkp


def test_jinja_invalid_template():
    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        render_jinja(
            textwrap.dedent("""\
                {%- if os.environ['ENV_VARIABLE'] == '1' %}
                {% %}
            """),
            filename="",
            is_included=False,
        )
