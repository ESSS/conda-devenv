from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Literal

import yaml
from colorama import Fore
from typing_extensions import Self

from .gen_scripts import Environment
from .gen_scripts import render_activate_script
from .gen_scripts import render_deactivate_script

_selector_pattern = re.compile(r".*?#\s*\[(.*)\].*")

YAMLData = dict[str, Any]


@dataclass(frozen=True)
class ProcessedEnvironment:
    """
    Result of processing a .devenv.yml or a plain .yml file.
    """

    conda_yaml_dict: YAMLData | None
    environment_contents: dict
    rendered_yaml: str

    @classmethod
    def from_file(cls, p: Path) -> Self:
        if is_devenv_file(p):
            conda_yaml_dict, environment_contents = load_yaml_dict(p)
            rendered_yaml = render_for_conda_env(conda_yaml_dict)
            return cls(
                conda_yaml_dict=conda_yaml_dict,
                environment_contents=environment_contents,
                rendered_yaml=rendered_yaml,
            )
        else:
            return cls(
                conda_yaml_dict=None,
                environment_contents={},
                rendered_yaml=p.read_text(),
            )


class UsageError(Exception):
    """
    Raised when a usage error occurs. In this case, we capture the exception
    and show to the user instead of blowing with a traceback.
    """


def preprocess_selector_in_line(line: str) -> str:
    x = _selector_pattern.search(line)
    if x is None:
        return line
    expr = x.group(1).strip()
    return f"{{% if {expr} %}}{line}{{% endif %}}"


def preprocess_selectors(contents: str) -> str:
    lines = [preprocess_selector_in_line(line) for line in contents.split("\n")]
    return "\n".join(lines)


def _min_conda_devenv_version(min_version: str) -> str:
    """Checks that the current conda devenv version is at least the given version"""
    from packaging.version import parse
    import conda_devenv

    if parse(conda_devenv.__version__) < parse(min_version):
        raise UsageError(
            f"This file requires at minimum conda-devenv {min_version}, "
            f"but you have {conda_devenv.__version__} installed.\n"
            "Please update conda-devenv.\n"
        )

    return ""


def _get_env(
    var_name: str, default: str | None = None, valid: Sequence[str] | None = None
) -> str:
    """Get env var value or default value and check against allowed values.

    :param var_name:
        Name of the environment variable.
    :param default:
        Default value for the variable. If not specified, the method raises
        an error when the variable is not set.
    :param valid:
        List of allowed values of the variable.
    :return:
        Value of the environment variable or default
    """
    value = os.environ.get(var_name, default)

    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set.")

    if valid is not None and value not in valid:
        raise ValueError(
            f"Allowed values for environment variable {var_name} are {valid}, "
            f"got {value}"
        )

    return value


def render_jinja(contents: str, filename: Path, is_included: bool) -> str:
    import jinja2
    import sys
    import platform

    iswin = sys.platform.startswith("win")
    islinux = sys.platform.startswith("linux")
    isosx = sys.platform.startswith("darwin")

    is32bit = "32bit" == platform.architecture()[0]
    is64bit = not is32bit

    jinja_dict = {
        "is_included": is_included,
        "os": os,
        "platform": platform,
        "root": os.path.dirname(os.path.abspath(filename)),
        "sys": sys,
        "aarch64": "aarch64" == platform.machine(),
        "arm64": isosx and "arm64" == platform.machine(),
        "x86": "x86" == platform.machine(),
        "x86_64": "x86_64" == platform.machine(),
        "linux": islinux,
        "linux32": islinux and is32bit,
        "linux64": islinux and is64bit,
        "osx": isosx,
        "unix": islinux or isosx,
        "win": iswin,
        "win32": iswin and is32bit,
        "win64": iswin and is64bit,
        "min_conda_devenv_version": _min_conda_devenv_version,
        "get_env": _get_env,
    }

    contents = preprocess_selectors(contents)

    return jinja2.Template(contents).render(**jinja_dict)


