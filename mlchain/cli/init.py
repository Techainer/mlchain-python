import click
import os

root_path = os.path.dirname(__file__)

@click.command("init", short_help="Init base config to run server.")
@click.argument('file', nargs=1, required=False, default='mlconfig.yaml')
def init_command(file):
    if file is None:
        file = 'mlconfig.yaml'
    with open(file,'wb') as f:
        f.write(open(os.path.join(root_path,'config.yaml'),'rb').read())
