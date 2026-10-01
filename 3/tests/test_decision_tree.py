import unittest
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decision_tree import DecisionTree, load_adult, quality


class DecisionTreeTests(unittest.TestCase):
    def test_criteria_classify_simple_separable_data(self):
        x = np.array([[0], [0], [0], [1], [1], [1]], dtype=np.float32)
        y = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
        for criterion in ("information_gain", "gain_ratio", "gini"):
            with self.subTest(criterion=criterion):
                model = DecisionTree(criterion, max_depth=2, min_leaf=1).fit(x, y)
                np.testing.assert_array_equal(model.predict(x), y)
                self.assertEqual(model.root.feature, 0)

    def test_adult_files_have_expected_sizes_and_normalized_labels(self):
        root = Path(__file__).resolve().parents[1]
        for name, expected in (("adult.data", 32561), ("adult.test", 16281)):
            with self.subTest(name=name):
                x, y = load_adult(root / "data" / name)
                self.assertEqual((len(x), len(y)), (expected, expected))
                self.assertTrue(np.isin(y, [0, 1]).all())

    def test_quality_uses_positive_income_class(self):
        actual = np.array([1, 1, 0, 0])
        predicted = np.array([1, 0, 1, 0])
        values = quality(actual, predicted)
        for key in ("accuracy", "precision", "recall", "f1"):
            self.assertAlmostEqual(values[key], .5)


if __name__ == "__main__":
    unittest.main()
