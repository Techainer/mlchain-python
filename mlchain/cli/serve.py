import os
import logging
import subprocess
import signal
import sys
import click


def sigterm_handler(nginx_pid, gunicorn_pid):
    try:
        os.kill(nginx_pid, signal.SIGQUIT)
    except OSError:
        pass
    try:
        os.kill(gunicorn_pid, signal.SIGTERM)
    except OSError:
        pass

    sys.exit(0)


def start_server(sub_command):
    if len(sub_command) == 0:
        raise Exception("Command empty")
    # link the log streams to stdout/err so they will be logged to the container logs

    nginx = subprocess.Popen(['nginx', '-c', '/etc/nginx/nginx.conf'])
    gunicorn = subprocess.Popen(sub_command)

    signal.signal(signal.SIGTERM,
                  lambda a, b: sigterm_handler(nginx.pid, gunicorn.pid))

    pids = set([nginx.pid, gunicorn.pid])
    while True:
        pid, _ = os.wait()
        if pid in pids:
            break

    sigterm_handler(nginx.pid, gunicorn.pid)
    logging.info('Inference server exiting')


@click.command("serve", short_help="Inference server.",
               context_settings={"ignore_unknown_options": True})
@click.argument('command', nargs=-1, required=True)
def serve_command(command):
    start_server(list(command))
