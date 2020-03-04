import shlex
from pathlib import Path
from textwrap import dedent

from typing import Callable, Dict, List, Union, NamedTuple


Value = Union[str, List[str]]
Environment = Dict[str, Value]


class ScriptRenderer(NamedTuple):
    """Renders a script.

    Should be provided a preamble with needed boilerplate, a function capable
    of generating a script body based on the environment, and an optional
    epilogue.
    """

    preamble: str
    generate_body: Callable[[Environment], str]
    epilogue: str = ""

    def render(self, environment: Environment) -> str:
        """Render the script.

        :param environment: The environment to base the script on.
        :return: A full script.
        """
        return "\n".join(
            s
            for s in (
                f"{self.preamble}",
                f"{self.generate_body(environment)}",
                f"{self.epilogue}",
            )
            if s
        )


def bash_and_fish_path(value: List[str]) -> str:
    """Renders the code to add directories to the path for bash and fish.

    :param value: A list of values to prepend to the path.
    :return: The code to prepend to path.
    """
    return "\n".join(f"add_path {shlex.quote(entry)}" for entry in reversed(value))


def list_prepend(
    variable_name: str, value: List[str], *, separator=":", variable_format: str
) -> str:
    """Render the value of a shell list with prepended extra values.

    :param variable_name: The name of the list variable.
    :param value: A list of values to prepend to the variable.
    :param separator: The desired separator.
    :param variable_format: The format for dereferencing a variable on the shell.
    :return: The new value portion to use for the list.
    """
    return separator.join((*value, variable_format.format(variable_name=variable_name)))


def bash_variable(variable_name: str, value: str):
    """Render the code to backup and set a variable in bash.

    :param variable_name: The name of the variable.
    :param value: The new value to set the variable to.
    :return: The code to backup and set the variable.
    """
    return dedent(
        f'''\
        if [ ! -z ${{{variable_name}+x}} ]; then
            export CONDA_DEVENV_BKP_{variable_name}="${variable_name}"
        fi
        export {variable_name}="{value}"'''
    )


def fish_variable(variable_name: str, value: str):
    """Render the code to backup and set a variable in fish.

    :param variable_name: The name of the variable.
    :param value: The new value to set the variable to.
    :return: The code to backup and set the variable.
    """
    return dedent(
        f'''\
        set -gx CONDA_DEVENV_BKP_{variable_name} ${variable_name}
        set -gx {variable_name} "{value}"'''
    )


def bash_and_fish_activate_body(
    environment: Environment, variable_renderer: Callable[[str, str], str]
):
    """Render the activate script body for bash and fish.

    :param environment: The environment to base the script on.
    :param variable_renderer: A function capable of rendering the code to backup
                              and set a variable.
    :return: The script body.
    """

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
    """Render the activate script body for cmd.

    :param environment: The environment to base the script on.
    :return: The script body.
    """
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


ACTIVATE_RENDERERS = {
    "bash": ScriptRenderer(
        preamble=dedent(
            """\
            #!/bin/bash
            function add_path {
                [[ ":$PATH:" != *":${1}:"* ]] && export PATH="${1}:${PATH}" || return 0
            }"""
        ),
        generate_body=lambda env: bash_and_fish_activate_body(env, bash_variable),
        epilogue="unset -f add_path",
    ),
    "fish": ScriptRenderer(
        preamble=dedent(
            """\
            function add_path
                if contains -- $argv[1] $PATH
                    return
                end

                set PATH $argv[1] $PATH
            end"""
        ),
        generate_body=lambda env: bash_and_fish_activate_body(env, fish_variable),
        epilogue="functions --erase add_path",
    ),
    "cmd": ScriptRenderer(
        preamble=dedent(
            """\
            @echo off"""
        ),
        generate_body=cmd_activate_body,
    ),
}


