<p align="center">
  <a href="https://mlchain.ml" target="_blank">
    <img src="docs/img/logo.png" target="_blank" height="80"/>
  </a><br><br>
  <i> <strong>MLChain:</strong> Auto-Magical Deploy AI model at large scale, high performance, and easy to use </i> <br>
  <a href="https://mlchain.readthedocs.io/en/latest/?" target="_blank">
  <br>
    <strong> Explore the docs » </strong>
  </a> <br>
  <a href="https://mlchain.ml" target="_blank"> Our Website </a>
    ·
  <a href="https://github.com/techainer/examples-python" target="_blank"> Examples in Python </a>
</p>


[![PyPI version](https://badge.fury.io/py/mlchain.svg)](https://badge.fury.io/py/mlchain)
[![Downloads](https://pepy.tech/badge/mlchain)](https://pepy.tech/project/mlchain)
[![Build Status](https://travis-ci.org/Techainer/mlchain-python.svg?branch=master)](https://travis-ci.org/Techainer/mlchain-python)
[![Documentation Status](https://readthedocs.org/projects/mlchain/badge/?version=latest)](https://mlchain.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Techainer/mlchain-python/blob/master/LICENSE)
</div>


MLChain is a simple, easy to use library that allows you to deploy your Machine Learning
model to hosting server easily and efficiently, drastically reducing the time required 
to build API that support an end-to-end AI product.

## Key features

- <b> Fast: </b> MLChain prioritize speed above other criteria.

- <b> Fast to code: </b> With a finished Machine Learning model, it takes 4 minutes on average 
  to deploy a fully functioning API with MLChain.

- <b> Flexible: </b> The nature of ML-Chain allows developing end-to-end adaptive, with 
  varied serializer and framework hosting at your choice.

- <b> Less debugging </b>: We get it. Humans make mistakes. With MLChain, its configuration makes debugging a lot easier and almost unnecessary.

- <b> Easy to code: </b> as a piece of cake!

- <b> Standards-based: </b> Based on the open standards for APIs: OpenAPI (previously known as Swagger), along with JSON Schema and other options.


## Installation

MLChain required Python 3.6 and above

### PyPI
To install latest stable version of MLChain, simply run:
```bash
pip install mlchain
```

![](docs/img/README/mlchain.gif)

### Build from source
If you can't wait for the next release, install the most up to date code with from `master` branch by running the following command:
```bash
git clone https://github.com/Techainer/mlchain-python
cd mlchain-python
pip install -r requirements.txt
python setup.py install
```
Or simply install using git:
```bash
pip install git+https://github.com/Techainer/mlchain-python@master --upgrade
```

## Documentation
Read ours documentation [here](https://mlchain.readthedocs.io/en/latest/?)


## Demo
Here's a minimal example of serving a dummy python class

Create a `main.py` file with:

```python
from mlchain.base import ServeModel

class Model():
    def __init__(self):
        self.ans = 10

    def predict(self):
        return self.ans

# Define model
model = Model()

# Serve model
serve_model = ServeModel(model)`

# Deploy model
if __name__ == '__main__':
    from mlchain.rpc.server.flask_server import FlaskServer
    FlaskServer(serve_model).run(port=5000,threads=12) # Run flask model with upto 12 threads
```
Now run:

```bash
python main.py
```

Now you can access your api at http://localhost:5000. So easy :D

## Examples
- Serving MNIST using MLchain: https://github.com/Techainer/mnist-mlchain-examples

## Asking for help
Welcome to the MLChain community!

If you have any questions, please feel free to:
1. [Read the docs](https://mlchain.readthedocs.io/en/latest/?)
2. [Open an issues](https://github.com/Techainer/mlchain-python/issues/new)

We are happy to help