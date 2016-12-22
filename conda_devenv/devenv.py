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
    queue = {"root": root_yaml}
    visited = {}

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
                    final_dict[key].extend(value)
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
    retcode = subprocess.call(command)
    if retcode != 0:
        sys.exit(retcode)

    # TODO: Write the scripts to set/unset the environment variables


if __name__ == "__main__":
    main()
