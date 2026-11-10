"""Synthetic-only local inference retry tests."""
import unittest
from qwen_contract import request_semantic

VALID = '{"nodes":[{"name":"Alpha","kind":"leaf","parent":null}],"edges":[]}'

class ContractTests(unittest.TestCase):
    def test_retry(self):
        responses = iter(["not-json", VALID])
        result = request_semantic(lambda prompt, image: next(responses), object())
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["status"], "valid")

    def test_coordinate_rejected(self):
        response = '{"nodes":[{"name":"Alpha","kind":"leaf","parent":null,"bbox":[0,0,1,1]}],"edges":[]}'
        result = request_semantic(lambda prompt, image: response, object(), max_retries=1)
        self.assertEqual(result["status"], "needs_review")

    def test_bounded_failure(self):
        result = request_semantic(lambda prompt, image: "{}", object(), max_retries=2)
        self.assertEqual(result["attempts"], 3)

if __name__ == "__main__":
    unittest.main()
