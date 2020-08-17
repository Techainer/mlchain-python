import click
import os


op_config = click.option("--config", "-c", default=None, help="file json or yaml")

@click.command("artifact", short_help="Download files from object storage to local.")
@click.argument('action', nargs=1, required=False, default=None)
@op_config
@click.option('--force/--no-force', default=False)
@click.argument('names', nargs=-1)
def artifact_command(action,config,force,names):
    from mlchain import config as mlconfig
    default_config = False
    if config is None:
        default_config = True
        config = 'mlconfig.yaml'
    if os.path.isfile(config):
        if config.endswith('.json'):
            config = mlconfig.load_json(config)
        elif config.endswith('.yaml') or config.endswith('.yml'):
            config = mlconfig.load_yaml(config)
        else:
            raise AssertionError("Not support file config {0}".format(config))
    else:
        if not default_config:
            raise FileNotFoundError("Not found file {0}".format(config))
        config = {}
    assert action in ['pull','push']
    mlconfig.artifact(action,config,force,names)