def handle_includes(root_filename: Path, root_yaml: YAMLData) -> dict[Path, YAMLData]:
    # This is a depth-first search
    import yaml
    import collections

    queue = collections.OrderedDict({Path(root_filename).resolve(): root_yaml})
    visited = collections.OrderedDict()

    if root_yaml is None:
        raise ValueError(
            "The root file '{root_filename}' is empty.".format(
                root_filename=root_filename
            )
        )

    while queue:
        filename, yaml_dict = queue.popitem()
        if filename in visited:
            continue

        for included_filename in yaml_dict.get("includes") or []:
            if Path(included_filename).is_absolute():
                included_filename = Path(included_filename)
            else:
                included_filename = Path(filename).parent / included_filename

            if not included_filename.is_file():
                raise ValueError(
                    "Couldn't find the file '{included_filename}' "
                    "while processing the file '{filename}'.".format(
                        included_filename=included_filename, filename=filename
                    )
                )
            jinja_contents = render_jinja(
                included_filename.read_text(encoding="UTF-8"),
                included_filename,
                is_included=True,
            )
            included_yaml_dict = yaml.safe_load(jinja_contents)
            if included_yaml_dict is None:
                raise ValueError(
                    "The file '{included_filename}' which was"
                    " included by '{filename}' is empty.".format(
                        included_filename=included_filename, filename=filename
                    )
                )
            queue[included_filename.resolve()] = included_yaml_dict

        if "includes" in yaml_dict:
            del yaml_dict["includes"]

        visited[filename] = yaml_dict

    return visited


def separate_strings_from_dicts(
    elements: Sequence[str | dict],
) -> tuple[Sequence[str], Sequence[dict]]:
    """
    Receive a list of strings and dicts and returns 2 lists, one solely with string and the other
    with dicts.
    """
    all_strs = []
    all_dicts = []
    for item in elements:
        if isinstance(item, str):
            all_strs.append(item)
        elif isinstance(item, dict):
            all_dicts.append(item)
        else:
            raise RuntimeError(f"Only strings and dicts are supported, got: {item!r}")
    return all_strs, all_dicts


def merge(
    dicts: Iterable[YAMLData], keys_to_skip: Sequence[str] = ("name",)
) -> YAMLData:
    final_dict: YAMLData = {}

    for d in dicts:
        if not isinstance(d, dict):
            raise ValueError(
                "Found '{!r}' when a dict is expected, check if our's '*.devenv.yml'"
                " files are properly formatted.".format(d)
            )
        for key, value in d.items():
            if key in keys_to_skip:
                continue

            if key in final_dict:
                if isinstance(value, dict):
                    final_dict[key] = merge([final_dict[key], value])
                elif isinstance(value, list):
                    # The can be dicts inside lists `'dependencies': [{'pip': ['foo', 'bar']}]`.
                    target_strings, target_dicts = separate_strings_from_dicts(
                        final_dict[key]
                    )
                    new_strings, new_dicts = separate_strings_from_dicts(value)
                    s: set[str] = {*target_strings, *new_strings}
                    merged_list: list[str | YAMLData] = list(sorted(s))
                    merged_dict = merge(list(target_dicts) + list(new_dicts))
                    if len(merged_dict) > 0:
                        merged_list.append(merged_dict)
                    final_dict[key] = merged_list
                elif value is None:
                    continue
                else:
                    message = " ".join(
                        [
                            "Can't merge the key: '{key}' because it will override the previous value.",
                            "Only lists and dicts can be merged. The type obtained was: {type}",
                        ]
                    ).format(key=key, type=type(value))
                    raise ValueError(message)
            elif value is not None:
                final_dict[key] = value
    merge_dependencies_version_specifications(final_dict, key_to_merge="dependencies")
    return final_dict


