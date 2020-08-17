<b> Pipeline </b> processing are designed to speed up your work when multiple tasks are required to be done.
For instance, if you are building an OCR system, it will have to be broken down into multiple processes 
(eg. text localization, text segmentation, text recognition). If you are processing 10 image, for instance, it will take
all of them to be processed through all these steps, drastically increase time. <b> Pipeline
</b> uses multi threads to better allocate those time, so that while you are processing <i> text segmentation </i> on image 1,
for instance, then the computer can already begin processing <i> text localization </i> on image 2, and so on.

## Tutorial

(Optional) For a finished tutorial for reference, find it here: https://github.com/trungATtechainer/MLChain-Full-Tutorial


Let's use our get_num() function from [client.py](../Client/general.md) for this task. After creating a new file,
called pipeline.py in the same directory, we import the important libraries.

First, import the necessary libraries. 

```python
# mlchain Pipeline 
from mlchain.workflows.pipeline import Pipeline,Step

# time for measurement purposes
import time

# import get_num function from client.py
from client import get_num
```

Next, download the data from <b> [here](https://drive.google.com/u/6/uc?id=1M6JsFwuPkTnGkPV0JOJYPjpB1tedKwsm&export=download) </b> and save into the same directory, under a folder called <b> data</b>. They contain the images that we will use
for our digit classification task. This should have been satisfied if you followed the <b> [parallel](../workflow/parallel.md) </b> guide.

After downloading the images, we create a name list of images that we want to process.

```python
# create list of images
img_list = ['17.png', '18.png', '30.png', '31.png', '32.png', '41.png', 
            '44.png', '46.png', '51.png', '55.png', '63.png', '68.png',
            '76.png', '85.png', '87.png', '90.png', '93.png', '94.png',
            '97.png', '112.png', '125.png', '137.png', '144.png', 
            '146.png'] # contains 24 images

for i in range(len(img_list)):
    img_list[i] = 'data/' + img_list[i] # specify PATH toward images
```

We also create another function <b> get_square()</b>, that takes the input x and return its square. 
For demonstration purpose, we introduce <b> time.sleep(1) </b> in this function. This will represents 
another AI function, for instance, that takes approximately 1 second after the first, original digit recognition step.

```python
def get_square(x):
    time.sleep(1)
    return x**2
```

### Test 1: Using for loop

In this test, we will test the programming using the good old for loop. In your file, paste the following code.

```python
# traditional approach
start = time.time() #start time

# run a for loop through both function and return result
r = []
for item in img_list:
    number = get_num(item) # get number from image (~2s)
    square_num = get_square(number) # get square (~1s)
    r.append(square_num)

end = time.time() # end time

print(r) # print results
print('Total time: ', end - start)
```

This code basically goes through the two functions above (<b>get_num()</b> and <b>get_square()</b>) for each image at a time.

```python
[64, 9, 9, 64, 9, 64, 9, 64, 9, 64, 9, 9, 9, 64, 9, 9, 9, 64, 64, 9, 64, 64, 64, 64]
Total time:  72.85201978683472
```

As predicted, since each image takes 2s to determine the digit and an additional 1 
second to process <b> get_square()</b>, it takes us a total of ~72 seconds to run.

Now, let's do the same thing using <b> pipeline </b>

### Test 2: Using pipeline

Remember to <b> # comment </b> the previous code that we have written for test 1. Add 
the following to the <b> pipeline.py </b> file:

```python
start = time.time() # start time

# pipeline architecture
pipeline = Pipeline(
    Step(get_num, max_thread = 24),
    Step(get_square, max_thread = 12)
)

#print results
r = pipeline(*img_list) # get results (* since input has to be multiple values)
end = time.time() # end time

print(r)
print('Total time: ', end - start)
```

This code takes the class <b> pipeline </b> to run our program. As we passes through class <b> pipeline </b> 
the different steps for the get_num() and get_square() function, it can begin to process on <i> image 2 </i>
even if we haven't finished processing <i> image 1. </i>

```python
[64, 9, 9, 64, 9, 64, 9, 64, 9, 64, 9, 9, 9, 64, 9, 9, 9, 64, 64, 9, 64, 64, 64, 64]
Total time:  3.1787729263305664
```

This <b> pipeline </b> class thus allows you to build your products more effectively.

## Module overview:

```python
class Pipeline:
    def __init__(self, *steps: Step):
```

### Variables:

- *steps (Step instances): list of steps we want to execute for each instance of input.