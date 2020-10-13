import copy

import pytest

from conda_devenv.devenv import (
    merge,
    merge_dependencies_version_specifications,
    separate_strings_from_dicts,
)


def test_merge_plain():
    a = {
        "name": "a",
        "dependencies": ["a_dependency",],
        "environment": {"PATH": ["a_path",]},
    }

    b = {
        "name": "b",
        "dependencies": ["b_dependency",],
        "environment": {"PATH": ["b_path"]},
        "channels": ["b_channel",],
    }

    merged_dict = merge([a, b])

    assert merged_dict == {
        "channels": ["b_channel",],
        "dependencies": ["a_dependency", "b_dependency",],
        "environment": {"PATH": ["a_path", "b_path",]},
    }


def test_merge_dependencies_with_pip():
    a = {
        "name": "a",
        "dependencies": ["a_dependency", {"pip": ["some_from_pip >=0.1",]}],
    }

    b = {
        "name": "b",
        "dependencies": ["b_dependency", {"pip": ["some_from_pip >=0.2",]}],
    }

    merged_dict = merge([a, b])

    assert merged_dict == {
        "dependencies": [
            "a_dependency",
            "b_dependency",
            {"pip": ["some_from_pip >=0.1,>=0.2",]},
        ]
    }


def test_separate_strings_from_dicts():
    assert separate_strings_from_dicts(["a", {"1": "2"}, "b", {"3": "4"}]) == (
        ["a", "b"],
        [{"1": "2"}, {"3": "4"}],
    )
    assert separate_strings_from_dicts(["a", "b"]) == (["a", "b"], [])
    assert separate_strings_from_dicts([{"1": "2"}, {"3": "4"}]) == (
        [],
        [{"1": "2"}, {"3": "4"}],
    )

    with pytest.raises(RuntimeError, match="Only strings and dicts are supported"):
        separate_strings_from_dicts([1])


def test_merge_empty_dependencies():
    """
    This happens when an environment file is declared like this:

    name: foo
    dependencies:
    {% if False %}
      - dependency
    {% endif %}
    """
    assert merge(
        [{"name": "a", "dependencies": []}, {"name": "b", "dependencies": None},]
    ) == {"dependencies": [],}

    assert merge(
        [{"name": "b", "dependencies": None}, {"name": "a", "dependencies": []},]
    ) == {"dependencies": [],}

    assert (
        merge(
            [{"name": "b", "dependencies": None}, {"name": "a", "dependencies": None},]
        )
        == {}
    )


def test_merge_dependencies_version_specifications_plain():
    merged_dict = {
        "dependencies": [
            "a_dependency==1.2.3",
            "a_dependency<=4",
            "b_dependency",
            "b_dependency=3",
        ],
    }

    merge_dependencies_version_specifications(merged_dict, key_to_merge="dependencies")

    assert merged_dict == {
        "dependencies": ["a_dependency ==1.2.3,<=4", "b_dependency =3",],
    }


def test_merge_dependencies_version_specifications_errors():
    merged_dict = {
        "dependencies": ["==1",],
    }
    with pytest.raises(
        RuntimeError, match='.*"==1" do not follow the expected format.*'
    ):
        merge_dependencies_version_specifications(
            merged_dict, key_to_merge="dependencies"
        )

    merged_dict = {
        "dependencies": [1,],
    }
    with pytest.raises(RuntimeError, match=".*Only strings and dicts are supported.*"):
        merge_dependencies_version_specifications(
            merged_dict, key_to_merge="dependencies"
        )


def test_merge_dependencies_version_specifications_pip_dependencies():
    """Regression test for issue #91, #92 and #113."""
    merged_dict = {
        "dependencies": [
            "pip",
            {
                "pip": [
                    # issue #113
                    "--editable path/to/first/package",
                    "--editable path/to/second/package",
                    # issue #118
                    "-e ./path/to/first/package",
                    "-e ./path/to/second/package",
                    # issue #92
                    "ConfigAndParse ==0.15.2",
                    # issue #91
                    "git+git@github.com:ESSS/conda-devenv.git@0.1",
                    "hg+ssh://hg@bitbucket.org/mforbes/mmfutils-fork@0.4.12",
                ]
            },
        ]
    }
    merged_dict_ = copy.deepcopy(merged_dict)
    merge_dependencies_version_specifications(merged_dict, key_to_merge="dependencies")
    assert merged_dict_ == merged_dict


def test_merge_error_can_not_merge():
    with pytest.raises(
        ValueError, match=".*because it will override the previous value.*"
    ):
        merge([{"a": "1"}, {"a": "2"}])
    with pytest.raises(ValueError, match="Found.*when a dict is expected.*"):
        merge([{"a": []}, {"a": {}}])
