import shlex
from textwrap import dedent

from typing import Callable, Dict, List, Union


ACTIVATE_PREAMBLE = {
    "bash": dedent(
        """\
            #!/bin/bash
            function add_path {
                [[ ":$PATH:" != *":${1}:"* ]] && export PATH="${1}:${PATH}" || return 0
            }"""
    ),
    "cmd": dedent(
        """\
            @echo off"""
    ),
    "fish": dedent(
        """\
            function add_path
                if contains -- $argv[1] $PATH
                    return
                end

                set PATH $argv[1] $PATH
            end"""
    ),
}


Value = Union[str, List[str]]
Environment = Dict[str, Value]


def bash_and_fish_path(value: List[str]) -> str:
    return "\n".join(f"add_path {shlex.quote(entry)}" for entry in reversed(value))


def list_prepend(
    variable_name: str, value: List[str], *, separator=":", variable_format: str
) -> str:
    return separator.join((*value, variable_format.format(variable_name=variable_name)))


def bash_variable(variable_name: str, value: str):
    return dedent(
        f'''\
        if [ ! -z ${{{variable_name}+x}} ]; then
            export CONDA_DEVENV_BKP_{variable_name}="${variable_name}"
        fi
        export {variable_name}="{value}"'''
    )


def fish_variable(variable_name: str, value: str):
    return dedent(
        f'''\
        set -gx CONDA_DEVENV_BKP_{variable_name} ${variable_name}
        set -gx {variable_name} "{value}"'''
    )


def activate_body(
    environment: Environment, variable_renderer: Callable[[str, str], str]
):
    def make_variable(variable_name: str, value: Value) -> str:
        if variable_name == "PATH":
            assert isinstance(value, List)
            return bash_and_fish_path(value)

        value = (
            list_prepend(variable_name, value, variable_format="${variable_name}")
            if isinstance(value, List)
            else value
        )

        return variable_renderer(variable_name, value)

    return "\n".join(
        make_variable(name, value) for name, value in sorted(environment.items())
    )


def cmd_activate_body(environment: Environment):
    body = []

    for variable in sorted(environment):
        value = environment[variable]
        pathsep = ";"
        if isinstance(value, list):
            # Lists are supposed to prepend to the existing value
            value = pathsep.join(value) + pathsep + f"%{variable}%"

        body.append(
            'set "CONDA_DEVENV_BKP_{variable}=%{variable}%"'.format(variable=variable)
        )
        body.append(f'set "{variable}={value}"')

    return "\n".join(body)


def render_activate_script(environment: Environment, shell: str):
    """
    :param dict environment:
    :param string shell:
        Valid values are:
            - bash
            - fish
            - cmd
    :return: string
    """
    script = ACTIVATE_PREAMBLE[shell].splitlines()

    if shell == "bash":
        script.append(activate_body(environment, bash_variable))
    elif shell == "fish":
        script.append(activate_body(environment, fish_variable))
    elif shell == "cmd":
        script.append(cmd_activate_body(environment))
    else:
        raise ValueError("Unknown shell: %s" % shell)

    return "\n".join(script)


DEACTIVATE_PREAMBLE = {
    "bash": dedent(
        """\
            #!/bin/bash
            function remove_path() {
               local p=":$1:"
               local d=":$PATH:"
               d=${d//$p/:}
               d=${d/#:/}
               export PATH=${d/%:/}
            }"""
    ),
    "cmd": dedent(
        """\
            @echo off"""
    ),
    "fish": dedent(
        """\
            function remove_path
                if set -l index (contains -i $argv[1] $PATH)
                    set --erase PATH[$index]
                end
            end"""
    ),
}


def bash_and_fish_remove_path(value: List[str]) -> str:
    return "\n".join(f"remove_path {shlex.quote(entry)}" for entry in value)


def bash_unset_variable(variable_name: str):
    return dedent(
        f"""\
        if [ ! -z ${{CONDA_DEVENV_BKP_{variable_name}+x}} ]; then
            export {variable_name}="$CONDA_DEVENV_BKP_{variable_name}"
            unset CONDA_DEVENV_BKP_{variable_name}
        else
            unset {variable_name}
        fi"""
    )


def fish_unset_variable(variable_name: str):
    return dedent(
        f"""\
        set -gx {variable_name} $CONDA_DEVENV_BKP_{variable_name}
        set -e CONDA_DEVENV_BKP_{variable_name}"""
    )


def deactivate_body(
    environment: Environment, variable_unset_renderer: Callable[[str], str]
):
    def unset_variable(variable_name: str, value: Value) -> str:
        if variable_name == "PATH":
            assert isinstance(value, List)
            return bash_and_fish_remove_path(value)

        return variable_unset_renderer(variable_name)

    return "\n".join(
        unset_variable(name, value) for name, value in sorted(environment.items())
    )


def cmd_deactivate_body(environment):
    body = []
    for variable in sorted(environment):
        body.append(
            'set "{variable}=%CONDA_DEVENV_BKP_{variable}%"'.format(variable=variable)
        )
        body.append(f"set CONDA_DEVENV_BKP_{variable}=")

    return "\n".join(body)


def render_deactivate_script(environment: Environment, shell="bash"):
    script = DEACTIVATE_PREAMBLE[shell].splitlines()

    if shell == "bash":
        script.append(deactivate_body(environment, bash_unset_variable))
    elif shell == "fish":
        script.append(deactivate_body(environment, fish_unset_variable))
    elif shell == "cmd":
        script.append(cmd_deactivate_body(environment))
    else:
        raise ValueError("Unknown platform")

    return "\n".join(script)
