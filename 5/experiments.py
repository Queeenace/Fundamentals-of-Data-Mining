"""Эксперименты и диаграммы для разделительной кластеризации."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from cluster import DEFAULT_DATA, add_noise, cluster, load_customers, write_assignments


ROOT = Path(__file__).parent
NOISE = (0, 0.01, 0.03, 0.05, 0.10)
KS = range(3, 10)
ALGORITHMS = ("kmeans", "kmedoids")


def main() -> None:
    original, ids = load_customers(DEFAULT_DATA)
    scaler = StandardScaler().fit(original)
    pca = PCA(n_components=2).fit(scaler.transform(original))
    results = []
    scatter = {}
    for noise in NOISE:
        values, changed = add_noise(original, noise)
        scaled = scaler.transform(values)
        for algorithm in ALGORITHMS:
            for k in KS:
                outcome = cluster(scaled, k, algorithm)
                results.append((algorithm, noise, k, int(changed.sum()), outcome.error, outcome.objective))
                print(f"{algorithm:8} шум={noise:.0%} k={k}: ошибка={outcome.error:.4f}", flush=True)
                if k == 5:
                    scatter[(algorithm, noise)] = (pca.transform(scaled), outcome.labels)
                    if noise in (0, 0.10):
                        name = f"{algorithm}_k5_noise{round(noise * 100)}.csv"
                        write_assignments(ROOT / "results" / name, ids, values, outcome.labels)
    path = ROOT / "results" / "experiments.csv"
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(("algorithm", "noise_fraction", "k", "changed_objects", "mean_euclidean_error", "algorithm_objective"))
        writer.writerows(results)
    draw_error(results)
    draw_scatter(scatter)


def draw_error(results: list[tuple]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for axis, algorithm in zip(axes, ALGORITHMS):
        for noise in NOISE:
            data = [row for row in results if row[0] == algorithm and row[1] == noise]
            axis.plot([row[2] for row in data], [row[4] for row in data], marker="o", label=f"{noise:.0%}")
        axis.set(title=algorithm, xlabel="Число кластеров k", xticks=list(KS))
        axis.grid(alpha=0.25)
        axis.legend(title="Доля шума")
    axes[0].set_ylabel("Среднее расстояние до представителя кластера")
    fig.tight_layout()
    path = ROOT / "figures" / "error_by_k_and_noise.png"
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def draw_scatter(scatter: dict) -> None:
    fig, axes = plt.subplots(2, 5, figsize=(17, 7), sharex=True, sharey=True)
    for row, algorithm in enumerate(ALGORITHMS):
        for column, noise in enumerate(NOISE):
            points, labels = scatter[(algorithm, noise)]
            axis = axes[row, column]
            axis.scatter(points[:, 0], points[:, 1], c=labels, cmap="tab10", s=9, alpha=0.7, vmin=0, vmax=4)
            axis.set_title(f"{algorithm}, шум {noise:.0%}")
            axis.grid(alpha=0.15)
            if row == 1:
                axis.set_xlabel("Главная компонента 1")
            if column == 0:
                axis.set_ylabel("Главная компонента 2")
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "clusters_k5_by_noise.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
