import shlex
from textwrap import dedent


def render_activate_script(environment, shell):
    """
    :param dict environment:
    :param string shell:
        Valid values are:
            - bash
            - fish
            - cmd
    :return: string
    """
    script = []
    if shell == "bash":
        script = ["#!/bin/bash"]
        script.extend(
            dedent(
                """\
                function add_path {
                    [[ ":$PATH:" != *":${1}:"* ]] && export PATH="${1}:${PATH}" || return 0
                }"""
            ).splitlines()
        )
    elif shell == "cmd":
        script = ["@echo off"]
    elif shell == "fish":
        script = dedent(
            """\
            function add_path
                if contains -- $argv[1] $PATH
                    return
                end

                set PATH $argv[1] $PATH
            end"""
        ).splitlines()

    for variable in sorted(environment):
        value = environment[variable]
        if shell == "bash":
            pathsep = ":"

            if isinstance(value, list):
                # Lists are supposed to prepend to the existing value
                if variable == "PATH":
                    path_entries = environment[variable]
                    for entry in reversed(path_entries):
                        script.append(f"add_path {shlex.quote(entry)}")
                    continue
                value = pathsep.join(value) + pathsep + f"${variable}"
            script.append(f"if [ ! -z ${{{variable}+x}} ]; then")
            script.append(
                '    export CONDA_DEVENV_BKP_{variable}="${variable}"'.format(
                    variable=variable
                )
            )
            script.append("fi")
            script.append(f'export {variable}="{value}"')

        elif shell == "cmd":
            pathsep = ";"
            if isinstance(value, list):
                # Lists are supposed to prepend to the existing value
                value = pathsep.join(value) + pathsep + f"%{variable}%"

            script.append(
                'set "CONDA_DEVENV_BKP_{variable}=%{variable}%"'.format(
                    variable=variable
                )
            )
            script.append(f'set "{variable}={value}"')

        elif shell == "fish":
            quote = '"'
            pathsep = ":"
            if isinstance(value, list):
                # Lists are supposed to prepend to the existing value
                if variable == "PATH":
                    path_entries = environment[variable]
                    for entry in reversed(path_entries):
                        script.append(f"add_path {shlex.quote(entry)}")
                    continue
                value = pathsep.join(value) + pathsep + ("$%s" % variable)

            script.append(
                "set -gx CONDA_DEVENV_BKP_{variable} ${variable}".format(
                    variable=variable
                )
            )
            script.append(
                "set -gx {variable} {quote}{value}{quote}".format(
                    variable=variable, value=value, quote=quote
                )
            )

        else:
            raise ValueError("Unknown shell: %s" % shell)

    return "\n".join(script)


def render_deactivate_script(environment, shell="bash"):
    script = []
    if shell == "bash":
        script = ["#!/bin/bash"]
        script.extend(
            dedent(
                """\
                function remove_path() {
                   local p=":$1:"
                   local d=":$PATH:"
                   d=${d//$p/:}
                   d=${d/#:/}
                   export PATH=${d/%:/}
                }"""
            ).splitlines()
        )
    elif shell == "cmd":
        script = ["@echo off"]
    elif shell == "fish":
        script = dedent(
            """\
            function remove_path
                if set -l index (contains -i $argv[1] $PATH)
                    set --erase PATH[$index]
                end
            end"""
        ).splitlines()

    for variable in sorted(environment):
        if shell == "bash":
            if variable == "PATH":
                path_entries = environment[variable]
                for entry in path_entries:
                    script.append(f"remove_path {shlex.quote(entry)}")
                continue
            script.append(
                "if [ ! -z ${{CONDA_DEVENV_BKP_{variable}+x}} ]; then".format(
                    variable=variable
                )
            )
            script.append(
                '    export {variable}="$CONDA_DEVENV_BKP_{variable}"'.format(
                    variable=variable
                )
            )
            script.append(f"    unset CONDA_DEVENV_BKP_{variable}")
            script.append("else")
            script.append(f"    unset {variable}")
            script.append("fi")

        elif shell == "cmd":
            script.append(
                'set "{variable}=%CONDA_DEVENV_BKP_{variable}%"'.format(
                    variable=variable
                )
            )
            script.append(f"set CONDA_DEVENV_BKP_{variable}=")

        elif shell == "fish":
            if variable == "PATH":
                path_entries = environment[variable]
                for entry in path_entries:
                    script.append(f"remove_path {shlex.quote(entry)}")
                continue

            script.append(
                "set -gx {variable} $CONDA_DEVENV_BKP_{variable}".format(
                    variable=variable
                )
            )
            script.append(f"set -e CONDA_DEVENV_BKP_{variable}")

        else:
            raise ValueError("Unknown platform")

    return "\n".join(script)
