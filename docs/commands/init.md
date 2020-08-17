Initialize a MLChain config.

### Usage
```bash
mlchain init CONFIG_FILE_NAME
```

### Options
| File name | Default | Description |
| --------------- | ------- | ----------- |
| CONFIG_FILE_NAME    | mlconfig.yaml | Name of config file |

### Description

This command creates a config file.

### Example
Initialize a mlchain config in your project directory.
```bash
$ cd /code/project
$ mlchain init mlconfig.yaml
File "mlconfig.yaml" is created in current directory
```

Example a file config
```yaml
name: mlchain-server # name of service
entry_file: server.py # python file contains object ServeModel
host: localhost # host service
port: 2222 # port service
server: flask # option flask or quart or grpc
trace: False # option True or False
queue: None # option None or rabbit or redis
wrapper: None # option None or gunicorn or hypercorn
log: False  # rate samples log
monitor_sampling_rate: 1.0
cors: true
artifact:
  - url: 'http://localhost:9000'  # if None use info object storage
    access_key: minioKey    # if None use info object storage
    secret_key: minioSecret   # if None use info object storage
    bucket: mlchain-model # if None use info object storage
    mapping:
      - from: 'models/model.pb'  # key object_storage
        to: 'models/model.pb'   # path local
gunicorn: # config apm-server if uses gunicorn wrapper
  timeout: 60
  keepalive: 60
  max_requests: 0
  threads: 1
  worker_class: 'gthread'
  umask: '0'
hypercorn: # config apm-server if uses hypercorn wrapper
  keep_alive_timeout: 60
  worker_class: 'asyncio'
  umask: 0

elastic_apm: # config apm-server if uses trace
  server_url: 'http://localhost:8200' # if None read from environ ELASTIC_APM_SERVER_URL

rabbit: # config rabbit queue if uses queue
  host: localhost # if None read from environ RABBIT_HOST
  port: 5672 # if None read from environ RABBIT_PORT

# change minio to object_storage
object_storage: # config minio if uses queue
  provider: minio # AWS, GCS, OSS, DG, Linode, Vutr, OpenStack, vv
  url: 'http://localhost:9000' # if None read from environ OBJECT_STORAGE_URL
  access_key: minioKey # if None read from environ OBJECT_STORAGE_ACCESS_KEY
  secret_key: minioSecret # if None read from environ OBJECT_STORAGE_SECRET_KEY
  bucket: mlchain-storage # if None read from environ OBJECT_STORAGE_BUCKET

elastic_search: # config elastic search if use queue
  host: localhost # if None read from environ ELASTIC_SEARCH_HOST
  port: 9200 # if None read from environ ELASTIC_SEARCH_PORT

logstash: # config logstash if use log
  host: localhost # if None read from environ LOGSTASH_HOST
  port: 5000 # if None read from environ LOGSTASH_PORT

redis: # config redis if use queue redis
  host: localhost # if None read from environ REDIS_HOST
  port: 6379 # if None read from environ REDIS_PORT
  db: 0 # if None read from environ REDIS_DB
  password: '' # if None read from environ REDIS_PASSWORD

mode:
  default: dev  # running mode
  env:   # set of mode env
    default: {}   # environ default
    dev: {} # environ by mode
    prod: {} # environ by mode

```
