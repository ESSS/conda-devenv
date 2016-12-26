import os

import pytest
import sys

from conda_devenv.devenv import load_yaml_dict


@pytest.fixture(autouse=True)
def load_yml_files(datadir):
    # TODO: remove this fixture when datadir finally decides to simply copy the files to the tmp directory
    datadir["a.yml"]
    datadir["b.yml"]
    datadir["c.yml"]
    datadir["a_wrong_definition_at_environment.yml"]
    datadir["b_includes_wrong_definition_at_environment.yml"]


def test_load_yaml_dict(datadir):
    conda_yaml_dict, environment = load_yaml_dict(datadir["c.yml"])
    assert set(environment.keys()) == {"PATH"}
    assert set(environment["PATH"]) == {"b_path", "a_path"}


def test_load_yaml_dict_with_wrong_definition_at_environment_key(datadir):
    filename = datadir["a_wrong_definition_at_environment.yml"]
    with pytest.raises(ValueError) as e:
        load_yaml_dict(filename)

    if sys.version_info >= (3,):
        exception_message_start = "The 'environment' key is supposed to be a dictionary, but you have the type " \
                                  "'<class 'list'>' at "
    else:
        exception_message_start = "The 'environment' key is supposed to be a dictionary, but you have the type " \
                                  "'<type 'list'>' at "
    assert exception_message_start in str(e.value)


def test_load_yaml_dict_with_wrong_definition_at_environment_key_will_add_wrong_file_to_exception_message(datadir):
    with pytest.raises(ValueError) as e:
        load_yaml_dict(datadir["b_includes_wrong_definition_at_environment.yml"])

    if sys.version_info >= (3,):
        exception_message_start = "The 'environment' key is supposed to be a dictionary, but you have the type " \
                                  "'<class 'list'>' at "
    else:
        exception_message_start = "The 'environment' key is supposed to be a dictionary, but you have the type " \
                                  "'<type 'list'>' at "

    assert exception_message_start in str(e.value)
    assert "a_wrong_definition_at_environment.yml" in str(e.value)
