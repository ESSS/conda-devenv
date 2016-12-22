import os
import textwrap

import sys

from conda_devenv.devenv import render_activate_script, render_deactivate_script


def test_render_activate_script(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "pathsep", ":")
    assert render_activate_script({"VALUE": "value"}) == textwrap.dedent("""\
        #!/bin/sh
        export CONDA_DEVENV_BKP_VALUE=$VALUE
        export VALUE="value"
        """).strip()
    assert render_activate_script({"PATH": ["path_a", "path_b"]}) == textwrap.dedent("""\
        #!/bin/sh
        export CONDA_DEVENV_BKP_PATH=$PATH
        export PATH="path_a:path_b:$PATH"
        """).strip()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "pathsep", ";")
    assert render_activate_script({"VALUE": "value"}) == textwrap.dedent("""\
        set CONDA_DEVENV_BKP_VALUE=%VALUE%
        set VALUE="value"
        """).strip()
    assert render_activate_script({"PATH": ["path_a", "path_b"]}) == textwrap.dedent("""\
        set CONDA_DEVENV_BKP_PATH=%PATH%
        set PATH="path_a;path_b;%PATH%"
        """).strip()


def test_render_deactivate_script(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "pathsep", ":")
    assert render_deactivate_script({"VALUE": "value"}) == textwrap.dedent("""\
        #!/bin/sh
        export VALUE=$CONDA_DEVENV_BKP_VALUE
        unset CONDA_DEVENV_BKP_VALUE
        """).strip()
    assert render_deactivate_script({"PATH": ["path_a", "path_b"]}) == textwrap.dedent("""\
        #!/bin/sh
        export PATH=$CONDA_DEVENV_BKP_PATH
        unset CONDA_DEVENV_BKP_PATH
        """).strip()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "pathsep", ";")
    assert render_deactivate_script({"VALUE": "value"}) == textwrap.dedent("""\
        set VALUE=%CONDA_DEVENV_BKP_VALUE%
        set CONDA_DEVENV_BKP_VALUE=
        """).strip()
    assert render_deactivate_script({"PATH": ["path_a", "path_b"]}) == textwrap.dedent("""\
        set PATH=%CONDA_DEVENV_BKP_PATH%
        set CONDA_DEVENV_BKP_PATH=
        """).strip()
