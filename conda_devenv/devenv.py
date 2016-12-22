import argparse
import os

import sys


def render_jinja(contents, filename):
    import jinja2
    import sys

    jinja_dict = {
        "root": os.path.dirname(os.path.abspath(filename)),
        "os": os,
        "sys": sys,
    }

    return jinja2.Template(contents).render(**jinja_dict)


def handle_includes(root_yaml):
    # This is a depth-first search
    import yaml
    import collections
    queue = collections.OrderedDict({"root": root_yaml})
    visited = collections.OrderedDict()

    while queue:
        filename, yaml_dict = queue.popitem()
        if filename in visited:
            continue

        for included_filename in yaml_dict.get("includes", []):
            with open(included_filename, "r") as f:
                jinja_contents = render_jinja(f.read(), included_filename)
            included_yaml_dict = yaml.load(jinja_contents)
            queue[included_filename] = included_yaml_dict

        if "includes" in yaml_dict:
            del yaml_dict["includes"]

        visited[filename] = yaml_dict

    return visited


def merge(dicts, keys_to_skip=('name',)):
    final_dict = {}

    for d in dicts:
        for key, value in d.items():
            if key in keys_to_skip:
                continue

            if key in final_dict:
                if isinstance(value, dict):
                    final_dict[key] = merge([final_dict[key], value])
                elif isinstance(value, list):
                    s = set()
                    s.update(final_dict[key])
                    s.update(value)
                    final_dict[key] = sorted(list(s))
                else:
                    message = "Can't merge the key: '{key}' because it will override the previous value. " \
                              "Only lists and dicts can be merged. The type obtained was: {type}"\
                        .format(
                            key=key,
                            type=type(value)
                        )
                    raise ValueError(message)
            else:
                final_dict[key] = value
    return final_dict


def load_yaml_dict(filename):
    with open(filename, "r") as f:
        contents = f.read()
    rendered_contents = render_jinja(contents, filename)

    import yaml
    root_yaml = yaml.load(rendered_contents)

    all_yaml_dicts = handle_includes(root_yaml)

    for filename, yaml_dict in all_yaml_dicts.items():
        environment_key_value = yaml_dict.get("environment", {})
        if not isinstance(environment_key_value, dict):
            raise ValueError("The 'environment' key is supposed to be a dictionary, but you have the type '{type}' at "
                             "'{filename}'.".format(type=type(environment_key_value), filename=filename))

    merged_dict = merge(all_yaml_dicts.values())

    # Force the "name" because we want to keep the name of the root yaml
    merged_dict["name"] = root_yaml["name"]

    environment = merged_dict.pop("environment", {})
    return merged_dict, environment


def render_for_conda_env(yaml_dict):
    import yaml
    return yaml.dump(yaml_dict, default_flow_style=False)


def render_activate_script(environment):
    script = []
    if sys.platform.startswith("linux"):
        script = ["#!/bin/sh"]
    for variable, value in environment.items():
        if sys.platform.startswith("linux"):
            if isinstance(value, list):
                # Lists are supposed to prepend to the existing value
                value = os.pathsep.join(value) + os.pathsep + "${variable}".format(variable=variable)

            script.append("export CONDA_DEVENV_BKP_{variable}=${variable}".format(variable=variable))
            script.append("export {variable}=\"{value}\"".format(variable=variable, value=value))

        elif sys.platform.startswith("win"):
            if isinstance(value, list):
                # Lists are supposed to prepend to the existing value
                value = os.pathsep.join(value) + os.pathsep + "%{variable}%".format(variable=variable)

            script.append("set CONDA_DEVENV_BKP_{variable}=%{variable}%".format(variable=variable))
            script.append("set {variable}=\"{value}\"".format(variable=variable, value=value))

        else:
            raise ValueError("Unknown platform")

    return '\n'.join(script)


