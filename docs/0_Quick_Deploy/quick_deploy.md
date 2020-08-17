# Deploy your model in 20 seconds

Implement our model

```python

class Model:
    def _init__(self):
        self.model = torch.load(...)
    
    def predict(self, img:nd.array):
        return self.model(img)
    
    def predict_batch(self, imgs:List(nd.array)):
        return self.model(img for img in imgs)
```

### Deploy with Python/Flask (bad)

```python
import flask
import json
import time

app = flask.Flask(__name__)
app.config["DEBUG"] = True

model = Model()

@app.route('/predict/<img>', methods=['GET'])
def predict(img):
    start = time.time()
    ans = model.predict(img)
    total_time = time.time() - start
    final_return = {'Time': total_time, 'result': ans}
    return json.dump(final_return)

@app.route('/predict/<imgs>', methods=['POST', 'GET'])
def predict_batch(imgs):
    final_return = []
    for img in imgs:
        start = time.time()
        ans = model.predict(img)
        total_time = time.time() - start
        final_dict = {'Time': total_time, 'result': ans}
        final_return.append(final_dict)
    return json.dump(final_return)

app.run()
```

### Deploy with MLChain (good)

```python
from mlchain.base import ServeModel 
model = Model()
serve_model = ServeModel(model)
```

On top of that, 