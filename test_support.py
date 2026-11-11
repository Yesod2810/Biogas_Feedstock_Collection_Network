"""Author: Thanh Dat Nguyen
Student ID: 23857030
Date: 29/10/2026
Purpose: Compare NumPy arrays and manual sequences with scalar equality in tests.
"""

import unittest
import numpy as np
from manual_structures import LinkedList


def _sequence_value(value):
    if isinstance(value, (np.ndarray, LinkedList, tuple)):
        return tuple(_sequence_value(item) for item in value)
    return value


class SequenceTestCase(unittest.TestCase):
    def assertEqual(self, first, second, msg=None):
        return super().assertEqual(_sequence_value(first), _sequence_value(second), msg)

    def assertNotEqual(self, first, second, msg=None):
        return super().assertNotEqual(_sequence_value(first), _sequence_value(second), msg)

