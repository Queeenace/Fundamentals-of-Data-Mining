"""Классификация дохода бинарным деревом с тремя критериями разбиения."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent
NAMES = ("age", "workclass", "fnlwgt", "education", "education-num",
         "marital-status", "occupation", "relationship", "race", "sex",
         "capital-gain", "capital-loss", "hours-per-week", "native-country")
NUMERIC = (0, 2, 4, 10, 11, 12)
CATEGORICAL = tuple(i for i in range(14) if i not in NUMERIC)


def load_adult(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Читает оба файла UCI, включая метку с точкой в adult.test."""
    rows, labels = [], []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, skipinitialspace=True):
            if len(row) != 15:
                continue  # В тестовом файле первая строка содержит пояснение.
            label = row[-1].strip().rstrip(".")
            if label not in ("<=50K", ">50K"):
                continue
            rows.append([value.strip() for value in row[:-1]])
            labels.append(label == ">50K")
    return np.asarray(rows, dtype=object), np.asarray(labels, dtype=np.int8)


def prepare(train_raw: np.ndarray, test_raw: np.ndarray):
    """Обучает кодирование только на обучающей части, без утечки из теста."""
    transformer = ColumnTransformer([
        ("numeric", "passthrough", list(NUMERIC)),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         list(CATEGORICAL)),
    ], sparse_threshold=0)
    x_train = transformer.fit_transform(train_raw).astype(np.float32)
    x_test = transformer.transform(test_raw).astype(np.float32)
    names = []
    for feature in transformer.get_feature_names_out():
        kind, encoded = feature.split("__", 1)
        if kind == "numeric":
            names.append(NAMES[int(encoded[1:])])
        else:
            index, category = encoded[1:].split("_", 1)
            names.append(f"{NAMES[int(index)]}={category}")
    return x_train, x_test, names


