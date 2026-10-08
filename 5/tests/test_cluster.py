import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cluster import add_noise, cluster


class ClusterTests(unittest.TestCase):
    def test_separated_groups(self):
        values = np.array([[0, 0], [0, 1], [10, 10], [10, 11]], dtype=float)
        for algorithm in ("kmeans", "kmedoids"):
            with self.subTest(algorithm=algorithm):
                result = cluster(values, 2, algorithm)
                self.assertEqual(result.labels[0], result.labels[1])
                self.assertEqual(result.labels[2], result.labels[3])
                self.assertNotEqual(result.labels[0], result.labels[2])
                self.assertAlmostEqual(result.error, 0.5)

    def test_noise_count_and_reproducibility(self):
        values = np.arange(200, dtype=float).reshape(100, 2)
        first, changed = add_noise(values, 0.03, seed=12)
        second, changed_again = add_noise(values, 0.03, seed=12)
        self.assertEqual(changed.sum(), 3)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(changed, changed_again)
        np.testing.assert_array_equal(first[~changed], values[~changed])


if __name__ == "__main__":
    unittest.main()