def render_deactivate_script(environment):
    script = []
    if sys.platform.startswith("linux"):
        script = ["#!/bin/sh"]
    for variable in environment.keys():
        if sys.platform.startswith("linux"):
            script.append("export {variable}=$CONDA_DEVENV_BKP_{variable}".format(variable=variable))
            script.append("unset CONDA_DEVENV_BKP_{variable}".format(variable=variable))

        elif sys.platform.startswith("win"):
            script.append("set {variable}=%CONDA_DEVENV_BKP_{variable}%".format(variable=variable))
            script.append("set CONDA_DEVENV_BKP_{variable}=".format(variable=variable))

        else:
            raise ValueError("Unknown platform")

    return '\n'.join(script)


def __write_conda_environment_file(args, filename, rendered_contents):
    if args.output_file:
        output_filename = args.output_file
    else:
        output_filename = filename.rstrip(".devenv.yml") + ".yml"
        if output_filename.endswith(".yml.yml"):
            raise ValueError("Can't guess the output file, please provide the output file with the --output-filename "
                             "flag")

    if os.path.exists(output_filename) and not args.force:
        raise ValueError("The output file '{}' already exists and the flag --force was omitted. Refusing to override "
                         "the file.".format(output_filename))

    with open(output_filename, 'w') as f:
        f.write(rendered_contents)

    return output_filename


def __call_conda_env_update(args, output_filename):
    import subprocess
    command = [
        "conda",
        "env",
        "update",
        "--file",
        output_filename,
    ]
    if not args.no_prune:
        command.append("--prune")
    if args.name:
        command.extend(["--name", args.name])
    print("> Executing: %s" % ' '.join(command))
    return subprocess.call(command)


def __write_activate_deactivate_scripts(args, conda_yaml_dict, environment):
    import subprocess
    env_name = args.name or conda_yaml_dict["name"]
    conda_root = subprocess.check_output(["conda", "info", "--root"])
    if sys.version_info >= (3, 0, 0):
        conda_root = conda_root.decode("utf-8")
    conda_root = conda_root.strip()

    from os.path import join

    env_directory = join(conda_root, "envs", env_name)

    activate_script = render_activate_script(environment)
    deactivate_script = render_deactivate_script(environment)

    activate_directory = join(env_directory, "etc", "conda", "activate.d")
    deactivate_directory = join(env_directory, "etc", "conda", "deactivate.d")

    os.makedirs(activate_directory, exist_ok=True)
    os.makedirs(deactivate_directory, exist_ok=True)

    extension = ".bat" if sys.platform.startswith("win") else ".sh"
    with open(join(activate_directory, "devenv-vars" + extension), "w") as f:
        f.write(activate_script)
    with open(join(deactivate_directory, "devenv-vars" + extension), "w") as f:
        f.write(deactivate_script)


def main():
    parser = argparse.ArgumentParser(description="Work with multiple conda-environment-like yaml files in dev mode.")
    parser.add_argument("--file", "-f", nargs="?", help="The environment.devenv.yml file to process.")
    parser.add_argument("--name", "-n", nargs="?", help="Name of environment.")
    parser.add_argument("--print", help="Only prints the rendered file to stdout and exits.", action="store_true")
    parser.add_argument("--no-prune", help="Don't pass --prune flag to conda-env.", action="store_true")
    parser.add_argument("--output-file", nargs="?", help="Output filename.")
    parser.add_argument("--force", action="store_true", help="Overrides the output file, even if it already exists.")

    args = parser.parse_args()

    filename = args.file or "environment.devenv.yml"

    conda_yaml_dict, environment = load_yaml_dict(filename)
    rendered_contents = render_for_conda_env(conda_yaml_dict)

    if args.print:
        print(rendered_contents)
        return

    # Write to the output file
    output_filename = __write_conda_environment_file(args, filename, rendered_contents)

    # Call conda-env update
    retcode = __call_conda_env_update(args, output_filename)
    if retcode != 0:
        sys.exit(retcode)

    __write_activate_deactivate_scripts(args, conda_yaml_dict, environment)


if __name__ == "__main__":
    main()
