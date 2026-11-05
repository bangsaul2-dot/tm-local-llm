"""Synthetic-only regression tests for generic public-diagram metrics."""
import unittest
from projects.SecureFrame.tools.public_diagram_benchmark import box_iou, score_boxes

class PublicBenchmarkTests(unittest.TestCase):
    def test_iou(self):
        self.assertEqual(box_iou([0, 0, 10, 10], [0, 0, 10, 10]), 1.0)
        self.assertEqual(box_iou([0, 0, 10, 10], [20, 20, 30, 30]), 0.0)

    def test_one_to_one_matching(self):
        metrics = score_boxes([[0, 0, 10, 10], [0, 0, 10, 10]], [[0, 0, 10, 10]])
        self.assertEqual((metrics["tp"], metrics["fp"], metrics["fn"]), (1, 1, 0))

    def test_missing_detection(self):
        metrics = score_boxes([], [[0, 0, 10, 10]])
        self.assertEqual((metrics["tp"], metrics["fp"], metrics["fn"]), (0, 0, 1))

if __name__ == "__main__":
    unittest.main()
