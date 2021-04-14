import logging
import multiprocessing
import os
from multiprocessing import Process, Queue
from os import getpid, kill
from signal import SIGINT
from threading import Timer
from time import sleep

multiprocessing.set_start_method("fork")

logger = logging.getLogger()


def background(runner, cli, args, new_pwd, prog_name, wait_time, q):
    Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
    os.chdir(new_pwd)
    result = runner.invoke(cli, args, prog_name=prog_name)
    q.put(('exit_code', result.exit_code))
    q.put(('output', result.output))


def test_breaking_process(runner, cli, args, new_pwd, prog_name, wait_time=10):
    q = Queue()
    # Running out app in SubProcess and after a while using signal sending
    # SIGINT, results passed back via channel/queue
    p = Process(target=background, args=(
        runner, cli, args, new_pwd, prog_name, wait_time, q))
    p.start()

    results = {}

    while p.is_alive():
        sleep(0.5)
    else:
        while not q.empty():
            key, value = q.get()
            results[key] = value
    print(results)
    logger.info('Output of `mlchain run`:\n' + results['output'])
    assert results['exit_code'] == 0


def background_2(runner, port, wait_time):
    Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
    runner.run(port=port, thread=1)


def test_breaking_process_server(runner, port, wait_time=10):
    p = Process(target=background_2, args=(runner, port, wait_time))
    p.start()
