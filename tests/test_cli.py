import os
from click.testing import CliRunner

from futurefire.cli import cli


def test_cli_load(tmpdir):
    runner = CliRunner()
    cfg = os.path.join(os.path.dirname(__file__), 'test.cfg')
    result = runner.invoke(cli, ['load', '--config_file', cfg, '--wksp', str(tmpdir)])
    assert result.exit_code == 0
    assert os.path.exists(tmpdir.join("roads.tif"))
    assert os.path.exists(tmpdir.join("roads_buf.tif"))
    assert os.path.exists(tmpdir.join("inventory.tif"))
