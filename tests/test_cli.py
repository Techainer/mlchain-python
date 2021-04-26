import logging
import unittest
import os

from click.testing import CliRunner
from mlchain.cli.main import main

logger = logging.getLogger()

class TestCLI(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.is_windows = os.name == 'nt'

    def test_mlchain_version(self):
        cli = main(is_testing=True)
        result = CliRunner().invoke(cli, args='--version'.split(), prog_name='python -m mlchain')
        logger.info('Output of `mlchain --version`:\n' + str(result.output))
        assert result.exit_code == 0

    def test_mlchain_init(self):
        cli = main(is_testing=True)
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, args='init'.split(), prog_name='python -m mlchain')
            logger.info('Output of `mlchain init`:\n' + str(result.output))
            assert result.exit_code == 0

            result = runner.invoke(cli, args='init'.split(), prog_name='python -m mlchain')
            logger.info('Output of `mlchain init` second time:\n' + str(result.output))
            assert result.exit_code == 0

    def test_mlchain_run(self):
        if self.is_windows:
            return 0
        cli = main(is_testing=True)
        runner = CliRunner()
        from .utils import test_breaking_process
        test_breaking_process(runner, cli, args='run'.split(), new_pwd='tests/dummy_server', prog_name='python3 -m mlchain')
