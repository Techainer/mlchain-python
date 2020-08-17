The main component of the ML-Chain library is the deployment of API effortlessly, 
customizable depending on developers' specification. This allows AI products to be scaled 
quickly, fostering better communication between various procedures.


## 1. Base Model

ML-Chain main function is the ServeModel class. This is essentially a wrapper, that
 takes various function created by your model and return the output in a web-based 
app.

This allows you to quickly deploy an app without having to build back-end software engineering 
products that might be time-consuming and cumbersome.

```python
from mlchain.base import ServeModel

class YourModel:
    def predict(self,input:str):
        '''
        function return output from input
        '''
        return output

model = YourModel()

serve_model = ServeModel(model)
```

To host the above model, you can simply run the command

```bash
mlchain run server.py --host localhost --port 5000
```

and your website should be hosting at http://localhost:5000

The definition of the ServeModel class is as followed:

```
class ServeModel(object):
    def __init__(self, model, name=None, deny_all_function=False, 
    blacklist=[], whitelist=[]):
```

#### Variables:

- model (instance): The model instance that you defined, including the model itself and 
accompanying function (eg. predict)

- deny_all_function (bool): Do not return any route, except for those in whitelist
(default: False)

- blacklist (list): list of functions that are not used. Use with deny_all_function == False.

- whitelist (list): list of functions that are always used. Use with deny_all_function == True.

## 2. Flexible configuration:

Mlchain comes with a configuration file that allows you to customize your api whatever way you wanted. 

One you have finished building your model, run 

```bash
mlchain init
```
This should create a <b> mlconfig.yml </b> file, which we will use to build our main API. 


```yaml
name: mlchain-server # name of service
entry_file: server.py # python file contains object ServeModel
host: localhost # host service
port: 5000 # port service
server: flask # server option flask or grpc 
wrapper: gunicorn # wrapper option None or gunicorn
gunicorn: # config gunicorn wrapper
  timeout: 60 # max time limit for the server to process
  keepalive: 60 # The number of seconds to wait for requests on a Keep-Alive connection.
  max_requests: 0 # The maximum number of requests a worker will process before restarting.
  threads: 1 # number of threads
  worker_class: 'gthread'
  umask: '0'# A bit mask for the file mode on files written by Gunicorn.
```

Let's go through each option and see what each one does:

#### name:
```--name```

This is the name to easily identify your API service and what it does.

#### entry_file:
```[ENTRY-FILE]```

File which contain your model (and its predict function).

#### host:
```--host STRING```

Host address.

#### port:
```--port INT```

Port to serve on.

#### server:
```--server STRING```

Type of server to run. Currently we support flask or grpc.

#### wrapper:
```--wrapper STRING```

Wrapper for server.

#### gunicorn - Specific setting:

- <b> timeout:</b> Workers silent for more than this many seconds are killed and restarted.
- <b> keepalive:</b> The number of seconds to wait for requests on a Keep-Alive connection.
- <b> max_requests:</b> The maximum number of requests a worker will process before restarting.
- <b> threads:</b> The number of worker threads for handling requests.
- <b> worker_class:</b> The type of workers to use.
- <b> umask:</b> A bit mask for the file mode on files written by Gunicorn.


When you are done configurating, run

```
mlchain run
```

to deplopy your API.

## 3. Serializer:

ML-Chain server function provides 3 main serializer options that allows developers to decide 
how their packages can be sent and received. These includes:

#### Json:
Json is arguably the most common and user-friendly data package. It is easy to read json and allows 
developer to quickly navigate what they need to find. Developers can also directly make changes to json files.
However, json packages comes with a small cost of needing extra storage and takes longer to send.

#### Message Pack:

Message Pack (msgpack) is a data package that deliver data similarly to 
json, but it is lighter and takes less storage. However, they are also more heavy compared to msgpackblosc, and 
they are not as user friendly as json.

#### Message Pack Blosc:
Message Pack Blosc (msgpackblosc) is a compacted version of the original message pack. This is similar to that of your ".zip" file,
which is a lot lighter than the other 2, but takes more computation power as it requires the computer to pack and unpack 
the data package at both ends. 

Depending on our systems and use cases, we can simply pick the best serializer for our purposes. 