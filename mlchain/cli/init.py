import os
import click
from mlchain import logger

root_path = os.path.dirname(__file__)


@click.command("init", short_help="Init base config to run server.")
@click.argument('file', nargs=1, required=False, default='mlconfig.yaml')
def init_command(file):
    if file is None:
        file = 'mlconfig.yaml'  # pragma: no cover
    if os.path.exists(file):
        logger.warning("File {} exists. Please change name file".format(file))
    else:
        with open(file, 'wb') as fp:
            with open(os.path.join(root_path, 'config.yaml'), 'rb') as fr:
                fp.write(fr.read())
