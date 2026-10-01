"""Воспроизводит эксперименты с тремя критериями и долями обучения."""

import json
import time
from pathlib import Path

from sklearn.model_selection import train_test_split

from decision_tree import ROOT, DecisionTree, load_adult, prepare, quality
from plots import quality_chart, tree_chart


def main():
    raw_train, y_train = load_adult(ROOT / "data/adult.data")
    raw_test, y_test = load_adult(ROOT / "data/adult.test")
    full = []
    for criterion in ("information_gain", "gain_ratio", "gini"):
        x_train, x_test, names = prepare(raw_train, raw_test)
        start = time.perf_counter()
        model = DecisionTree(criterion).fit(x_train, y_train)
        seconds = time.perf_counter() - start
        tree = model.root.as_dict(names)
        result = {"criterion": criterion, "train_count": len(y_train),
                  "test_count": len(y_test), "seconds": seconds,
                  "quality": quality(y_test, model.predict(x_test)), "tree": tree}
        (ROOT / "results" / f"tree_{criterion}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        tree_chart(tree, criterion.replace("_", " ").title(),
                   ROOT / "figures" / f"tree_{criterion}.png")
        full.append({key: value for key, value in result.items() if key != "tree"})
        print(criterion, result["quality"], f"{seconds:.1f} s", flush=True)

    splits = []
    for share in (.6, .7, .8, .9):
        train_raw, test_raw, train_y, test_y = train_test_split(
            raw_train, y_train, train_size=share, stratify=y_train, random_state=42)
        x_train, x_test, _ = prepare(train_raw, test_raw)
        start = time.perf_counter()
        model = DecisionTree("gini").fit(x_train, train_y)
        seconds = time.perf_counter() - start
        result = {"train_share": share, "train_count": len(train_y),
                  "test_count": len(test_y), "seconds": seconds,
                  "quality": quality(test_y, model.predict(x_test))}
        splits.append(result)
        print(share, result["quality"], f"{seconds:.1f} s", flush=True)
    summary = {"data": "UCI Adult/Census Income", "seed": 42,
               "max_depth": 6, "min_leaf": 120, "numeric_bins": 32,
               "full_training": full, "split_criterion": "gini", "splits": splits}
    (ROOT / "results/summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_chart(splits, ROOT / "figures/quality_by_share.png")


if __name__ == "__main__":
    main()