def merge_dependencies_version_specifications(
    yaml_dict: YAMLData, key_to_merge: str, pip: bool = False
) -> None:
    import collections
    import re

    value_to_merge = yaml_dict.get(key_to_merge, None)
    if value_to_merge is None:
        return

    package_pattern = (
        r"^(?P<channel>[a-z0-9_\-/.]+::)?"
        # package regex based on https://conda.io/docs/building/pkg-name-conv.html#package-naming-conventions
        r"(?P<package>[a-z0-9_\-.]+)"
        r"\s*(?P<version>.*)$"
    )

    new_dependencies: dict[str, collections.OrderedDict] = {}
    new_dict_dependencies = []
    for dep in value_to_merge:
        if isinstance(dep, dict):
            for key in dep:
                merge_dependencies_version_specifications(
                    dep, key_to_merge=key, pip=(key == "pip")
                )
            new_dict_dependencies.append(dep)
        elif isinstance(dep, str):
            if pip and ("+" in dep or ":" in dep or dep.startswith("-")):
                # Look for dependencies in the pip section that are
                # managed by version control or contain flags.  For example:
                #   hg+ssh://hg@bitbucket.org/mforbes/mmfutils-fork@0.4.12
                #   --editable path/to/local/package
                # Skip processing these and just pass them through
                package_name = dep
                package_version = ""
            else:
                m = re.match(package_pattern, dep, flags=re.IGNORECASE)
                if m is None:
                    raise RuntimeError(
                        'The package version specification "{}" do not follow the'
                        " expected format.".format(dep)
                    )
                # Consider the channel name as part of the package name.
                # If multiple channels are specified, the package will be repeated.
                package_name = m.group("package")
                if m.group("channel"):
                    package_name = m.group("channel") + package_name

                package_version = m.group("version")

            # OrderedDict is used as an ordered set, the value is ignored.
            version_matchers = new_dependencies.setdefault(
                package_name, collections.OrderedDict()
            )
            if len(package_version) > 0:
                version_matchers[package_version] = True
        else:
            raise RuntimeError(f"Only strings and dicts are supported, got: {dep!r}")

    result = set()
    for dep_name, dep_version_matchers in new_dependencies.items():
        if len(dep_version_matchers) > 0:
            result.add(dep_name + " " + ",".join(dep_version_matchers))
        else:
            result.add(dep_name)

    new_dict_dependencies = sorted(new_dict_dependencies, key=lambda x: list(x.keys()))
    yaml_dict[key_to_merge] = sorted(result) + new_dict_dependencies


def load_yaml_dict(filename: Path) -> tuple[YAMLData, dict]:
    with open(filename) as f:
        contents = f.read()
    rendered_contents = render_jinja(contents, filename, is_included=False)

    import yaml

    root_yaml = yaml.safe_load(rendered_contents)

    all_yaml_dicts = handle_includes(filename, root_yaml)

    for filename, yaml_dict in all_yaml_dicts.items():
        environment_key_value = yaml_dict.get("environment", {})
        if environment_key_value is None:
            # Just an empty 'environment:' line will return None.
            environment_key_value = {}
        if not isinstance(environment_key_value, dict):
            raise ValueError(
                "The 'environment' key is supposed to be a dictionary, but you have the type "
                "'{type}' at '{filename}'.".format(
                    type=type(environment_key_value), filename=filename
                )
            )

    merged_dict = merge(all_yaml_dicts.values())

    # Force the "name" because we want to keep the name of the root yaml
    if "name" in root_yaml:
        merged_dict["name"] = root_yaml["name"]

    environment = merged_dict.pop("environment", {})
    return merged_dict, environment


def get_env_name_from_yaml_data(yaml_data: YAMLData) -> str:
    """Gets the name from the yaml data, raising an appropriate UserError if not found."""
    try:
        return yaml_data["name"]
    except KeyError:
        raise UsageError("file environment.devenv.yml has no 'name' key defined.")


DEFAULT_HEADER = "# generated by conda-devenv, do not modify and do not commit to VCS\n"


def render_for_conda_env(yaml_dict: YAMLData, header: str = DEFAULT_HEADER) -> str:
    import yaml

    contents = header
    contents += yaml.dump(yaml_dict, default_flow_style=False)
    return contents


