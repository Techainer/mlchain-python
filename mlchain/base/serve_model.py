from inspect import signature
import inspect
import time
from .exceptions import MlChainError
from threading import Lock, Event
import itertools
import types
from mlchain import mlchain_context

def non_thread(timeout=-1):
    if timeout is None or (isinstance(timeout, (float, int)) and timeout <= 0):
        timeout = -1
    else:
        timeout = float(timeout)
    lock = Lock()

    def wrapper(func):
        def f(*args, **kwargs):
            acquire = lock.acquire(timeout=timeout)
            if acquire:
                try:
                    output = func(*args, **kwargs)
                except Exception as e:
                    lock.release()
                    raise e
                lock.release()
            else:
                lock.release()
                raise MlChainError("Timeout nonthread", code="T001", status_code=408)
            return output

        f.__signature__ = signature(func)
        f.__qualname__ = func.__qualname__
        return f

    return wrapper


def get_single_funcion(batch_func, variables, variable_names=None, default=None, timeout=-1, name='single_func',
                       max_queue=100,
                       max_batch_size=32):
    if timeout is None or (isinstance(timeout, (float, int)) and timeout <= 0):
        timeout = -1
    else:
        timeout = float(timeout)
    if isinstance(batch_func, types.MethodType):
        self = batch_func.__self__
    else:
        self = None
    if default is None:
        default = {}
    assert len(set(list(variables) + list(default))) == len(variables) + len(default)
    if variable_names is None:
        variable_names = {}
    for var in variables:
        if var not in variable_names:
            variable_names[var] = var
    arg_names = list(variable_names.values())
    queue = []
    lock = Lock()
    result = {}
    job_counter = itertools.count()

    def handler():
        if len(queue) > 0:
            pivot = min(max_batch_size, len(queue))
            kwargs = {variable: [] for variable in variable_names}
            done_events = []
            ids = []
            for sample in queue[:pivot]:
                if sample['done__'].is_set():
                    continue
                for k in kwargs:
                    kwargs[k].append(sample[variable_names[k]])
                done_events.append(sample['done__'])
                ids.append(sample['id__'])
            if len(ids) > 0:
                try:
                    outputs = batch_func(**kwargs, **default)
                except Exception as e:
                    outputs = [str(e)] * len(ids)
                for done, id, output in zip(done_events, ids, outputs):
                    result[id] = output
                    done.set()
            for i in range(pivot):
                queue.pop(0)

    def f(*args, **kwargs):
        if len(queue) > max_queue:
            raise MlChainError("Serve busy", code="T003", status_code=429)
        assert len(args) + len(kwargs) == len(arg_names)
        e = Event()
        id = next(job_counter)
        params = {**{v: arg for v, arg in zip(arg_names, args)}, **kwargs, 'id__': id, 'done__': e}
        queue.append(params)

        acquire = lock.acquire(timeout=timeout)
        if acquire:
            try:
                if not e.is_set():
                    handler()
            except Exception as e:
                lock.release()
                raise e
            lock.release()
        else:
            lock.release()
            raise MlChainError("Timeout batch", code="T002", status_code=408)

        if not e.wait(timeout):
            raise MlChainError("Timeout batch", code="T002", status_code=408)
        if id in result:
            return result.pop(id)
        else:
            raise MlChainError("Timeout batch", code="T002", status_code=408)

    if self:
        wrapper = eval('lambda self,{0}: 0'.format(', '.join(arg_names)))
        wrapper.__name__ = name
        wrapper = types.MethodType(wrapper, self)
    else:
        wrapper = eval('lambda {0}: 0'.format(', '.join(arg_names)))
        wrapper.__name__ = name
    for v, t in variables.items():
        wrapper.__annotations__[variable_names[v]] = t

    f.__signature__ = signature(wrapper)
    f.__qualname__ = '.'.join(batch_func.__qualname__.split('.')[:-1] + [name])
    del wrapper
    return f


def batch(name, variables, default=None, variable_names=None, timeout=-1, max_queue=100, max_batch_size=32):
    def wrapper(f):
        f.__BATCH_CONFIG__ = {
            'name': name,
            'variables': variables,
            'variable_names': variable_names,
            'default': default,
            'timeout': timeout,
            'max_queue': max_queue,
            'max_batch_size': max_batch_size
        }
        return f

    return wrapper


