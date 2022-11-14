from unittest import TestCase
import sys
import os

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.Python_1_test import keys_teshaurus


class TestTesaurus(TestCase):

    def setUp(self):
        self.data = ['Иван', 'Мария', 'Петр', 'Илья', 'Михаил']
        self.ok = {'И': ['Иван', 'Илья'], 'М': ['Мария', 'Михаил'], 'П': 'Петр'}

    def test_tesaurus(self):
        result = keys_teshaurus(self.data)
        self.assertEqual(result, self.ok)

    def test_wrong_type(self):
        self.assertRaises(AttributeError, keys_teshaurus, "wrong_list")
