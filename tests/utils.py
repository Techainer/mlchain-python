import logging
import os
from multiprocessing import Process, Queue
from os import getpid, kill
from signal import SIGINT
from threading import Timer
from time import sleep
import time

logger = logging.getLogger()


def background(runner, cli, args, new_pwd, prog_name, wait_time, q):
    Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
    Timer(wait_time+1, lambda: kill(getpid(), SIGINT)).start()
    Timer(wait_time+2,lambda: kill(getpid(), SIGINT)).start()
    os.chdir(new_pwd)
    result = runner.invoke(cli, args, prog_name=prog_name)
    q.put(('exit_code', result.exit_code))
    q.put(('output', result.output))


def test_breaking_process(runner, cli, args, new_pwd, prog_name, wait_time=10, total_alive_time=60):
    q = Queue()
    # Running out app in SubProcess and after a while using signal sending
    # SIGINT, results passed back via channel/queue
    p = Process(target=background, args=(
        runner, cli, args, new_pwd, prog_name, wait_time, q))
    st = time.time()
    p.start()

    results = {}
    terminated = False
    while p.is_alive():
        sleep(0.5)
        ttl = time.time() - st
        if ttl > total_alive_time:
            p.terminate()
            try:
                p.kill()
            except Exception:
                pass
            terminated = True
            q.put(('exit_code', 9))
            q.put(('output', "Process was terminated after running for too long"))
    else:
        while not q.empty():
            key, value = q.get()
            results[key] = value
    if not terminated:
        logger.info('=========================\nOutput of `' + prog_name + ' run` at dir: ' +
                    new_pwd + ':\n' + results['output'] + '\n' + '=========================')


def background_2(runner, port, wait_time):
    Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
    Timer(wait_time+1, lambda: kill(getpid(), SIGINT)).start()
    Timer(wait_time+2, lambda: kill(getpid(), SIGINT)).start()
    runner.run(port=port, thread=1)


def test_breaking_process_server(runner, port, wait_time=10):
    p = Process(target=background_2, args=(runner, port, wait_time))
    p.start()
    p.join()
    assert p.exitcode in [0, 1]
