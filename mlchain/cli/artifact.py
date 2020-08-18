import os
import click
from mlchain.storage.object_storage import ObjectStorage
from mlchain import config as mlconfig

op_config = click.option("--config", "-c", default=None, help="file json or yaml")


@click.command("artifact", short_help="Download files from object storage to local.")
@click.argument('action', nargs=1, required=False, default=None)
@op_config
@click.option('--force/--no-force', default=False)
@click.argument('names', nargs=-1)
def artifact_command(action, config, force, names):
    default_config = False
    if config is None:
        default_config = True
        config = 'mlconfig.yaml'
    if os.path.isfile(config):
        data = mlconfig.load_file(config)
        if data is None:
            raise AssertionError("Not support file config {0}".format(config))
    else:
        if not default_config:
            raise FileNotFoundError("Not found file {0}".format(config))
        data = {}
    assert action in ['pull', 'push']
    if 'artifact' in data:
        artifact = data['artifact']

        for source in artifact:
            storage = ObjectStorage(bucket=source.get('bucket', None),
                                    url=source.get('url', None),
                                    access_key=source.get('access_key'),
                                    secret_key=source.get('secret_key', None),
                                    provider=source.get('provider', None))
            for download in source.get('mapping', []):
                d_remote = download.get('remote', None)
                d_local = download.get('local', None)
                d_type = download.get('type', None)
                bucket = download.get('bucket', None)
                d_name = download.get('name', None)
                if d_remote is not None and d_local is not None and d_type is not None \
                        and (d_name is None or names is None or len(names) == 0 or d_name in names):
                    if action == 'pull':
                        if force or not os.path.exists(d_local):
                            if d_type == 'file':
                                storage.download_file(d_remote, d_local, bucket)
                            elif d_type == 'folder':
                                storage.download_dir(d_remote, d_local, bucket)
                            else:
                                raise Exception('artifact type is file or folder')
                    elif action == 'push':
                        if d_type == 'file':
                            storage.upload_file(d_local, d_remote, bucket, overwrite=force)
                        elif d_type == 'folder':
                            storage.upload_dir(d_local, d_remote, bucket)
                        else:
                            raise Exception('artifact type is file or folder')
    else:
        raise Exception("Not found artifact in config")
