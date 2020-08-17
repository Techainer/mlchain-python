Run your project on MLChain.

### Usage
```bash
mlchain run [OPTIONS] [COMMAND]
```

### Options
| Name, shorthand | Default | Description |
| --------------- | ------- | ----------- |
| `--host <host name>` |  localhost  | API host |
| `--port <api port>` |  5000  | API port |
| `--flask/--quart` |  flask  | Web frameworks uses to run api |
| `--gunicorn/--hypercorn` |    | Api framework wrapper to protect api |
| `--mode <mode>` |    | environ |
| `--rabbit/--redis` |   | Queue framework if use Async server |
| `--config <path file config>` |  mlconfig.yaml  | Path of config file |


### Description
MLChain be used to host the model you generated as REST API. API can be used to evaluate your model over HTTP protocol.

See [serving document](../guides/serving/) for more details.

This command to serve model
### Example
```bash
$ mlchain run server.py --flask --gunicorn --host localhost --port 3456
```

{!contributing.md!}
