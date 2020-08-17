Workflow is an independent function of MLChain that allows you to process your function 
in a <b> parallel </b> or a <b> pipeline </b> manner. This uses multi thread processing without
the need of complex DevOps programming, allowing your app to run multiple tasks at your CPU's best ability.

### Parallel Processing

<b> Parallel </b> processing are designed specifically to speed up your task. For instance, if you are
having a task (eg. image classification) that needs to be done 20 times, using <b> parallel </b> with 
20 threads speed that up 20 times, meaning it only take as long as processing 1 image.

[View full tutorial >>](../workflow/parallel.md)

### Pipeline Processing
<b> Pipeline </b> processing are designed to speed up your work when multiple tasks are required to be done.
For instance, if you are building an OCR system, it will have to be broken down into multiple processes 
(eg. text localization, text segmentation, text recognition). If you are processing 10 image, for instance, it will take
all of them to be processed through all these steps, drastically increase time. <b> Pipeline
</b> uses multi threads to better allocate those time, so that while you are processing <i> text segmentation </i> on image 1,
for instance, then the computer can already begin processing <i> text localization </i> on image 2, and so on.

[View full tutorial >>](../workflow/pipeline.md)