import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hierarchical import METHODS, fit_hierarchy, labels_at_k, mean_centroid_error


class HierarchicalTests(unittest.TestCase):
    def test_all_linkages_separate_obvious_groups(self):
        values = np.array([[0, 0], [0, 1], [10, 10], [10, 11]], dtype=float)
        for method in METHODS:
            with self.subTest(method=method):
                labels = labels_at_k(fit_hierarchy(values, method), 2)
                self.assertEqual(len(set(labels)), 2)
                self.assertEqual(labels[0], labels[1])
                self.assertEqual(labels[2], labels[3])
                self.assertNotEqual(labels[0], labels[2])
                self.assertAlmostEqual(mean_centroid_error(values, labels), 0.5)


if __name__ == "__main__":
    unittest.main()