class ServeModel(object):
    def __init__(self, model, name=None, deny_all_function=False, blacklist=[], whitelist=[], config=None):
        if isinstance(model, type):
            raise AssertionError("Your input model must be an instance")

        self.model = model
        self.name = name or model.__class__.__name__
        self.all_serve_function = set()
        self.all_atrributes = set()
        blacklist_set = set(self._check_blacklist(deny_all_function, blacklist, whitelist))
        self._check_all_func(blacklist_set)
        self._check_all_attribute(blacklist_set)
        self.config = config

    def _check_blacklist(self, deny_all_function, blacklist, whitelist):
        output = []
        if deny_all_function:
            for name in dir(self.model):
                attr = getattr(self.model, name)

                if not name.startswith("__") and (
                        getattr(attr, "_MLCHAIN_EXCEPT_SERVING", False) or name not in whitelist):
                    output.append(name)
        else:
            for name in dir(self.model):
                attr = getattr(self.model, name)

                if not name.startswith("__") and (getattr(attr, "_MLCHAIN_EXCEPT_SERVING", False) or name in blacklist):
                    output.append(name)
        return output

    def _check_all_func(self, blacklist_set):
        """
        Check all available function of class to serve
        """

        self.all_serve_function = set()
        for name in dir(self.model):
            attr = getattr(self.model, name)

            if (not name.startswith("__") or name == '__call__') and callable(attr) and name not in blacklist_set:
                self.all_serve_function.add(name)
                batch_config = getattr(attr, '__BATCH_CONFIG__', None)
                if batch_config:
                    single_func = get_single_funcion(attr, variables=batch_config['variables'],
                                                     default=batch_config['default'],
                                                     variable_names=batch_config['variable_names'],
                                                     timeout=batch_config['timeout'], name=batch_config['name'],
                                                     max_queue=batch_config['max_queue'],
                                                     max_batch_size=batch_config['max_batch_size'])
                    setattr(self.model, batch_config['name'], single_func)
                    self.all_serve_function.add(batch_config['name'])

    def _list_all_atrributes(self):
        return list(self.all_atrributes)

    def _check_all_attribute(self, blacklist_set):
        """
        Check all available function of class to serve
        """

        self.all_atrributes = set()
        for name in dir(self.model):
            attr = getattr(self.model, name)

            if not name.startswith("__") and not callable(attr):
                if not getattr(attr, "_MLCHAIN_EXCEPT_SERVING", False) and name not in blacklist_set:
                    self.all_atrributes.add(name)

    def _list_all_function(self):
        """
        Get all functions of model
        """
        return list(self.all_serve_function)

    def _list_all_function_and_description(self):
        """
        Get all function and description of all function of model
        """
        output = {}

        for name in self.all_serve_function:
            output[name] = getattr(self.model, name).__doc__
        return output

    def _list_all_function_and_parameters(self):
        """
        Get all function and parameters of all function of model
        """
        output = {}

        for name in self.all_serve_function:
            output[name] = str(signature(getattr(self.model, name)))
        return output

    def _get_description_of_func(self, function_name):
        """
        Get description of a specific function
        """
        if function_name is None or len(function_name) == 0 or function_name not in self.all_serve_function:
            return "No description for unknown function"

        return getattr(self.model, function_name).__doc__

    def _get_parameters_of_func(self, function_name):
        """
        Get all parameters of a specific function
        """
        if function_name is None or len(function_name) == 0 or function_name not in self.all_serve_function:
            return "No parameters for unknown function"

        return str(signature(getattr(self.model, function_name)))

    def _get_all_description(self):
        """
        Get all description of model
        """
        output = {
            '__main__': self.model.__doc__,
            'all_func_des': self._list_all_function_and_description(),
            'all_func_params': self._list_all_function_and_parameters(),
            'all_attributes': self._list_all_atrributes()
        }
        return output

    def get_function(self, function_name):
        return getattr(self.model, function_name)

    def _valid_format_kwargs(self, kwargs, func_):
        """
        Normalize data into right formats of func_
        """
        inspect_func_ = signature(func_)

        accept_kwargs = "**" in str(inspect_func_)

        # Check valid parameters
        for key, value in kwargs.items():
            if key not in inspect_func_.parameters:
                if accept_kwargs:
                    pass
                else:
                    raise AssertionError(
                        "You should not have {0} in your parameters. This function require: {1}".format(key,
                                                                                                        inspect_func_.parameters))
        return kwargs

    def call_function(self, function_name_, id_=None, *args, **kwargs):
        """
        Flow request values into function_name and return output
        """
        function_name, id = function_name_, id_
        if function_name is None:
            raise AssertionError("You need to specify the function name (API name)")
        mlchain_context['context_id'] = id_
        if isinstance(function_name, str):
            if len(function_name) == 0:
                if hasattr(self.model, '__call__') and callable(getattr(self.model, '__call__')):
                    func_ = getattr(self.model, '__call__')
                else:
                    raise AssertionError("You need to specify the function name (API name)")
            else:
                if function_name not in self.all_serve_function:
                    if function_name in self.all_atrributes:
                        return getattr(self.model, function_name)
                    else:
                        raise AssertionError("This function or attribute hasn't been served or in blacklist")

                func_ = getattr(self.model, function_name)

            # Normalize format of input
            self._valid_format_kwargs(kwargs, func_)
            # Call function
            output = func_(*args, **kwargs)
        else:
            raise AssertionError("function_name must be str")
        return output

    async def call_async_function(self, function_name_, id_=None, *args, **kwargs):
        """
        Flow request values into function_name and return output
        """
        function_name, id = function_name_, id_
        if function_name is None:
            raise AssertionError("You need to specify the function name (API name)")
        mlchain_context['context_id'] = id_
        if isinstance(function_name, str):
            if len(function_name) == 0:
                if hasattr(self.model, '__call__') and callable(getattr(self.model, '__call__')):
                    func_ = getattr(self.model, '__call__')
                else:
                    raise AssertionError("You need to specify the function name (API name)")
            else:
                if function_name not in self.all_serve_function:
                    if function_name in self.all_atrributes:
                        return getattr(self.model, function_name)
                    else:
                        raise AssertionError("This function or attribute hasn't been served or in blacklist")

                func_ = getattr(self.model, function_name)

            # Call function
            self._valid_format_kwargs(kwargs, func_)
            if inspect.iscoroutinefunction(func_):
                output = await func_(*args, **kwargs)
            else:
                output = func_(*args, **kwargs)
        else:
            raise AssertionError("function_name must be str")
        return output

    def get_all_func(self):
        funcs = {name: getattr(self.model, name) for name in self.all_serve_function}
        return funcs