def quality(y_true, y_pred) -> dict[str, float]:
    return {"accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0))}


def entropy(positive: np.ndarray, total: np.ndarray) -> np.ndarray:
    p = np.divide(positive, total, out=np.zeros_like(positive, dtype=float), where=total > 0)
    q = 1 - p
    result = np.zeros_like(p, dtype=float)
    np.multiply(p, np.log2(p, out=np.zeros_like(p), where=p > 0), out=result)
    result *= -1
    result -= np.multiply(q, np.log2(q, out=np.zeros_like(q), where=q > 0))
    return result


def gini(positive: np.ndarray, total: np.ndarray) -> np.ndarray:
    p = np.divide(positive, total, out=np.zeros_like(positive, dtype=float), where=total > 0)
    return 2 * p * (1 - p)


@dataclass
class Node:
    count: int
    positive: int
    depth: int
    feature: int | None = None
    threshold: float | None = None
    score: float = 0.0
    left: "Node | None" = None
    right: "Node | None" = None

    def as_dict(self, names: list[str]) -> dict:
        result = {"count": self.count, "positive": self.positive,
                  "prediction": ">50K" if self.positive * 2 >= self.count else "<=50K",
                  "depth": self.depth}
        if self.feature is not None:
            result.update({"feature": names[self.feature], "threshold": self.threshold,
                           "score": self.score, "left": self.left.as_dict(names),
                           "right": self.right.as_dict(names)})
        return result


class DecisionTree:
    """Ищет бинарные разбиения по IG, gain ratio или уменьшению Gini."""

    def __init__(self, criterion="gini", max_depth=6, min_leaf=120, bins=32):
        if criterion not in ("information_gain", "gain_ratio", "gini"):
            raise ValueError("Критерий: information_gain, gain_ratio или gini")
        self.criterion, self.max_depth = criterion, max_depth
        self.min_leaf, self.bins = min_leaf, bins
        self.root = None

    def fit(self, x: np.ndarray, y: np.ndarray):
        self.x, self.y = x, y
        self.root = self._build(np.arange(len(y)), 0)
        del self.x, self.y
        return self

    def _build(self, indices: np.ndarray, depth: int) -> Node:
        y = self.y[indices]
        count, positive = len(y), int(y.sum())
        node = Node(count, positive, depth)
        if depth >= self.max_depth or min(positive, count - positive) == 0 or count < 2 * self.min_leaf:
            return node
        parent = float((gini if self.criterion == "gini" else entropy)(
            np.array([positive]), np.array([count]))[0])
        best = (0.0, None, None)
        # Для чисел проверяются квантили, для индикаторов категорий одно разбиение.
        for feature in range(self.x.shape[1]):
            values = self.x[indices, feature]
            low, high = float(values.min()), float(values.max())
            if low == high:
                continue
            if low >= 0 and high <= 1 and np.all((values == 0) | (values == 1)):
                thresholds = np.array([0.5])
            else:
                thresholds = np.unique(np.quantile(values, np.linspace(0, 1, self.bins + 2)[1:-1]))
            positions = np.searchsorted(thresholds, values, side="left")
            groups = np.bincount(positions, minlength=len(thresholds) + 1)
            positives = np.bincount(positions, weights=y, minlength=len(thresholds) + 1)
            left_count, left_positive = np.cumsum(groups)[:-1], np.cumsum(positives)[:-1]
            valid = (left_count >= self.min_leaf) & (count - left_count >= self.min_leaf)
            if not valid.any():
                continue
            right_count, right_positive = count - left_count, positive - left_positive
            impurity = gini if self.criterion == "gini" else entropy
            weighted = (left_count * impurity(left_positive, left_count)
                        + right_count * impurity(right_positive, right_count)) / count
            scores = parent - weighted
            if self.criterion == "gain_ratio":
                split_info = entropy(left_count, np.full(len(left_count), count))
                scores = np.divide(scores, split_info, out=np.zeros_like(scores), where=split_info > 0)
            scores[~valid] = -np.inf
            candidate = int(np.argmax(scores))
            if scores[candidate] > best[0] + 1e-12:
                best = (float(scores[candidate]), feature, float(thresholds[candidate]))
        score, feature, threshold = best
        if feature is None or score <= 1e-6:
            return node
        left_mask = self.x[indices, feature] <= threshold
        node.feature, node.threshold, node.score = feature, threshold, score
        node.left = self._build(indices[left_mask], depth + 1)
        node.right = self._build(indices[~left_mask], depth + 1)
        return node

    def predict(self, x: np.ndarray) -> np.ndarray:
        result = np.zeros(len(x), dtype=np.int8)

        def visit(node, indices):
            if node.feature is None:
                result[indices] = int(node.positive * 2 >= node.count)
                return
            mask = x[indices, node.feature] <= node.threshold
            visit(node.left, indices[mask])
            visit(node.right, indices[~mask])

        visit(self.root, np.arange(len(x)))
        return result


def main():
    parser = argparse.ArgumentParser(description="Дерево решений для Census Income")
    parser.add_argument("--train", type=Path, default=ROOT / "data/adult.data")
    parser.add_argument("--test", type=Path, default=ROOT / "data/adult.test")
    parser.add_argument("--criterion", choices=("information_gain", "gain_ratio", "gini"), default="gini")
    parser.add_argument("--train-share", type=float, default=None, help="Доля 0..1; без параметра используются все исходные обучающие данные")
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--min-leaf", type=int, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw_train, y_train = load_adult(args.train)
    if args.train_share is None:
        raw_test, y_test = load_adult(args.test)
        split = "original_100_percent"
    else:
        if not 0 < args.train_share < 1:
            parser.error("--train-share должен быть между 0 и 1")
        raw_train, raw_test, y_train, y_test = train_test_split(
            raw_train, y_train, train_size=args.train_share, stratify=y_train, random_state=42)
        split = args.train_share
    x_train, x_test, names = prepare(raw_train, raw_test)
    model = DecisionTree(args.criterion, args.max_depth, args.min_leaf).fit(x_train, y_train)
    result = {"criterion": args.criterion, "split": split,
              "train_count": len(y_train), "test_count": len(y_test),
              "quality": quality(y_test, model.predict(x_test)),
              "tree": model.root.as_dict(names)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
