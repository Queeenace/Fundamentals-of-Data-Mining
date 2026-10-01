"""Случайный лес для данных Census Income."""

import argparse
import json
import sys
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "3"))
from decision_tree import load_adult, prepare, quality  # noqa: E402


def fit_forest(data: Path, n_estimators: int, train_share: float = .8,
               max_depth: int = 12, min_leaf: int = 10,
               max_features: str = "sqrt", seed: int = 42):
    if not 0 < train_share < 1:
        raise ValueError("Доля обучения должна быть между 0 и 1")
    if n_estimators < 1 or max_depth < 1 or min_leaf < 1:
        raise ValueError("Число деревьев, глубина и размер листа должны быть положительными")
    raw, labels = load_adult(data)
    train_raw, test_raw, train_y, test_y = train_test_split(
        raw, labels, train_size=train_share, stratify=labels, random_state=seed)
    x_train, x_test, names = prepare(train_raw, test_raw)
    forest = RandomForestClassifier(
        n_estimators=n_estimators, criterion="gini", bootstrap=True,
        max_depth=max_depth, min_samples_leaf=min_leaf,
        max_features=max_features, random_state=seed, n_jobs=-1)
    forest.fit(x_train, train_y)
    result = {"technique": "random_forest", "n_estimators": n_estimators,
              "max_depth": max_depth, "min_leaf": min_leaf,
              "max_features": max_features, "train_share": train_share,
              "train_count": len(train_y), "test_count": len(test_y),
              "quality": quality(test_y, forest.predict(x_test)),
              "feature_importance": sorted(zip(names, map(float, forest.feature_importances_)),
                                           key=lambda item: item[1], reverse=True)[:15]}
    return result


def main():
    parser = argparse.ArgumentParser(description="Классификация Census Income случайным лесом")
    parser.add_argument("--data", type=Path, default=ROOT.parent / "3/data/adult.data")
    parser.add_argument("--technique", choices=["random_forest"], default="random_forest")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--train-share", type=float, default=.8)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--min-leaf", type=int, default=10)
    parser.add_argument("--max-features", choices=["sqrt", "log2"], default="sqrt")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = fit_forest(args.data, args.n_estimators, args.train_share,
                        args.max_depth, args.min_leaf, args.max_features)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
