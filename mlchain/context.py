import contextvars
from copy import deepcopy

class MLChainContext:
    variables = contextvars.ContextVar("mlchain_variables")

    def __getitem__(self, item):
        try:
            variables = self.variables.get()
            if item in variables:
                return variables[item]
            return None
        except:
            return None

    def __setitem__(self, key, value):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
        except:
            variables = {}
        variables[key] = value
        self.variables.set(variables)

    def pop(self, key):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
        except:
            variables = {}
        if key in variables:
            variables.pop(key)
        self.variables.set(variables)

    def __contains__(self, item):
        try:
            variables = self.variables.get()
            if item in variables:
                return True
            return False
        except:
            return False

    def items(self):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
            return variables.items()
        except:
            return []

    def update(self, vars: dict):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
        except:
            variables = {}
        variables.update(vars)
        self.variables.set(variables)

    def to_dict(self):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
        except:
            variables = {}
        return variables

    def copy(self):
        try:
            variables = self.variables.get()
            if variables is None:
                variables = {}
        except:
            variables = {}
        return deepcopy(variables)

    def set(self, variables):
        self.variables.set(variables)

    def __getattr__(self, item):
        return self.__getitem__(item)


mlchain_context = MLChainContext()
