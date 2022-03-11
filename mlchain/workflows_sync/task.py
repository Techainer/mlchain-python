from mlchain import mlchain_context

class Task:
    """
    This class wrap a function to a Task 
    :func_: Function 
    """

    def __init__(self, func_, *args, **kwargs):
        assert callable(func_), 'You have to transfer a callable instance and its params'
        self.func_ = func_
        self.args = args
        self.kwargs = kwargs
        self.span = None
        self.context = mlchain_context.copy()

    def exec(self):
        return self.func_(*self.args, **self.kwargs)

    def __call__(self):
        """
        Task's process code
        """
        return self.func_(*self.args, **self.kwargs)

    def __enter__(self):
        mlchain_context.update(self.context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass