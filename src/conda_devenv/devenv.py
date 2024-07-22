from __future__ import annotations

import argparse
import collections
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
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any
from typing import Literal

from colorama import Fore
from typing_extensions import Self

from .gen_scripts import render_activate_script
from .gen_scripts import render_deactivate_script

_selector_pattern = re.compile(r".*?#\s*\[(.*)\].*")

YAMLData = dict[str, Any]


@dataclass(frozen=True)
class ProcessedEnvironment:
    """
    Result of processing a .devenv.yml or a plain .yml file.
    """

    conda_yaml_dict: YAMLData
    rendered_yaml: str
    is_devenv_file: bool

    @classmethod
    def from_file(cls, p: Path, *, conda_platform: CondaPlatform | None = None) -> Self:
        is_devenv_file = p.suffixes[-2:] == [".devenv", ".yml"]

        conda_yaml_dict = load_yaml_dict(p, conda_platform=conda_platform)
        if is_devenv_file:
            rendered_yaml = render_for_conda_env(conda_yaml_dict)
        else:
            rendered_yaml = p.read_text(encoding="UTF-8")
        return cls(
            conda_yaml_dict=conda_yaml_dict,
            rendered_yaml=rendered_yaml,
            is_devenv_file=is_devenv_file,
        )


class CondaPlatform(Enum):
    """Enumerates the known platforms in conda convention."""

    Win32 = "win-32"
    Win64 = "win-64"
    Linux32 = "linux-32"
    Linux64 = "linux-64"
    Osx32 = "osx-32"
    Osx64 = "osx-64"

    @classmethod
    def current(cls) -> Self:
        import sys
        import platform

        if sys.platform.startswith("win"):
            name = "win"
        elif sys.platform.startswith("linux"):
            name = "linux"
        elif sys.platform.startswith("darwin"):
            name = "osx"
        else:
            name = ""

        bits = "32" if platform.architecture()[0] == "32bit" else "64"
        return cls(f"{name}-{bits}")

    @cached_property
    def name(self) -> str:
        return self.value.split("-")[0]

    @cached_property
    def bits(self) -> int:
        return int(self.value.split("-")[1])

    @cached_property
    def selectors(self) -> Mapping[str, bool]:
        """
        Returns platform-specific selectors that can be used for rendering
        environment.devenv.yml files.
        """
        name = self.name
        bits = self.bits
        return {
            "linux": name == "linux",
            "linux32": name == "linux" and bits == 32,
            "linux64": name == "linux" and bits == 64,
            "osx": name == "osx",
            "osx32": name == "osx" and bits == 32,
            "osx64": name == "osx" and bits == 64,
            "unix": name in ("linux", "osx"),
            "win": name == "win",
            "win32": name == "win" and bits == 32,
            "win64": name == "win" and bits == 64,
        }


class UsageError(Exception):
    """
    Raised when a usage error occurs. In this case, we capture the exception
    and show to the user instead of blowing with a traceback.
    """


class LockFileNotFoundError(Exception):
    """
    Raised when we attempt to create/update an env using a lock file, but it does not exist.
    """

    def __init__(self, lock_file: Path) -> None:
        super().__init__(f"Required lock file {lock_file} not found")
        self.lock_file = lock_file


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


def render_jinja(
    contents: str,
    filename: Path,
    *,
    is_included: bool,
    conda_platform: CondaPlatform,
) -> str:
    import jinja2
    import sys
    import platform

    jinja_dict = {
        "aarch64": "aarch64" == platform.machine(),
        "arm64": conda_platform.name == "osx" and "arm64" == platform.machine(),
        "get_env": _get_env,
        "is_included": is_included,
        "min_conda_devenv_version": _min_conda_devenv_version,
        "os": os,
        "platform": platform,
        "root": os.path.dirname(os.path.abspath(filename)),
        "sys": sys,
        "x86": "x86" == platform.machine(),
        "x86_64": "x86_64" == platform.machine(),
        **conda_platform.selectors,
    }

    contents = preprocess_selectors(contents)
    return jinja2.Template(contents).render(**jinja_dict)


def handle_includes(
    root_filename: Path, root_yaml: YAMLData, conda_platform: CondaPlatform
) -> dict[Path, YAMLData]:
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
                conda_platform=conda_platform,
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
                    # There can be dicts inside lists `'dependencies': [{'pip': ['foo', 'bar']}]`.
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

    return final_dict