def __write_conda_environment_file(
    args: argparse.Namespace, filename: Path, rendered_contents: str
) -> Path:
    if args.output_file:
        output_filename = args.output_file
    else:
        output_filename, yaml_ext = os.path.splitext(filename)
        output_filename, devenv_ext = os.path.splitext(output_filename)
        if yaml_ext == "" or devenv_ext == "":
            # File has no extension or has a single extension, if we proceed we
            # will override the input file
            raise ValueError(
                "Can't guess the output filename, please provide "
                "the output filename with the --output-filename "
                "flag"
            )
        output_filename += yaml_ext

    with open(output_filename, "w") as f:
        f.write(rendered_contents)

    return output_filename


def truncate_history_file(env_directory: Path | None) -> None:
    """
    Since conda version 4.4 the "--prune" option does not prune the environment to match just the
    supplied specs but take in account the previous environment history we truncate the history
    file so only the package and version specs from the environment description file are used.

    This is based on the comments:
    - https://github.com/conda/conda/issues/6809#issuecomment-367877250
    - https://github.com/conda/conda/issues/7279#issuecomment-389359679

    If the behavior of the "--prune" option changes again or something in the lines
    "--ignore-history" or "--prune-hard" ar implemented we should revisit this function and
    update the "conda-env" arguments.
    """
    if env_directory is None:
        return  # Environment does not exist, no history to truncate

    from os.path import isfile, join
    from time import time
    from shutil import copyfile

    history_filename = join(env_directory, "conda-meta", "history")
    history_backup_filename = f"{history_filename}.{time()}"
    if isfile(history_filename):
        copyfile(history_filename, history_backup_filename)

        with open(history_filename, "w") as history:
            history.truncate()


def __call_conda_env_update(
    args: argparse.Namespace,
    output_filename: Path,
    env_manager: Literal["conda", "mamba"],
) -> int:
    cmdline_args = [
        "env",
        "update",
        "--file",
        str(output_filename),
    ]
    if not args.no_prune:
        cmdline_args.append("--prune")
    if args.name:
        cmdline_args.extend(["--name", args.name])
    if args.quiet:
        cmdline_args.extend(["--quiet"])
    if args.verbose:
        cmdline_args.extend(["-" + "v" * args.verbose])

    if not args.quiet:
        full_cmdline = [str(env_manager)] + cmdline_args
        print(f"{Fore.CYAN}{' '.join(full_cmdline)}{Fore.RESET}")

    return _call_conda(env_manager, cmdline_args)


def _call_conda(env_manager: Literal["conda", "mamba"], args: Sequence[str]) -> int:
    """
    Calls conda-env or mamba directly via subprocess.check_call.

    We have this indirection here to mock this function during testing.
    """
    # We need shell=True on Windows because conda and mamba are .bat files.
    return subprocess.check_call(
        [str(env_manager)] + list(args), shell=sys.platform.startswith("win")
    )


def write_activate_deactivate_scripts(
    args: argparse.Namespace,
    conda_yaml_dict: YAMLData,
    env_manager: Literal["conda", "mamba"],
    environment: Environment,
    env_directory: Path | None,
) -> None:
    if env_directory is None:
        env_name = args.name or get_env_name_from_yaml_data(conda_yaml_dict)
        env_directory = get_env_directory(env_manager, env_name)
        if env_directory is None:
            raise UsageError(f"Couldn't find directory of environment '{env_name}'")

    from os.path import join

    activate_directory = join(env_directory, "etc", "conda", "activate.d")
    deactivate_directory = join(env_directory, "etc", "conda", "deactivate.d")

    if not os.path.exists(activate_directory):
        os.makedirs(activate_directory)
    if not os.path.exists(deactivate_directory):
        os.makedirs(deactivate_directory)

    if sys.platform == "win32":
        # Generate scripts for cmd.exe and powershell
        files = [("devenv-vars.bat", "cmd"), ("devenv-vars.ps1", "ps1")]
    else:
        # Linux and Mac should create a .sh
        files = [("devenv-vars.sh", "bash"), ("devenv-vars.fish", "fish")]

    for filename, shell in files:
        activate_script = render_activate_script(environment, shell)
        deactivate_script = render_deactivate_script(environment, shell)

        with open(join(activate_directory, filename), "w") as f:
            f.write(activate_script)
        with open(join(deactivate_directory, filename), "w") as f:
            f.write(deactivate_script)


