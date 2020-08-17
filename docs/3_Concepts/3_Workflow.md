Workflow is an independent function of MLChain that allows you to process your function 
in a <b> parallel </b> or a <b> pipeline </b> manner. This uses multi thread processing without
the need of complex DevOps programming, allowing your app to run multiple tasks at your CPU's best ability.

## Parallel Processing

<b> Parallel </b> processing are designed specifically to speed up your task. For instance, if you are
having a task (eg. image classification) that needs to be done 20 times, using <b> parallel </b> with 
20 threads speed that up 20 times, meaning it only take as long as processing 1 image.

```python
results = Parallel(
    tasks= [Task(predict,img) for img in images], # listing the tasks
    max_threads=24 # no. of threads. 24 threads for 24 images to minimize run time
).run()
```

In the above function, we are making a direct call to the <b> predict </b> function, which takes in <b> img </b>
as its args and returns the final results.

### Task in Parallel:

Task include the functions and params needed for your application. When "Task" is called, it takes the function and the 
corresponding parameters to initiate a variety of work to be done. This is then sent to various threads and subsequently processed.

In the above example,

```python
Task(predict, img) for img in images
```

creates a variety of tasks that takes "predict" as the functions and "img" in "images" as its parameters.

### Parallel class:

```python
class Parallel:
    def __init__(self, tasks:[], max_threads:int=10, max_retries:int=0, 
                pass_fail_job:bool=False, verbose:bool=True, threading:bool=True):
```

#### Variables:

- tasks (list): list of tasks (or functions) that you want to be completed

- max_threads (int): maximum number of threads that the computer is allowed to use (default = 10)

- max_retries (int):  (default = 0)

- pass_fail_job (bool):  (default = False)

- verbose (bool):  (default = True)

- threading (bool):  (default = True)

## Pipeline Processing
<b> Pipeline </b> processing are designed to speed up your work when multiple tasks are required to be done.
For instance, if you are building an OCR system, it will have to be broken down into multiple processes 
(eg. text localization, text segmentation, text recognition). If you are processing 10 image, for instance, it will take
all of them to be processed through all these steps, drastically increase time. <b> Pipeline
</b> uses multi threads to better allocate those time, so that while you are processing <i> text segmentation </i> on image 1,
for instance, then the computer can already begin processing <i> text localization </i> on image 2, and so on.

```python
pipeline = Pipeline(
    Step(predict1, max_thread = 24),
    Step(predict2, max_thread = 12)
)

results = pipeline(*images)
```
In the above function, we are making a direct calls to the <b> predict1 </b> function and <b> predict2 </b> functions. In later analysis, these takes in images and process them with multithreading, drastically speed up the process and allowing us to build roburst applications.

### Step in Pipeline:

Step include the multiple functions that are used in your application. When "Step" is called under pipeline, it create instances that take the output of the previous function as the new function's input. You can imagine it as a neural network, where the output of the previous layers is fed on to the next layer.

In the above example,

```python
Step(predict1, max_thread = 24)
```

creates an instance of a function "predict1" among the full pipeline.

### Pipeline Class:

```python
class Pipeline:
    def __init__(self, *steps: Step):
```

#### Variables:

- *steps (Step instances): list of steps we want to execute for each instance of input.