def process_constraints_into_dependencies(yaml_dict: YAMLData) -> None:
    """
    Adds new package specifications to 'dependencies' if they appear in the 'constraints' section.
    """
    if not yaml_dict.get("constraints") or not yaml_dict.get("dependencies"):
        return

    dependency_names = {
        PackageSpecifier.parse(dep).name
        for dep in yaml_dict["dependencies"]
        if isinstance(dep, str)
    }

    added_dependencies = [
        constraint
        for constraint in yaml_dict["constraints"]
        if PackageSpecifier.parse(constraint).name in dependency_names
    ]

    yaml_dict["dependencies"] += added_dependencies


def merge_dependencies_version_specifications(
    yaml_dict: YAMLData, key_to_merge: str, pip: bool = False
) -> None:
    value_to_merge = yaml_dict.get(key_to_merge, None)
    if value_to_merge is None:
        return

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
                package = PackageSpecifier.parse(dep)
                # Consider the channel name as part of the package name.
                # If multiple channels are specified, the package will be repeated.
                package_name = package.channel + package.name
                package_version = package.version

            # OrderedDict is used as an ordered set, the value is ignored.
            version_matchers = new_dependencies.setdefault(
                package_name, collections.OrderedDict()
            )
            if len(package_version) > 0:
                version_matchers[package_version] = None
        else:
            raise UsageError(f"Only strings and dicts are supported, got: {dep!r}")

    # keep the order of dependencies
    result: dict[str, Any] = collections.OrderedDict()
    for dep_name, dep_version_matchers in new_dependencies.items():
        if len(dep_version_matchers) > 0:
            result[dep_name + " " + ",".join(dep_version_matchers)] = None
        else:
            result[dep_name] = None

    yaml_dict[key_to_merge] = list(result.keys()) + new_dict_dependencies


@dataclass(frozen=True)
class PackageSpecifier:
    """
    A package specifiers as can be declared in a "dependencies" section, for example:

        dependencies:
        - conda-forge::pytest >=7, !=7.1.1

    This would produce PackageSpecifier("conda-forge", "pytest", ">=7, !=7.1.1".

    Note that channel and version might be "".
    """

    channel: str
    name: str
    version: str

    _PACKAGE_PATTERN = re.compile(
        # Channel is optional.
        r"^(?P<channel>[a-z0-9_\-/.]+::)?"
        # Package regex based on https://conda.io/docs/building/pkg-name-conv.html#package-naming-conventions
        r"(?P<package>[a-z0-9_\-.]+)"
        # Version.
        r"\s*(?P<version>.*)$",
        flags=re.IGNORECASE,
    )

    @classmethod
    def parse(cls, specifier: str) -> Self:
        m = re.match(cls._PACKAGE_PATTERN, specifier)
        if m is None:
            raise UsageError(
                f'The package version specification "{specifier}" do not follow the'
                " expected format."
            )
        return cls(
            channel=m.group("channel") or "",
            name=m.group("package"),
            version=m.group("version") or "",
        )


def load_yaml_dict(
    filename: Path, *, conda_platform: CondaPlatform | None = None
) -> YAMLData:
    """
    Loads the given devenv.yml file, recursively processing it, using the selectors for the given
    platform -- when not given, use the current platform.
    """
    with open(filename) as f:
        contents = f.read()

    if conda_platform is None:
        conda_platform = CondaPlatform.current()

    rendered_contents = render_jinja(
        contents, filename, is_included=False, conda_platform=conda_platform
    )

    import yaml

    root_yaml = yaml.safe_load(rendered_contents)

    all_yaml_dicts = handle_includes(filename, root_yaml, conda_platform=conda_platform)

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

    process_constraints_into_dependencies(merged_dict)
    merged_dict.pop("constraints", None)

    merge_dependencies_version_specifications(merged_dict, key_to_merge="dependencies")

    # Force these keys to always be set by the most downstream devenv file.
    # all_yaml_dicts is ordered from downstream to upstream.
    for forced_key in ("name", "channels", "platforms"):
        for yaml_dict in all_yaml_dicts.values():
            if forced_key in yaml_dict:
                merged_dict[forced_key] = yaml_dict[forced_key]
                break

    if "environment" not in merged_dict:
        merged_dict["environment"] = {}

    return merged_dict


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
        print(f"{Fore.CYAN}{' '.join(full_cmdline)}{Fore.RESET}", flush=True)

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


def _get_target_env_name(args: argparse.Namespace, conda_yaml_dict: YAMLData) -> str:
    return args.name or get_env_name_from_yaml_data(conda_yaml_dict)


