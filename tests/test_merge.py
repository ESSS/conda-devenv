from conda_devenv.devenv import merge


def test_merge():
    a = {
        "name": "a",
        "dependencies": [
            "a_dependency",
        ],
        "environment": {
            "PATH": [
                "a_path",
            ]
        }
    }

    b = {
        "name": "b",
        "dependencies": [
            "b_dependency",
        ],
        "environment": {
            "PATH": [
                "b_path"
            ]
        },
        "channels": [
            "b_channel",
        ],
    }

    merged_dict = merge([a, b])

    assert merged_dict == {
        "channels": [
            "b_channel",
        ],
        "dependencies": [
            "a_dependency",
            "b_dependency",
        ],
        "environment": {
            "PATH": [
                "a_path",
                "b_path",
            ]
        }
    }


def test_merge_empty_dependencies():
    """
    This happens when an environment file is declared like this:

    name: foo
    dependencies:
    {% if False %}
      - dependency
    {% endif %}
    """
    assert merge([
        {"name": "a",
         "dependencies": []}
        ,
        {"name": "b",
         "dependencies": None}
        ,
    ]) == {
        "dependencies": [],
    }

    assert merge([
        {"name": "b",
         "dependencies": None}
        ,
        {"name": "a",
         "dependencies": []}
        ,
    ]) == {
        "dependencies": [],
    }

    assert merge([
        {"name": "b",
         "dependencies": None}
        ,
        {"name": "a",
         "dependencies": None}
        ,
    ]) == {}