def get_env_name(
    args: argparse.Namespace,
    output_filename: Path,
    conda_yaml_dict: YAMLData | None = None,
) -> str:
    """
    :param args:
        When the user supplies the name option in the command line this namespace have a "name"
        defined with a not `None` value and this value is returned.
    :param output_filename:
        No jinja rendering is performed on this file if it is used.
    :param conda_yaml_dict:
        If supplied and not `None` then `output_filename` is ignored.
    """
    if args.name:
        return args.name

    if conda_yaml_dict is None:
        with open(output_filename) as stream:
            conda_yaml_dict = yaml.safe_load(stream)

    return get_env_name_from_yaml_data(conda_yaml_dict)


def _get_envs_dirs_from_conda(env_manager: Literal["conda", "mamba"]) -> Sequence[Path]:
    # We need shell=True on Windows because conda and mamba are .bat files.
    output = subprocess.check_output(
        [str(env_manager), "info", "--json"],
        text=True,
        shell=sys.platform.startswith("win"),
    )
    info = json.loads(output)
    return [Path(x) for x in info["envs_dirs"]]


def get_env_directory(
    env_manager: Literal["conda", "mamba"], env_name: str
) -> Path | None:
    """
    The environment path if the environment exists.
    """
    envs_dirs = _get_envs_dirs_from_conda(env_manager)

    for directory in envs_dirs:
        env = os.path.join(directory, env_name)
        conda_meta_dir = os.path.join(env, "conda-meta")
        if os.path.isdir(conda_meta_dir):
            return Path(os.path.normpath(env))

    return None


def parse_env_var_args(env_var_args: Sequence[str] | None) -> Mapping[str, str]:
    """
    :param env_var_args:
        List of arguments in the form "VAR_NAME" or "VAR_NAME=VALUE"
    :return:
        Mapping from "VAR_NAME" to "VALUE" or empty str.
    """
    env_vars = {}
    if env_var_args is not None:
        for arg in env_var_args:
            split_arg = arg.split("=", 1)
            if len(split_arg) == 1:
                env_vars[split_arg[0]] = ""
            elif len(split_arg) == 2:
                env_vars[split_arg[0]] = split_arg[1]

    return env_vars


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="devenv",
        description="Work with multiple conda-environment-like yaml files in dev mode.",
    )
    parser.add_argument(
        "--file",
        "-f",
        nargs="?",
        help="The environment.devenv.yml file to process. "
        "The default value is '%(default)s'.",
        default="environment.devenv.yml",
    )
    parser.add_argument("--name", "-n", nargs="?", help="Name of environment.")
    parser.add_argument(
        "--print",
        help="Prints the rendered file as will be sent to conda-"
        "env to stdout and exits.",
        action="store_true",
    )
    parser.add_argument(
        "--print-full",
        help="Similar to --print, but also includes the 'environment' section.",
        action="store_true",
    )
    parser.add_argument(
        "--no-prune", help="Don't pass --prune flag to conda-env.", action="store_true"
    )
    parser.add_argument("--output-file", nargs="?", help="Output filename.")
    parser.add_argument(
        "--quiet", action="store_true", default=False, help="Do not show progress"
    )
    parser.add_argument(
        "--env-var",
        "-e",
        action="append",
        help="Define or override environment variables in the form VAR_NAME or "
        "VAR_NAME=VALUE.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Use once for info, twice for debug, three times for trace.",
    )
    parser.add_argument(
        "--version", action="store_true", default=False, help="Show version and exit"
    )
    parser.add_argument(
        "--env-manager",
        "-m",
        help="The environment manager to use. "
        "Default to 'conda' or the value of 'CONDA_DEVENV_ENV_MANAGER' environment variable if set.",
        default=None,
    )

    argv = sys.argv[1:] if argv is None else argv
    return parser.parse_args(argv)