def write_activate_deactivate_scripts(
    args: argparse.Namespace,
    conda_yaml_dict: YAMLData,
    env_manager: Literal["conda", "mamba"],
    env_directory: Path | None,
) -> None:
    if env_directory is None:
        env_name = _get_target_env_name(args, conda_yaml_dict)
        env_directory = get_env_directory(env_manager, env_name)
        if env_directory is None:
            raise UsageError(
                f"Could not find directory of environment '{env_name}' "
                "when trying to write activate scripts (should have been created by now)."
            )

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

    environment = conda_yaml_dict.get("environment", {})
    for filename, shell in files:
        activate_script = render_activate_script(environment, shell)
        deactivate_script = render_deactivate_script(environment, shell)

        with open(join(activate_directory, filename), "w") as f:
            f.write(activate_script)
        with open(join(deactivate_directory, filename), "w") as f:
            f.write(deactivate_script)


def get_env_name(
    args: argparse.Namespace,
    conda_yaml_dict: YAMLData,
) -> str:
    """
    :param args:
        When the user supplies the name option in the command line this namespace have a "name"
        defined with a not `None` value and this value is returned.
    :param conda_yaml_dict:
        If supplied and not `None` then `output_filename` is ignored.
    """
    if args.name:
        return args.name

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

    group = parser.add_argument_group(
        title="Locking",
        description="Options related to creating and using lockfiles. Requires conda-lock installed.",
    )
    group.add_argument(
        "--lock",
        default=False,
        action="store_true",
        help="Create one or more lock files for the environment.devenv.yml file, or other file given by '--file'.",
    )

    group.add_argument(
        "--use-locks",
        choices=["auto", "yes", "no"],
        default=os.environ.get("CONDA_DEVENV_USE_LOCKS", "auto"),
        help=(
            "How to use lock files: 'auto' will use them if available, 'yes' "
            "will try to use and fail if not available, 'no' skip lock files always. "
            "Can also be configured via CONDA_DEVENV_USE_LOCKS environment variable."
        ),
    )
    group.add_argument(
        "--update-locks",
        metavar="PACKAGE",
        action="append",
        help="Update the given package in all lock files, while still obeying the pins in the devenv.yml file. "
        "Can be passed multiple times. Pass '' (empty) to update all packages.",
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


def resolve_source_file(args: argparse.Namespace) -> Path:
    """Get and verify that the argument passed on the command-line is correct."""
    filename = Path(args.file)
    if not filename.is_file():
        raise UsageError(f'file "{filename}" does not exist.')
    return filename


def main_with_args_namespace(args: argparse.Namespace) -> int | str | None:
    if args.version:
        from conda_devenv import __version__

        print(f"conda-devenv version {__version__}")
        return 0

    os.environ.update(parse_env_var_args(args.env_var))
    env_manager = resolve_env_manager(args)

    if args.print or args.print_full:
        return print_rendered_environment(args)

    if args.lock or args.update_locks:
        return create_update_lock_file(env_manager, args)

    elif args.use_locks in ("auto", "yes"):
        try:
            return create_update_env_using_lock_file(env_manager, args)
        except LockFileNotFoundError as e:
            if args.use_locks == "yes":
                raise UsageError(
                    f"lock file {e.lock_file} not found and --use-locks=yes, aborting."
                )
        return create_update_env(env_manager, args)

    else:
        return create_update_env(env_manager, args)


def print_rendered_environment(args: argparse.Namespace) -> int:
    """
    If print_full is True, includes the 'environment' section (for environment
    variable definition), which is usually left out of the processed environment.yml
    file.
    """
    render = ProcessedEnvironment.from_file(resolve_source_file(args))
    print(render.rendered_yaml)
    if (
        args.print_full
        and render.conda_yaml_dict
        and "environment" in render.conda_yaml_dict
    ):
        print(
            render_for_conda_env(
                {"environment": render.conda_yaml_dict["environment"]}, header=""
            )
        )
    return 0


def create_update_env(
    env_manager: Literal["conda", "mamba"], args: argparse.Namespace
) -> int:
    filename = resolve_source_file(args)
    processed = ProcessedEnvironment.from_file(filename)
    if processed.is_devenv_file:
        # Write the processed contents into the equivalent environment.yml file.
        output_filename = __write_conda_environment_file(
            args, filename, processed.rendered_yaml
        )
    else:
        # Just call conda-env directly in plain environment.yml files.
        output_filename = filename

    # Call conda-env update
    if return_code := __call_conda_env_update(args, output_filename, env_manager):
        return return_code

    if processed.is_devenv_file:
        env_name = get_env_name(args, processed.conda_yaml_dict)
        env_directory = get_env_directory(env_manager, env_name)

        write_activate_deactivate_scripts(
            args,
            env_manager=env_manager,
            conda_yaml_dict=processed.conda_yaml_dict,
            env_directory=env_directory,
        )
    return 0


def _get_lock_paths(
    source: Path, env_name: str, conda_platform: CondaPlatform
) -> tuple[Path, Path]:
    base_lock_file = (
        source.parent / f".{env_name}.{conda_platform.value}.lock_environment.yml"
    )
    target_lock_file = (
        source.parent / f".{env_name}.{conda_platform.value}.conda-lock.yml"
    )
    return base_lock_file, target_lock_file


def create_update_lock_file(
    env_manager: Literal["conda", "mamba"], args: argparse.Namespace
) -> int:
    def get_required_key(name: str) -> Sequence[str]:
        try:
            return processed_env.conda_yaml_dict[name]
        except KeyError:
            raise UsageError(
                f"Locking requires key '{name}' defined in the starting devenv.yml file"
            )

    filename = resolve_source_file(args)
    processed_env = ProcessedEnvironment.from_file(filename)
    if not processed_env.is_devenv_file:
        raise UsageError("Locking requires a .devenv.yml file")
    platforms = get_required_key("platforms")
    _ = get_required_key("channels")

    env_name = _get_target_env_name(args, processed_env.conda_yaml_dict)
    for platform in platforms:
        conda_platform = CondaPlatform(platform)
        plat_render = ProcessedEnvironment.from_file(
            filename, conda_platform=conda_platform
        )
        base_lock_file, target_lock_file = _get_lock_paths(
            filename, env_name, conda_platform
        )
        header = f"# Generated by conda-devenv locking support for env {env_name} platform {platform}\n"
        base_lock_file.write_text(header + plat_render.rendered_yaml)

        if not args.quiet:
            verb = "Creating" if not base_lock_file.is_file() else "Updating"
            print(
                f"{Fore.BLUE}{verb} lock files for "
                f"{Fore.MAGENTA}{env_name}{Fore.BLUE} platform "
                f"{Fore.GREEN}{platform}{Fore.RESET}",
                flush=True,
            )

        update_args = []
        if args.update_locks:
            for name in args.update_locks:
                update_args += ["--update", name]

        cmdline_args = [
            "lock",
            "--file",
            str(base_lock_file),
            "--platform",
            platform,
            "--lockfile",
            str(target_lock_file),
            *update_args,
        ]
        if not args.quiet:
            full_cmdline = [str(env_manager), *cmdline_args]
            print(f"{Fore.CYAN}{' '.join(full_cmdline)}{Fore.RESET}", flush=True)

        if return_code := _call_conda(env_manager, cmdline_args):
            return return_code

    return 0


def create_update_env_using_lock_file(
    env_manager: Literal["conda", "mamba"], args: argparse.Namespace
) -> int:
    filename = resolve_source_file(args)
    processed_env = ProcessedEnvironment.from_file(filename)

    conda_platform = CondaPlatform.current()
    _, target_lock_file = _get_lock_paths(
        filename,
        get_env_name_from_yaml_data(processed_env.conda_yaml_dict),
        conda_platform,
    )
    if not target_lock_file.is_file():
        raise LockFileNotFoundError(target_lock_file)

    env_name = _get_target_env_name(args, processed_env.conda_yaml_dict)
    cmdline_args = ["lock", "install", "--name", env_name, str(target_lock_file)]
    env_directory = get_env_directory(env_manager, env_name)
    if not args.quiet:
        verb = (
            "Updating"
            if env_directory is not None and env_directory.is_dir()
            else "Creating"
        )
        print(
            f"{Fore.BLUE}{verb} env "
            f"{Fore.MAGENTA}{env_name}{Fore.BLUE} platform "
            f"{Fore.GREEN}{conda_platform.value}{Fore.BLUE} using lockfile{Fore.RESET}",
            flush=True,
        )

        full_cmdline = [str(env_manager), *cmdline_args]
        print(f"{Fore.CYAN}{' '.join(full_cmdline)}{Fore.RESET}", flush=True)

    if return_code := _call_conda(env_manager, cmdline_args):
        return return_code

    write_activate_deactivate_scripts(
        args,
        env_manager=env_manager,
        conda_yaml_dict=processed_env.conda_yaml_dict or {},
        env_directory=env_directory,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
