import sys
import os
from unittest import TestCase
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from client import make_presence, response_process


class TestClient(TestCase):
    def setUp(self):
        self.data = {
            'action': 'presence',
            'time': 1,
            'type': 'status',
            'user': {
                "account_name": 'Guest',
                "status": "Yep, I am here!"
            }
        }
        self.server_answer_200 = {RESPONSE: 200}
        self.server_answer_400 = {
            RESPONSE: 400,
            ERROR: 'Bad Request'}
        self.server_answer_no_response = {}
        self.result_200 = 'На связи!'
        self.result_400 = f'Bad request 400'
        self.result_error = {ERROR: 'Bad Request'}

    def test_make_presence(self):
        result = make_presence()
        result['time'] = 1
        self.assertEqual(result, self.data)

    def test_response_process(self):
        # Testing response=200
        result_200 = response_process(self.server_answer_200)
        self.assertEqual(result_200, self.result_200)
        # Testing response=400
        result_400 = response_process(self.server_answer_400)
        self.assertEqual(result_400, self.result_400)
        self.assertRaises(ValueError,response_process, self.result_error)

    def tearDown(self) -> None:
        pass
