"""Tests use synthetic rectangles, not real technical drawings."""
import unittest
from geometry_candidates import deduplicate_boxes, classify_nested_boxes

class GeometryCandidateTests(unittest.TestCase):
    def test_duplicate_removed(self):
        self.assertEqual(len(deduplicate_boxes([[0,0,10,10],[0,0,10,10]])),1)

    def test_nested_container_retained(self):
        boxes=[[0,0,100,100],[10,10,30,30]]
        self.assertEqual(len(deduplicate_boxes(boxes)),2)
        self.assertEqual(classify_nested_boxes(boxes),[None,0])

if __name__ == "__main__":
    unittest.main()
