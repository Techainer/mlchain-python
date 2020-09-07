import inspect
import trio
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
        if inspect.iscoroutinefunction(self.func_) \
                or (not inspect.isfunction(self.func_)
                    and hasattr(self.func_, '__call__')
                    and inspect.iscoroutinefunction(self.func_.__call__)):
            return trio.run(self.__call__)
        with self:
            return self.func_(*self.args, **self.kwargs)

    async def exec_async(self):
        return self.__call__()

    async def __call__(self):
        """
        Task's process code
        """
        if inspect.iscoroutinefunction(self.func_) \
                or (not inspect.isfunction(self.func_)
                    and hasattr(self.func_, '__call__')
                    and inspect.iscoroutinefunction(self.func_.__call__)):
            async with self:
                return await self.func_(*self.args, **self.kwargs)
        with self:
            return self.func_(*self.args, **self.kwargs)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def __enter__(self):
        mlchain_context.set(self.context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SyncTask:
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
        mlchain_context.set(self.context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
