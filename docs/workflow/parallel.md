<b> Parallel </b> processing are designed specifically to speed up your task. For instance, if you are
having a task (eg. image classification) that needs to be done 20 times, using <b> parallel </b> with 
20 threads speed that up 20 times, meaning it only take as long as processing 1 image.

## Tutorial

(Optional) For a finished tutorial for reference, find it here: https://github.com/trungATtechainer/MLChain-Full-Tutorial


Let's use our <b> get_num() </b> function from [client.py](../Client/general.md) for this task. After creating 
a new file, called <b> parallel.py</b> in the same directory, we import the important libraries. 

```python
# import mlchain workflows library
from mlchain.workflows import Parallel,Task

# import time for measurement purposes
import time

# import get_num function from client.py
from client import get_num
```
Next, download the data from <b> [here](https://drive.google.com/u/6/uc?id=1M6JsFwuPkTnGkPV0JOJYPjpB1tedKwsm&export=download) </b> and save into the same directory, under a folder called <b> data</b>. They contain the images that we will use
for our digit classification task. This should have been satisfied if you followed the <b> [pipeline](../workflow/pipeline.md) </b> guide.

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

### Test 1 (for loop)

In this test, we will test the programming using the good old for loop. In your file, paste the following code.

```python
start = time.time() # start time

# running a for loop through all the tasks
r = []
for item in img_list:
    r.append(get_num(item))
end = time.time()

# printing results and processed time
print (r)
print('Total time: ', end - start)
```
In this code, we basically run image classification for all of our images. Once that is done, it prints out
the result and the time taken.

```python
[8, 3, 3, 8, 3, 8, 3, 8, 3, 8, 3, 3, 3, 8, 3, 3, 3, 8, 8, 3, 8, 8, 8, 8]
Total time:  48.9379518032074
```

This process took us up to 49 seconds to run, which is unfavourable in most software development context.
Now, let's see how long it will take to run with parallel.

### Test 2 (run with parallel)

Remember to <b> comment </b> the previous code that we have written for test 1. Add the following to the <b> parallel.py </b> file:

```python
start = time.time() # start time

# Using Parallel
r = Parallel(
    tasks= [Task(get_num,i) for i in img_list], # listing the tasks
    max_threads=24 # no. of threads. 24 threads for 24 images to minimize run time
).run()

end = time.time() # end time

# printing result and time
print(r)
print('Total time: ', end - start)
```

In this code, we are using parallel to run our program. This is specified by the <b> Parallel() </b> instance above. 
In which, we specify the tasks that we want the computer to run, which is <b> get_num() </b>
for all images in img_list.

```python
[8, 3, 3, 8, 3, 8, 3, 8, 3, 8, 3, 3, 3, 8, 3, 3, 3, 8, 8, 3, 8, 8, 8, 8]
Total time:  2.1767709255218506
```

This process takes only approximately <b> 2 seconds </b> which is 24 times faster than our original 
test 1. This is an advantage of mlchain workflow parallel, by allowing users to 
optimize their code without having DevOps knowledge.

## Module overview:

```python
class Parallel:
    def __init__(self, tasks:[], max_threads:int=10, max_retries:int=0, 
                pass_fail_job:bool=False, verbose:bool=True, threading:bool=True):
```

### Variables:

- tasks (list): list of tasks (or functions) that you want to be completed

- max_threads (int): maximum number of threads that the computer is allowed to use (default = 10)

- max_retries (int):  (default = 0)

- pass_fail_job (bool):  (default = False)

- verbose (bool):  (default = True)

- threading (bool):  (default = True)
