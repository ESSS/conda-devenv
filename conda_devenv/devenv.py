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

    return visited.values()


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
    merged_dict = merge(all_yaml_dicts)

    # Force the "name" because we want to keep the name of the root yaml
    merged_dict["name"] = root_yaml["name"]

    environment = merged_dict.pop("environment", {})
    return merged_dict, environment


def render_for_conda_env(yaml_dict):
    import yaml
    return yaml.dump(yaml_dict, default_flow_style=False)


def render_activate_script(environment):
    script = "#!/bin/sh"
    for variable, value in environment.items():
        if isinstance(value, list):
            value = os.pathsep.join(value)
        script += "export CONDA_DEVENV_BKP_{variable}=${variable}\n".format(variable={variable})
        script += "export {variable}={value}\n".format(variable={variable}, value={value})
    return script


def render_deactivate_script(environment):
    script = ""
    for variable in environment.keys():
        script += "export {variable}=$CONDA_DEVENV_BKP_{variable}\n".format(variable={variable})
        script += "unset CONDA_DEVENV_BKP_{variable}\n".format(variable={variable})
    return script


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

    from os.path import join

    print("env_name: %s" % env_name)
    env_directory = join(conda_root, "envs", env_name)

    activate_script = render_activate_script(environment)
    deactivate_script = render_deactivate_script(environment)

    activate_directory = join(env_directory, "etc", "activate.d")
    deactivate_directory = join(env_directory, "etc", "deactivate.d")

    os.makedirs(activate_directory)
    os.makedirs(deactivate_directory)

    extension = ".bat" if sys.platform.startswith("win") else ".sh"
    with open(join(activate_directory, "devenv-vars" + extension), "w") as f:
        f.write(activate_script)
    with open(join(deactivate_directory, "devenv-vars" + extension), "w") as f:
        f.write(deactivate_script)


def main():
    parser = argparse.ArgumentParser(description="Work with multiple conda-environment-like yaml files in dev mode.")
    parser.add_argument("--file", "-f", nargs="?",
                        help="The environment.devenv.yml file to process.")

    parser.add_argument("--name", "-n", nargs="?",
                        help="Name of environment.")

    parser.add_argument("--print", help="Only prints the rendered file to stdout and exits.",
                        action="store_true")

    parser.add_argument("--no-prune", help="Don't pass --prune flag to conda-env.",
                        action="store_true")

    parser.add_argument("--output-file", help="Output filename.",
                        default="environment.yml")

    args = parser.parse_args()

    filename = args.file or "environment.devenv.yml"

    conda_yaml_dict, environment = load_yaml_dict(filename)
    rendered_contents = render_for_conda_env(conda_yaml_dict)

    if args.print:
        print(rendered_contents)
        return

    # Write to the output file
    if args.output_file:
        output_filename = args.output_file
    else:
        output_filename = filename.rstrip(".devenv.yml") + ".yml"
        if output_filename.endswith(".yml.yml"):
            raise ValueError("Can't guess the output file, please provide the output file with the --output-filename "
                             "flag")

    with open(output_filename, 'w') as f:
        f.write(rendered_contents)

    # Call conda-env update
    retcode = __call_conda_env_update(args, output_filename)
    if retcode != 0:
        sys.exit(retcode)

    __write_activate_deactivate_scripts(args, conda_yaml_dict, environment)


if __name__ == "__main__":
    main()
