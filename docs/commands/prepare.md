Download data from storage.

### Usage
```bash
mlchain prepare CONFIG_FILE_NAME [OPTIONS]
```

### Options
| File name | Default | Description |
| --------------- | ------- | ----------- |
| `CONFIG_FILE_NAME`    | mlconfig.yaml | Name of config file |
| `--force/--no-force`    | `--no-force` | Force download if exists file |

### Description

This command download file from object storage in artifact config

### Example
Download file in config
```bash
$ mlchain prepare mlconfig.yaml
```

Example a file config
```yaml
artifact:
  - url: 'http://localhost:9000'  # if None use info object storage
    access_key: minioKey    # if None use info object storage
    secret_key: minioSecret   # if None use info object storage
    bucket: mlchain-model # if None use info object storage
    mapping:
      - from: 'models/model.pb'  # key object_storage
        to: 'models/model.pb'   # path local
```
