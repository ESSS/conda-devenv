import argparse
import os
import re
import sys
from pathlib import Path

from .gen_scripts import render_activate_script, render_deactivate_script


_selector_pattern = re.compile(r".*?#\s*\[(.*)\].*")


def preprocess_selector_in_line(line):
    x = _selector_pattern.search(line)
    if x is None:
        return line
    expr = x.group(1).strip()
    return f"{{% if {expr} %}}{line}{{% endif %}}"


def preprocess_selectors(contents):
    contents = contents.split("\n")
    lines = [preprocess_selector_in_line(line) for line in contents]
    return "\n".join(lines)


def _min_conda_devenv_version(min_version):
    """Checks that the current conda devenv version is at least the given version"""
    from distutils.version import LooseVersion
    import conda_devenv

    if LooseVersion(conda_devenv.__version__) < LooseVersion(min_version):
        msg = "This file requires at minimum conda-devenv {}, but you have {} installed.\n"
        sys.stderr.write(msg.format(min_version, conda_devenv.__version__))
        sys.stderr.write("Please update conda-devenv.\n")
        raise SystemExit(1)

    return ""


def _get_env(var_name, default=None, valid=None):
    """ Get env var value or default value and check against allowed values.

    :param str var_name:
        Name of the environment variable.
    :param Optional[str] default:
        Default value for the variable. If not specified, the method raises
        an error when the variable is not set.
    :param Optional[List[str]] valid:
        List of allowed values of the variable.
    :return: str
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


def render_jinja(contents, filename, is_included):
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


def handle_includes(root_filename, root_yaml):
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


def separate_strings_from_dicts(elements):
    """
    Receive a list of strings and dicts an returns 2 lists, one solely with string and the other
    with dicts.

    :param List[Union[str, Dict[str, str]]] elements:
    :rtype: Tuple[List[str], List[Dict[str, str]]]
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


def merge(dicts, keys_to_skip=("name",)):
    final_dict = {}

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
                    s = set()
                    s.update(target_strings)
                    s.update(new_strings)

                    merged_list = sorted(list(s))
                    merged_dict = merge(target_dicts + new_dicts)
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


def merge_dependencies_version_specifications(yaml_dict, key_to_merge, pip=False):
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

    new_dependencies = {}
    new_dict_dependencies = []
    for dep in value_to_merge:
        if isinstance(dep, dict):
            for key in dep:
                merge_dependencies_version_specifications(
                    dep, key_to_merge=key, pip=(key == "pip")
                )
            new_dict_dependencies.append(dep)
        elif isinstance(dep, str):
            if pip and ("+" in dep or ":" in dep):
                # Look for dependencies in the pip section that are
                # managed by version control.  For example:
                #   hg+ssh://hg@bitbucket.org/mforbes/mmfutils-fork@0.4.12
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


def load_yaml_dict(filename):
    with open(filename, "r") as f:
        contents = f.read()
    rendered_contents = render_jinja(contents, filename, is_included=False)

    import yaml

    root_yaml = yaml.safe_load(rendered_contents)

    all_yaml_dicts = handle_includes(filename, root_yaml)

    for filename, yaml_dict in all_yaml_dicts.items():
        environment_key_value = yaml_dict.get("environment", {})
        if not isinstance(environment_key_value, dict):
            raise ValueError(
                "The 'environment' key is supposed to be a dictionary, but you have the type "
                "'{type}' at '{filename}'.".format(
                    type=type(environment_key_value), filename=filename
                )
            )

    merged_dict = merge(all_yaml_dicts.values())

    # Force the "name" because we want to keep the name of the root yaml
    merged_dict["name"] = root_yaml["name"]

    environment = merged_dict.pop("environment", {})
    return merged_dict, environment


DEFAULT_HEADER = "# generated by conda-devenv, do not modify and do not commit to VCS\n"


def render_for_conda_env(yaml_dict, header=DEFAULT_HEADER):
    import yaml

    contents = header
    contents += yaml.dump(yaml_dict, default_flow_style=False)
    return contents


def __write_conda_environment_file(args, filename, rendered_contents):
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


def truncate_history_file(env_directory):
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
        return  # Environment does not exists, no history to truncate

    from os.path import isfile, join
    from time import time
    from shutil import copyfile

    history_filename = join(env_directory, "conda-meta", "history")
    history_backup_filename = "{}.{}".format(history_filename, time())
    if isfile(history_filename):
        copyfile(history_filename, history_backup_filename)

        with open(history_filename, "w") as history:
            history.truncate()


def _is_mamba_installed() -> bool:
    try:
        import mamba
    except ModuleNotFoundError:
        return False
    return True


def __call_conda_env_update(args, output_filename):
    env_manager = "conda"
    if not args.disable_mamba and _is_mamba_installed():
        env_manager = "mamba"

    command = [
        env_manager,
        "env",
        "update",
        "--file",
        output_filename,
    ]
    if not args.no_prune:
        command.append("--prune")
    if args.name:
        command.extend(["--name", args.name])
    if args.quiet:
        command.extend(["--quiet"])
    if args.verbose:
        command.extend(["-" + "v" * args.verbose])

    if not args.quiet:
        print("> Executing: %s" % " ".join(command))

    old_argv = sys.argv[:]
    try:
        sys.argv = command[1:] if env_manager == "conda" else command
        try:
            return _call_conda(env_manager)
        except SystemExit as e:
            return e.code
    finally:
        sys.argv = old_argv


