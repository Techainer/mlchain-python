## Introduction

MLChain class Client allows you to pass your Machine Learning model's output seamlessly between different 
computers, servers, and so on.

The below example uses MLChain client to make request from http://localhost:5000, that is hosted by ourselves. 
In real examples, this can be any website url which contain our model.

## Tutorial

First, follow the tutorial [here](../Model Deployment/tutorial.md) and deploy your model at http://localhost:5000, if you haven't already done so.

Next, create a file <b> client.py </b> any where on your computer. At the same time,
download <a href="https://drive.google.com/u/6/uc?id=15wqHzVhFzbusivB7eHB0jWHlA1CIE-DF&export=download" target="_blank"> <b> this </b> </a> image to that folder.

(Optional) For a finished tutorial for reference, find it here: https://github.com/trungATtechainer/MLChain-Full-Tutorial

In the <b> client.py </b> file, include the following code:

```python
from mlchain.client import Client
import cv2

image_name = '19.png' # downloaded image

def get_num(image_name):
    # tell the system to use the model currently hosting in localhost, port 5000
    model = Client(api_address='localhost:5000',serializer='json').model(check_status=False)

    # import our image
    img = cv2.imread(image_name)

    # get model response on image
    res = model.image_predict(img)

    # print result
    return res

if __name__ == '__main__':
    print(get_num(image_name))
```
You can see that in this code, first we get the name of the image that we downloaded <i> 19.png </i> as the image
that we want to test for digit recognizer. Next, we tell the <b> Client </b> class to use the model specified at localhost:5000, where
we are already hosting our model.
Next, we read the image, and pass it through the image_prediction function that we wrote [here](../Model Deployment/tutorial.md) to get out final
response, which is the number 4.

In your terminal, running 

    $ python client.py

will return "res" as the model's response. Please ensure that you are already hosting your 
app at localhost:5000 using the model deployment feature.

This results in the output of 

```json
4
```


In software development, we believe using this service allows programmers to better transfer AI models' final results and allowing 
for more cooperation between programmers. This allows you to communicate without having to build complex API systems in the company.

### Sending requests to the REST API
You can also send request to this API using the terminal.

```bash
curl -F "img=@19.png"  http://localhost:5000/call/image_predict
```

In the above example, we are having a request to the url http://localhost:5000/call/image_predict, 
where our input form is our image under variable <i> img </i> (19.png). This doesn't require you to build
a separate <b> client.py </b> file.

This also results in the output of 

```json
{"output": 4, "time": 0.0}
```

Which is our model's response for the image.