def render_activate_script(environment: Environment, shell: str):
    """Render the activating script for a given environment and a given shell.

    :param environment: The environment to base the script on.
    :param shell:
        Valid values are:
            - bash
            - fish
            - cmd
    :return string: The activate script for the given shell based on the
                    environment.
    """
    try:
        renderer = ACTIVATE_RENDERERS[shell]
    except KeyError as e:
        raise ValueError("Unknown shell: %s" % shell) from e

    return renderer.render(environment)


def bash_and_fish_remove_path(value: List[str]) -> str:
    """Renders the code to remove directories from the path for bash and fish.

    :param value: A list of values to prepend to the path.
    :return: The code to prepend to path.
    """
    return "\n".join(f"remove_path {shlex.quote(entry)}" for entry in value)


def cmd_remove_path(value: List[str]) -> str:
    """Renders the code to remove directories from the path in cmd.

    :param value: A list of values to prepend to the path.
    :return: The code to prepend to path.
    """
    return "\n".join(f"set PATH=%PATH:{Path(entry)};=%" for entry in value)


def bash_unset_variable(variable_name: str):
    """Render the code to unset a variable and/or restore its backp in bash.

    :param variable_name: The name of the variable.
    :param value: The new value to set the variable to.
    :return: The code to backup and set the variable.
    """
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
    """Render the code to unset a variable and/or restore its backp in bash.

    :param variable_name: The name of the variable.
    :param value: The new value to set the variable to.
    :return: The code to backup and set the variable.
    """
    return dedent(
        f"""\
        set -gx {variable_name} $CONDA_DEVENV_BKP_{variable_name}
        set -e CONDA_DEVENV_BKP_{variable_name}"""
    )


def cmd_unset_variable(variable_name: str):
    """Render the code to unset a variable and/or restore its backup in cmd.

    :param variable_name: The name of the variable.
    :return: The code to restore and/or unset the variable.
    """
    return dedent(
        f"""\
        set "{variable_name}=%CONDA_DEVENV_BKP_{variable_name}%"
        set CONDA_DEVENV_BKP_{variable_name}="""
    )


def deactivate_body(
    environment: Environment,
    remove_path: Callable[[List[str]], str],
    variable_unset_renderer: Callable[[str], str],
):
    """Render the activate script body for bash and fish.

    :param environment: The environment to base the script on.
    :param variable_unset_renderer: A function capable of rendering the code to
                                    restore backup or unset a variable.
    :return: The script body.
    """

    def unset_variable(variable_name: str, value: Value) -> str:
        if variable_name == "PATH":
            assert isinstance(value, List)
            return remove_path(value)

        return variable_unset_renderer(variable_name)

    return "\n".join(
        unset_variable(name, value) for name, value in sorted(environment.items())
    )


DEACTIVATE_RENDERERS = {
    "bash": ScriptRenderer(
        preamble=dedent(
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
        generate_body=lambda env: deactivate_body(
            env, bash_and_fish_remove_path, bash_unset_variable
        ),
        epilogue="unset -f remove_path",
    ),
    "fish": ScriptRenderer(
        preamble=dedent(
            """\
            function remove_path
                if set -l index (contains -i $argv[1] $PATH)
                    set --erase PATH[$index]
                end
            end"""
        ),
        generate_body=lambda env: deactivate_body(
            env, bash_and_fish_remove_path, fish_unset_variable
        ),
        epilogue="functions --erase remove_path",
    ),
    "cmd": ScriptRenderer(
        preamble=dedent(
            """\
            @echo off"""
        ),
        generate_body=lambda env: deactivate_body(
            env, cmd_remove_path, cmd_unset_variable
        ),
    ),
}


def render_deactivate_script(environment: Environment, shell="bash"):
    """Render the deactivating script for a given environment and a given shell.

    :param environment: The environment to base the script on.
    :param shell:
        Valid values are:
            - bash
            - fish
            - cmd
    :return string: The deactivate script for the given shell based on the
                    environment.
    """
    try:
        renderer = DEACTIVATE_RENDERERS[shell]
    except KeyError as e:
        raise ValueError("Unknown shell: %s" % shell) from e

    return renderer.render(environment)
