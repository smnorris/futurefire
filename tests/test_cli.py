import os
from click.testing import CliRunner

from futurefire.cli import cli


def test_cli_load(tmpdir):
    runner = CliRunner()
    cfg = os.path.join(os.path.dirname(__file__), 'test_config.cfg')
    result = runner.invoke(cli, ['load', '--config_file', cfg])
    assert result.exit_code == 0
    wksp = os.path.join(os.path.dirname(__file__), 'tempdata')
    assert os.path.exists(wksp)
    assert os.path.exists(os.path.join(wksp, "roads.tif"))
    assert os.path.exists(os.path.join(wksp, "inventory.tif"))
    assert os.path.exists(os.path.join(wksp, "roads_buf.tif"))