def main(args: list[str] | None = None) -> int | str | None:
    args_namespace = parse_args(args)
    try:
        return main_with_args_namespace(args_namespace)
    except UsageError as e:
        print(f"{Fore.RED}ERROR: {e}{Fore.RESET}", file=sys.stderr)
        return 2


def mamba_main(args: list[str] | None = None) -> int | str | None:
    args_namespace = parse_args(args)
    if args_namespace.env_manager is None:
        args_namespace.env_manager = "mamba"
    try:
        return main_with_args_namespace(args_namespace)
    except UsageError as e:
        print(f"{Fore.RED}ERROR: {e}{Fore.RESET}", file=sys.stderr)
        return 2


def resolve_env_manager(args: argparse.Namespace) -> Literal["conda", "mamba"]:
    """
    Resolve which environment manager to use, consulting the command-line and
    the appropriate environment variable.
    """
    env_manager = args.env_manager
    if env_manager is None:
        env_manager_origin = "environment variable"
        env_manager = os.environ.get("CONDA_DEVENV_ENV_MANAGER", "conda")
    else:
        env_manager_origin = "'--env-manager' ('-m') option"

    if env_manager not in ("conda", "mamba"):
        raise UsageError(
            (
                f'conda-devenv does not know the environment manager "{env_manager}" '
                f"obtained from {env_manager_origin}."
            ),
        )

    if shutil.which(env_manager) is None:
        raise UsageError(
            f'Could not find "{env_manager}" on PATH, obtained from {env_manager_origin}.'
        )
    return env_manager


def main_with_args_namespace(args: argparse.Namespace) -> int | str | None:
    if args.version:
        from conda_devenv import __version__

        print(f"conda-devenv version {__version__}")
        return 0

    os.environ.update(parse_env_var_args(args.env_var))
    env_manager = resolve_env_manager(args)

    if args.print or args.print_full:
        render = ProcessedEnvironment.from_file(resolve_source_file(args))
        print(render.rendered_yaml)
        if args.print_full and render.environment_contents:
            print(
                render_for_conda_env(
                    {"environment": render.environment_contents}, header=""
                )
            )
        return 0

    return create_update_env(env_manager, args)


def resolve_source_file(args: argparse.Namespace) -> Path:
    """Get and verify that the argument passed on the command-line is correct."""
    filename = Path(args.file)
    if not filename.is_file():
        raise UsageError(f'file "{filename}" does not exist.')
    return filename


def is_devenv_file(p: Path) -> bool:
    """Return True if the given file appears to be a devenv.yml file."""
    return p.suffixes == [".devenv", ".yml"]


def create_update_env(
    env_manager: Literal["conda", "mamba"], args: argparse.Namespace
) -> int:
    filename = resolve_source_file(args)
    render = ProcessedEnvironment.from_file(filename)
    if is_devenv_file(filename):
        # Write the processed contents into the equivalent environment.yml file.
        output_filename = __write_conda_environment_file(
            args, filename, render.rendered_yaml
        )
    else:
        # Just call conda-env directly in plain environment.yml files.
        output_filename = filename

    # Hack around --prune not working correctly (at least in conda; mamba seems to work correctly).
    env_name = get_env_name(args, output_filename, render.conda_yaml_dict)
    env_directory = get_env_directory(env_manager, env_name)
    if not args.no_prune:
        # Truncate the history file
        truncate_history_file(env_directory)

    # Call conda-env update
    if return_code := __call_conda_env_update(args, output_filename, env_manager):
        return return_code

    if is_devenv_file(filename):
        write_activate_deactivate_scripts(
            args,
            env_manager=env_manager,
            conda_yaml_dict=render.conda_yaml_dict or {},
            environment=render.environment_contents,
            env_directory=env_directory,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
