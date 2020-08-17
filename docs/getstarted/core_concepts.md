# Core Concepts

The essential points for understanding and effectively using MLChain can be
grouped into the following categories:

- [ML Deployment](../Model Deployment/general.md)
- [Client API](../Client/general.md)
- [Workflow](#workflow)

This document serves as an introduction to each of these categories. When
you're ready to dive deeper, each category has its own section in our
documentation. These sections allows you to understand the inner working of particular functions, along with 
real life example using our service.

## ML Deployment
Simple Machine Learning model deployment is the central feature of ML Chain library.
Our ServeModel function allows user to deploy their model without requiring software engineering knowledge.
We support Flask and grpc for website hosting.

[Read More...](../Model Deployment/general.md)

## Client Sharing
This use our Client Class service that allows users to share their ML models to other users, along with reusing and coming 
back to them every time they want to redeploy their model.

[Read More...](../Client/general.md)

## Workflow
Workflow is an independent function of MLChain that allows you to process your function 
in a <b> parallel </b> or a <b> pipeline </b> manner. This uses multi thread processing without
the need of complex DevOps programming, allowing your app to run multiple tasks 20 - 50 times faster than traditional approach.

[Read More...](/workflow/general.md)
