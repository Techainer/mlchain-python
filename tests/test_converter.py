from mlchain.base.converter import Converter, get_type
import unittest
from typing import *
import numpy as np


def check_type(value, t):
    t_origin, t_args = get_type(t)
    if t_origin == Union:
        for arg in t_args:
            if check_type(value, arg):
                return True
        return False
    if isinstance(value, t_origin):
        if t_args is None:
            return True
        else:
            return True
    else:
        return False


class TestConverter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.converter = Converter()
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_list(self):
        print(get_type(Union[dict, list]))
        test_cases = [
            {
                "origin": "[\"haha\"]",
                "type": List,
                "expected": ["haha"]
            },
            {
                "origin": "[\"haha\"]",
                "type": Union[list, dict],
                "expected": ["haha"]
            },
            {
                "origin": "[\"haha\"]",
                "type": List,
                "expected": ["haha"]
            },
            {
                "origin": [1],
                "type": List[str],
                "expected": ["1"],
            },
            {
                "origin": "[[1,2,3],[1,2,3]]",
                "type": np.ndarray,
                "expected": np.array([[1, 2, 3], [1, 2, 3]]),
            },
            {
                "origin": ["[[1,2,3],[1,2,3]]"],
                "type": List[np.ndarray],
                "expected": [np.array([[1, 2, 3], [1, 2, 3]])],
            },
        ]
        for test_case in test_cases:
            value = self.converter.convert(test_case['origin'], test_case['type'])
            self.assertTrue(check_type(value, test_case['type']),
                            msg="{0}: {1} -> {2}".format(test_case['type'], test_case['origin'], test_case['expected']))


if __name__ == '__main__':
    unittest.main()
