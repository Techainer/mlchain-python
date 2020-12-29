import click
import os

root_path = os.path.dirname(__file__)

@click.command("init", short_help="Init base config to run server.")
def init_command():
    def create_file(file): 
        with open(file, 'wb') as f:
            f.write(open(os.path.join(root_path, file), 'rb').read())

    ALL_INIT_FILES = ['mlconfig.yaml', 'mlchain_server.py']
    for file in ALL_INIT_FILES:
        if os.path.exists(file): 
            if click.confirm('File {0} is exist, Do you want to force update?'.format(file)):
                create_file(file)
        else: 
            create_file(file)

    click.secho('Mlchain initalization is done!', blink=True, bold=True)