import argparse
import os


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
    # This is a breadth-first search
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
            if key in final_dict:
                if key in keys_to_skip:
                    continue
                if isinstance(value, list):
                    final_dict[key].extend(value)
                else:
                    message = "Can't merge the key: '{key}' because it will override the previous value. " \
                              "Only lists can be merged. The type obtained was: {type}".format(key=key,
                                                                                               type=type(value))
                    raise ValueError(message)
            else:
                final_dict[key] = value
    return final_dict


def render(filename):
    with open(filename, "r") as f:
        contents = f.read()
    rendered_contents = render_jinja(contents, filename)

    import yaml
    root_yaml = yaml.load(rendered_contents)
    all_yaml_dicts = handle_includes(root_yaml)
    final_dict = merge(all_yaml_dicts)
    return yaml.dump(final_dict)


def main():
    parser = argparse.ArgumentParser(description="Work with multiple conda-environment-like yaml files in dev mode.")
    parser.add_argument("filename", nargs="?",
                        help="The environment.devenv.yml file to process.")

    parser.add_argument("--print", help="Only prints the rendered file to stdout and exits.",
                        action="store_true")

    # 0 - jinja
    # 1 - includes
    # 2 - environment

    args = parser.parse_args()

    filename = args.filename or "environment.devenv.yml"

    rendered_contents = render(filename)

    if args.print:
        print(rendered_contents)
        return

    # Write to the output file
    output_filename = filename.rstrip(".devenv.yml") + ".yml"
    if output_filename.endswith(".yml.yml"):
        raise ValueError("Can't guess the output file, please provide the output file with the --output-filename flag")

    with open(output_filename, 'w') as f:
        f.write(rendered_contents)

    # TODO: call conda env update at the generated file


if __name__ == "__main__":
    main()
