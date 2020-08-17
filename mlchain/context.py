import contextvars
from copy import deepcopy


class MLChainContext:
    variables = contextvars.ContextVar("mlchain_variables")

    def __getitem__(self, item):
        try:
            variables = self.variables.get()
            if item in variables:
                return variables[item]
            else:
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
            else:
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

    def get(self):
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

    def set(self, vars):
        self.variables.set(vars)


mlchain_context = MLChainContext()
