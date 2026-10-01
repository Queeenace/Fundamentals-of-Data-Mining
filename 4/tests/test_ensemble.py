import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ensemble import fit_forest


class EnsembleTests(unittest.TestCase):
    def test_forest_uses_requested_number_and_split(self):
        path = Path(__file__).resolve().parents[2] / "3/data/adult.data"
        result = fit_forest(path, 3)
        self.assertEqual(result["n_estimators"], 3)
        self.assertEqual(result["train_count"] + result["test_count"], 32561)
        self.assertEqual(result["test_count"], 6513)
        self.assertTrue(all(0 <= value <= 1 for value in result["quality"].values()))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            fit_forest(Path("unused"), 0)


if __name__ == "__main__":
    unittest.main()
