import os
import textwrap

import sys

import pytest

from conda_devenv.devenv import render_activate_script, render_deactivate_script


@pytest.fixture
def single_values():
    return {"VALUE": "value"}


@pytest.fixture
def multiple_values():
    paths = ["path_a", "path_b"]
    return {"PATH": paths, "LD_LIBRARY_PATH": paths}


def test_render_activate_and_deactivate_scripts_bash(single_values, multiple_values):
    # activate
    assert render_activate_script(single_values, "bash") == textwrap.dedent("""\
        #!/bin/bash
        if [ ! -z ${VALUE+x} ]; then
            export CONDA_DEVENV_BKP_VALUE="$VALUE"
        fi
        export VALUE="value"
        """).strip()
    assert render_activate_script(multiple_values, "bash") == textwrap.dedent("""\
        #!/bin/bash
        if [ ! -z ${LD_LIBRARY_PATH+x} ]; then
            export CONDA_DEVENV_BKP_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
        fi
        export LD_LIBRARY_PATH="path_a:path_b:$LD_LIBRARY_PATH"
        if [ ! -z ${PATH+x} ]; then
            export CONDA_DEVENV_BKP_PATH="$PATH"
        fi
        export PATH="path_a:path_b:$PATH"
        """).strip()

    # deactivate
    assert render_deactivate_script(single_values, "bash") == textwrap.dedent("""\
        #!/bin/bash
        if [ ! -z ${CONDA_DEVENV_BKP_VALUE+x} ]; then
            export VALUE="$CONDA_DEVENV_BKP_VALUE"
            unset CONDA_DEVENV_BKP_VALUE
        else
            unset VALUE
        fi
        """).strip()
    assert render_deactivate_script(multiple_values, "bash") == textwrap.dedent("""\
        #!/bin/bash
        if [ ! -z ${CONDA_DEVENV_BKP_LD_LIBRARY_PATH+x} ]; then
            export LD_LIBRARY_PATH="$CONDA_DEVENV_BKP_LD_LIBRARY_PATH"
            unset CONDA_DEVENV_BKP_LD_LIBRARY_PATH
        else
            unset LD_LIBRARY_PATH
        fi
        if [ ! -z ${CONDA_DEVENV_BKP_PATH+x} ]; then
            export PATH="$CONDA_DEVENV_BKP_PATH"
            unset CONDA_DEVENV_BKP_PATH
        else
            unset PATH
        fi
        """).strip()


def test_render_activate_and_deactivate_scripts_cmd(single_values, multiple_values):
    # activate
    assert render_activate_script(single_values, "cmd") == textwrap.dedent("""\
        @echo off
        set "CONDA_DEVENV_BKP_VALUE=%VALUE%"
        set "VALUE=value"
        """).strip()
    assert render_activate_script(multiple_values, "cmd") == textwrap.dedent("""\
        @echo off
        set "CONDA_DEVENV_BKP_LD_LIBRARY_PATH=%LD_LIBRARY_PATH%"
        set "LD_LIBRARY_PATH=path_a;path_b;%LD_LIBRARY_PATH%"
        set "CONDA_DEVENV_BKP_PATH=%PATH%"
        set "PATH=path_a;path_b;%PATH%"
        """).strip()

    # deactivate
    assert render_deactivate_script(single_values, "cmd") == textwrap.dedent("""\
        @echo off
        set "VALUE=%CONDA_DEVENV_BKP_VALUE%"
        set CONDA_DEVENV_BKP_VALUE=
        """).strip()
    assert render_deactivate_script(multiple_values, "cmd") == textwrap.dedent("""\
        @echo off
        set "LD_LIBRARY_PATH=%CONDA_DEVENV_BKP_LD_LIBRARY_PATH%"
        set CONDA_DEVENV_BKP_LD_LIBRARY_PATH=
        set "PATH=%CONDA_DEVENV_BKP_PATH%"
        set CONDA_DEVENV_BKP_PATH=
        """).strip()


def test_render_activate_and_deactivate_scripts_fish(single_values, multiple_values):
    # activate
    assert render_activate_script(single_values, "fish") == textwrap.dedent("""\
        set -gx CONDA_DEVENV_BKP_VALUE $VALUE
        set -gx VALUE "value"
        """).strip()
    assert render_activate_script(multiple_values, "fish") == textwrap.dedent("""\
        set -gx CONDA_DEVENV_BKP_LD_LIBRARY_PATH $LD_LIBRARY_PATH
        set -gx LD_LIBRARY_PATH "path_a:path_b:$LD_LIBRARY_PATH"
        set -gx CONDA_DEVENV_BKP_PATH $PATH
        set -gx PATH path_a path_b $PATH
        """).strip()

    # deactivate
    assert render_deactivate_script({"VALUE": "value"}, "fish") == textwrap.dedent("""\
        set -gx VALUE $CONDA_DEVENV_BKP_VALUE
        set -e CONDA_DEVENV_BKP_VALUE
        """).strip()
    assert render_deactivate_script(multiple_values, "fish") == textwrap.dedent("""\
        set -gx LD_LIBRARY_PATH $CONDA_DEVENV_BKP_LD_LIBRARY_PATH
        set -e CONDA_DEVENV_BKP_LD_LIBRARY_PATH
        set -gx PATH $CONDA_DEVENV_BKP_PATH
        set -e CONDA_DEVENV_BKP_PATH
        """).strip()
