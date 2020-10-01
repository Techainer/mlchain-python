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
        test_breaking_process(runner, cli, args='run'.split(), new_pwd='tests/dummy_server', prog_name='python -m mlchain')


def test_breaking_process(runner, cli, args, new_pwd, prog_name):
    from multiprocessing import Queue, Process
    from threading import Timer
    from time import sleep
    from os import kill, getpid
    from signal import SIGINT

    q = Queue()

    # Running out app in SubProcess and after a while using signal sending 
    # SIGINT, results passed back via channel/queue  
    def background():
        Timer(5, lambda: kill(getpid(), SIGINT)).start()
        os.chdir(new_pwd)
        result = runner.invoke(cli, args, prog_name=prog_name)
        q.put(('exit_code', result.exit_code))
        q.put(('output', result.output))

    p = Process(target=background)
    p.start()

    results = {}

    while p.is_alive():
        sleep(0.5)
    else:
        while not q.empty():
            key, value = q.get()
            results[key] = value
    logger.info('Output of `mlchain run`:\n' + results['output'])
    assert results['exit_code'] == 0