def _call_conda(env_manager: str = "conda"):
    """
    Calls conda-env or mamba directly using its internal API. ``sys.argv``
    must already be configured at this point.

    We have this indirection here so we can mock this function during testing.
    :param env_manager: Switch to `conda` or `mamba` for a given input
    """
    if env_manager == "mamba":
        from mamba.mamba import main
    else:
        from conda_env.cli.main import main
    return main()


def write_activate_deactivate_scripts(
    args, conda_yaml_dict, environment, env_directory
):
    if env_directory is None:
        env_name = args.name or conda_yaml_dict["name"]
        env_directory = get_env_directory(env_name)
        if env_directory is None:
            raise ValueError("Couldn't find directory of environment '%s'" % env_name)

    from os.path import join

    activate_directory = join(env_directory, "etc", "conda", "activate.d")
    deactivate_directory = join(env_directory, "etc", "conda", "deactivate.d")

    if not os.path.exists(activate_directory):
        os.makedirs(activate_directory)
    if not os.path.exists(deactivate_directory):
        os.makedirs(deactivate_directory)

    if sys.platform == "win32":
        files = [("devenv-vars.bat", "cmd")]
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


def get_env_name(args, output_filename, conda_yaml_dict=None):
    """
    :param argparse.Namespace args:
        When the user supplies the name option in the command line this namespace have a "name"
        defined with a not `None` value and this value is returned.
    :param str output_filename:
        No jinja rendering is performed on this file if it is used.
    :param Optional[Dict[str,Any]] conda_yaml_dict:
        If supplied and not `None` then `output_filename` is ignored.
    """
    if args.name:
        return args.name

    if conda_yaml_dict is None:
        import yaml

        with open(output_filename, "r") as stream:
            conda_yaml_dict = yaml.safe_load(stream)

    return conda_yaml_dict["name"]


def _get_envs_dirs_from_conda():
    from conda.base.context import context

    return context.envs_dirs


def get_env_directory(env_name):
    """
    :rtype: Optional[str]
    :return: The environment path if the enviromment exists.
    """
    envs_dirs = _get_envs_dirs_from_conda()

    for directory in envs_dirs:
        env = os.path.join(directory, env_name)
        conda_meta_dir = os.path.join(env, "conda-meta")
        if os.path.isdir(conda_meta_dir):
            return os.path.normpath(env)

    return None


def parse_env_var_args(env_var_args):
    """
    :param List[str] env_var_args:
        List of arguments in the form "VAR_NAME" or "VAR_NAME=VALUE"
    :return: Dict[str,str]
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


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="Work with multiple conda-environment-like yaml files in dev mode."
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
        help="Similar to --print, but also " "includes the 'environment' section.",
        action="store_true",
    )
    parser.add_argument(
        "--no-prune", help="Don't pass --prune flag to conda-env.", action="store_true"
    )
    parser.add_argument("--output-file", nargs="?", help="Output filename.")
    parser.add_argument(
        "--disable-mamba-detection",
        action="store_true",
        default=False,
        help="Disable mamba detection. It will use just conda to manage the environemnt.",
        dest="disable_mamba",
    )
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

    args = parser.parse_args(args)

    if args.version:
        from ._version import version

        print(f"conda-devenv version {version}")
        return 0

    filename = args.file
    filename = os.path.abspath(filename)
    if not os.path.isfile(filename):
        print(f'File "{filename}" does not exist.', file=sys.stderr)
        return 1

    is_devenv_input_file = filename.endswith(".devenv.yml")
    if is_devenv_input_file:
        # update environment variables
        os.environ.update(parse_env_var_args(args.env_var))

        # render conda-devenv file
        conda_yaml_dict, environment = load_yaml_dict(filename)
        rendered_contents = render_for_conda_env(conda_yaml_dict)

        if args.print or args.print_full:
            print(rendered_contents)
            if args.print_full:
                print(render_for_conda_env({"environment": environment}, header=""))
            return 0

        # Write to the output file
        output_filename = __write_conda_environment_file(
            args, filename, rendered_contents
        )
    else:
        conda_yaml_dict = environment = None
        # Just call conda-env directly in plain environment.yml files
        output_filename = filename
        if args.print:
            with open(filename) as f:
                print(f.read())
            return 0

    env_name = get_env_name(args, output_filename, conda_yaml_dict)
    env_directory = get_env_directory(env_name)

    if not args.no_prune:
        # Truncate the history file
        truncate_history_file(env_directory)

    # Call conda-env update
    retcode = __call_conda_env_update(args, output_filename)
    if retcode:
        return retcode

    if is_devenv_input_file:
        write_activate_deactivate_scripts(
            args, conda_yaml_dict, environment, env_directory
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
