# MLConfig File

MLChain config file (mlconfig.yaml) is a powerful tool you can use to automate 
and drive various serve model in MLChain. It sits at the root directory of your 
project folder (directory where you run "mlchain init"). The config file should
be written in standard YAML syntax.

## Provide default arguments for mlchain run

Instead of having to type out all the command arguments everytime you want to serve model from MLChain CLI, you can save a set of default arguments in mlconfig.yaml. With this, all you have to type next time is just `mlchain run`.

For example, the following command:

```bash
mlchain run server.py --host localhost --port 5000 --flask --gunicorn
```

Can be simplified to just `mlchain run` if you have the following mlconfig.yml created inside project root directory:

```yaml
name: mlchain-server # name of service
entry_file: server.py # python file contains object ServeModel
host: localhost # host service
port: 5000 # port service
server: flask # option flask or grpc
wrapper: gunicorn # option None or gunicorn
gunicorn: # config apm-server if uses gunicorn wrapper
  timeout: 60
  keepalive: 60
  max_requests: 0
  threads: 1
  worker_class: 'gthread'
  umask: '0'
```

You can also override the arguments in `mlchain run` command to quickly test out a change. For example:

```bash
mlchain run --host 4000
```

is equivalent to the following with above mentioned config file:

```bash
mlchain run server.py --host localhost --port 4000 --flask --gunicorn
```
