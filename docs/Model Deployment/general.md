The main component of MLChain Machine Learning Model Deployment is the use of 
the ServeModel class. This class takes various function that is created by your model
(defined as class YourModel in the following code) and return the output in a web-based 
app.

This allows you to quickly deploy an app without having to build back-end software engineering 
products that might be time-consuming and cumbersome.

```python
from mlchain.base import ServeModel

class YourModel:
    def predict(self,input:str):
        '''
        function return input
        '''
        return input

model = YourModel()

serve_model = ServeModel(model)
```

To host the above model, you can simply run the command

```bash
mlchain run server.py --host localhost --port 5000
```

and your website should be hosting at http://localhost:5000

[Access full tutorial >>](../Model Deployment/tutorial.md)