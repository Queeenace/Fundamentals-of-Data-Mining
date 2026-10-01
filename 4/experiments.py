"""Измеряет качество случайного леса из 50–100 деревьев."""

import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ensemble import ROOT, fit_forest

sys.path.insert(0, str(ROOT.parent / "3"))
from plots import METRICS  # noqa: E402


def main():
    tree_summary = json.loads((ROOT.parent / "3/results/summary.json").read_text(encoding="utf-8"))
    baseline = next(row["quality"] for row in tree_summary["splits"] if row["train_share"] == .8)
    rows = []
    for count in range(50, 101, 10):
        start = time.perf_counter()
        result = fit_forest(ROOT.parent / "3/data/adult.data", count)
        result["seconds"] = time.perf_counter() - start
        rows.append(result)
        print(count, result["quality"], f"{result['seconds']:.1f} s", flush=True)
    summary = {"seed": 42, "train_share": .8, "comparison_tree_criterion": "gini",
               "comparison_tree_max_depth": 6, "comparison_tree_min_leaf": 120,
               "tree_baseline": baseline, "forests": rows}
    (ROOT / "results/summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 12})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    xs = [row["n_estimators"] for row in rows]
    for ax, (key, label) in zip(axes.flat, METRICS.items()):
        ys = [row["quality"][key] * 100 for row in rows]
        ax.plot(xs, ys, "ko-", label="Случайный лес")
        ax.axhline(baseline[key] * 100, color="gray", ls="--", label="Одно дерево")
        ax.set_title(label)
        ax.set_ylabel("Значение, %")
        ax.set_xticks(xs)
        ax.grid(alpha=.2)
        ax.legend(fontsize=9)
    for ax in axes[-1]:
        ax.set_xlabel("Количество деревьев")
    fig.tight_layout()
    fig.savefig(ROOT / "figures/forest_quality.png", dpi=190)
    plt.close(fig)


if __name__ == "__main__":
    main()
