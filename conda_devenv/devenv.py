import argparse
import os


def render_jinja(content, filename):
    import jinja2
    import sys

    jinja_dict = {
        "root": os.path.dirname(os.path.abspath(filename)),
        "os": os,
        "sys": sys,
    }

    return jinja2.Template(content).render(**jinja_dict)


def main():
    parser = argparse.ArgumentParser(description="Work with multiple conda-environment-like yaml files in dev mode.")
    parser.add_argument("filename", nargs="?",
                        help="The environment.devenv.yml file to process.")

    # parser.add_argument("--force-env", "-f", help="Force re-creation of the environment, even if it already exists.",
    #                     action="store_true")

    # 0 - jinja
    # 1 - includes
    # 2 - environment

    args = parser.parse_args()

    filename = args.filename or "environment.devenv.yml"

    output_filename = filename.rstrip(".devenv.yml") + ".yml"
    if output_filename.endswith(".yml.yml"):
        raise ValueError("Can't guess the output file, please provide the output file with the --output-filename flag")

    # Render jinja
    with open(filename, "r") as f:
        contents = f.read()

    rendered_contents = render_jinja(contents, filename)

    with open(output_filename, 'w') as f:
        f.write(rendered_contents)


if __name__ == "__main__":
    main()
