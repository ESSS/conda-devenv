from __future__ import absolute_import, division, print_function, unicode_literals


def test_truncate_history_file_backups_file(mocker, tmpdir):
    import textwrap
    history = textwrap.dedent('''\
        ==> 2018-06-01 10:58:59 <==
        # cmd: D:\Miniconda\Scripts\conda create -n devenv --file requirements_dev.txt
        +mirror-conda-forge::argh-0.26.2-py36_1
        +mirror-conda-forge::bumpversion-0.5.3-py36_0
        +mirror-conda-forge::pathtools-0.1.2-py36_0
    ''')
    history_file = tmpdir.join('conda-meta', 'history')
    history_file.ensure()
    history_file.write(history)
    mocker.patch('time.time', return_value=123)

    from conda_devenv.devenv import truncate_history_file
    truncate_history_file(str(tmpdir))

    backup = tmpdir.join('conda-meta', 'history.123')
    assert backup.read() == history
    assert history_file.read() == ''


def test_truncate_history_file_ingores_missing(mocker, tmpdir):
    conda_meta_dir = tmpdir.join('conda-meta')
    conda_meta_dir.ensure(dir=True)  # Just meta folder no history.
    from conda_devenv.devenv import truncate_history_file
    truncate_history_file(str(tmpdir))
    # Truncate should not raise.
