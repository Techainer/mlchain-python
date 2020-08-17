"""
This code is referenced from Floyhub
https://github.com/Floydhub/floyd-cli
"""
import os
import logging

def get_color(n):
    return '\x1b[3{0}m'.format(n)

class MultiLine(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', newline=None):
        logging.Formatter.__init__(self, fmt, datefmt, style)
        self.newline = newline
        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

        self.color = {
            logging.DEBUG: get_color(WHITE),
            logging.INFO: get_color(BLUE),
            logging.WARNING: get_color(YELLOW),
            logging.ERROR: get_color(RED),
            logging.CRITICAL: get_color(RED),
        }

    def format(self, record):
        result = super().format(record)
        if self.newline:
            result = result.replace("\n", "\n{0}".format(self.newline % (record.__dict__)))
        levelname = record.levelno
        if levelname in self.color:
            result = self.color[levelname] + result + '\x1b[39m'
        return result.strip()

hand = logging.StreamHandler()
hand.setFormatter(MultiLine('[%(name)s]:[%(process)d] [%(asctime)s]-[%(levelname)s]-[%(filename)s:%(lineno)d]-%(message)s',
                            "%Y-%m-%d %H:%M:%S %z",
                            newline='[%(name)s]:[%(process)d] [%(asctime)s]-[%(levelname)s] '))
logging.basicConfig(handlers=[hand], level=logging.getLevelName(os.getenv('LOGLEVEL', 'INFO').upper()))
logger = logging.getLogger('mlchain-logger')

import traceback

import sys
from contextlib import contextmanager
import re
from traceback import StackSummary, extract_tb


def exception_handle(type, value, traceback):
    logger.error(format_exc(tb=traceback, exception=value))


@contextmanager
def except_handler():
    "Sets a custom exception handler for the scope of a 'with' block."
    sys.excepthook = exception_handle
    yield
    sys.excepthook = sys.__excepthook__


def format_exc(name='mlchain', tb=None, exception=None):
    if exception is None:
        formatted_lines = traceback.format_exc().splitlines()
    else:
        formatted_lines = []
        if tb is not None:
            for item in StackSummary.from_list(extract_tb(tb)).format():
                str_item = str(item)
                if str_item.endswith("\n"):
                    formatted_lines.append(str_item[:-1])
                else:
                    formatted_lines.append(str_item)
        formatted_lines += [x for x in re.split('(\\\\n)|(\\n)', str(exception)) if x not in ["\\n", "\n", "", None]]

    output = []
    kt = True
    last_mlchain_append = -1
    for x in formatted_lines:
        output.append(x)
    return "\n".join(output) + "\n"


