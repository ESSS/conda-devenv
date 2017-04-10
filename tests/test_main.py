from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import textwrap

import pytest
from conda_devenv import devenv


@pytest.fixture
def patch_conda_calls(mocker):
    """
    Patches all necessary functions so that we can do integration testing without actually calling
    conda.
    """
    mocker.patch.object(devenv, '_call_conda', autospec=True, return_value=0)
    mocker.patch.object(devenv, 'write_activate_deactivate_scripts', autospec=True)


@pytest.mark.parametrize('input_name, expected_output_name', [
    ('environment.devenv.yml', 'environment.yml'),
    ('environment.yml', 'environment.yml'),
])
@pytest.mark.usefixtures('patch_conda_calls')
def test_handle_input_file(tmpdir, input_name, expected_output_name):
    """
    Test how conda-devenv handles input files: devenv.yml and pure .yml files.
    """
    argv = []
    def call_conda_mock():
        argv[:] = sys.argv[:]
        return 0

    devenv._call_conda.side_effect = call_conda_mock
    
    filename = tmpdir.join(input_name)
    filename.write(textwrap.dedent('''\
        name: a
        dependencies:
          - a_dependency
    '''))
    assert devenv.main(['--file', str(filename), '--quiet']) == 0
    assert devenv._call_conda.call_count == 1
    cmdline = 'env update --file {} --prune --quiet'.format(tmpdir.join(expected_output_name))
    assert argv == cmdline.split()


@pytest.mark.parametrize('input_name', ['environment.devenv.yml', 'environment.yml'])
@pytest.mark.usefixtures('patch_conda_calls')
def test_print(tmpdir, input_name, capsys):
    """
    Test --print option for different types of inputs.
    """
    filename = tmpdir.join(input_name)
    filename.write(textwrap.dedent('''\
        name: a
        dependencies:
          - a_dependency
    '''))
    assert devenv.main(['--file', str(filename), '--quiet', '--print']) == 0
    out, err = capsys.readouterr()
    assert 'dependencies:' in out
    assert 'name: a' in out


@pytest.mark.usefixtures('patch_conda_calls')
def test_print_full(tmpdir, capsys):
    """
    Test --print option for different types of inputs.
    """
    filename = tmpdir.join('environment.devenv.yml')
    filename.write(textwrap.dedent('''\
        name: a
        dependencies:
          - a_dependency
        environment:
          PYTHONPATH: {{ root }}/source
    '''))
    assert devenv.main(['--file', str(filename), '--quiet', '--print-full']) == 0
    out, err = capsys.readouterr()
    assert err == ''
    assert 'dependencies:' in out
    assert 'name: a' in out
    assert 'environment:' in out
    assert 'PYTHONPATH:' in out

