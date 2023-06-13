from pathlib import Path


def test_truncate_history_file_backups_file(mocker, tmp_path: Path) -> None:
    import textwrap

    history = textwrap.dedent(
        r"""\
        ==> 2018-06-01 10:58:59 <==
        # cmd: D:\Miniconda\Scripts\conda create -n devenv --file requirements_dev.txt
        +mirror-conda-forge::argh-0.26.2-py36_1
        +mirror-conda-forge::bumpversion-0.5.3-py36_0
        +mirror-conda-forge::pathtools-0.1.2-py36_0
    """
    )
    history_file = tmp_path.joinpath("conda-meta", "history")
    history_file.parent.mkdir(parents=True)
    history_file.write_text(history)
    mocker.patch("time.time", return_value=123)

    from conda_devenv.devenv import truncate_history_file

    truncate_history_file(tmp_path)

    backup = tmp_path.joinpath("conda-meta", "history.123")
    assert backup.read_text() == history
    assert history_file.read_text() == ""


def test_truncate_history_file_ignores_missing(mocker, tmp_path: Path) -> None:
    conda_meta_dir = tmp_path.joinpath("conda-meta")
    conda_meta_dir.mkdir()  # Just meta folder no history.
    from conda_devenv.devenv import truncate_history_file

    truncate_history_file(tmp_path)
    # Truncate should not raise.
