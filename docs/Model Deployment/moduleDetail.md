```
class ServeModel(object):

    def __init__(self, model, name=None, deny_all_function=False, 
    blacklist=[], whitelist=[]):
```

### Variables:

- model (instance): The model instance that you defined, including general architecture and 
accompanying function

- deny_all_function (bool): Do not return any route, except for those in whitelist
(default: False)

- blacklist (list): list of functions that are not used. Use with deny_all_function == False.

- whitelist (list): list of functions that are always used. Use with deny_all_function == True.

### Example use:

Case 1: deny_all_function == False, blacklist == [], whitelist == []

```python
# serve model
serve_model = ServeModel(model)
```

return:
![image](../img/Model%20Deployment/allDefault.jpg)

Case 2: deny_all_function == False, blacklist == ['blacklist1', 'blacklist2']

```python
# serve model
serve_model = ServeModel(model, blacklist = ['model', 'transform'])
```

return: 
![image](../img/Model%20Deployment/blackList.jpg)

Case 3: deny_all_function == True, whitelist == ['model', 'image_predict']

```python
# serve model
serve_model = ServeModel(model, deny_all_function = True, whitelist = ['model', 'image_predict'])
```

return:
![image](../img/Model%20Deployment/whiteList.jpg)

[Client Sharing >>](../Client/general.md)