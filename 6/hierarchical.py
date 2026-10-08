"""Иерархическая кластеризация клиентов банка."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import cut_tree, dendrogram, linkage
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "5"))
from cluster import DEFAULT_DATA, FEATURES, load_customers


METHODS = ("single", "complete", "average", "ward")


def fit_hierarchy(values: np.ndarray, method: str) -> np.ndarray:
    if method not in METHODS:
        raise ValueError(f"Связь кластеров: {', '.join(METHODS)}")
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Нужна матрица минимум из двух объектов с конечными координатами")
    return linkage(values, method=method, metric="euclidean", optimal_ordering=False)


def labels_at_k(tree: np.ndarray, k: int) -> np.ndarray:
    if not 2 <= k <= len(tree) + 1:
        raise ValueError("Недопустимое число кластеров")
    return cut_tree(tree, n_clusters=[k]).ravel()


def mean_centroid_error(values: np.ndarray, labels: np.ndarray) -> float:
    distances = np.empty(len(values))
    for label in np.unique(labels):
        members = labels == label
        center = values[members].mean(axis=0)
        distances[members] = np.linalg.norm(values[members] - center, axis=1)
    return float(distances.mean())


def save_dendrogram(tree: np.ndarray, method: str, path: Path, last_clusters: int = 35) -> None:
    # Последние слияния показывают структуру дерева без 850 мелких подписей.
    fig, axis = plt.subplots(figsize=(12, 5))
    dendrogram(tree, truncate_mode="lastp", p=last_clusters, show_leaf_counts=True, ax=axis)
    axis.set(title=f"{method}: последние {last_clusters} слияний", xlabel="Группа клиентов (число объектов)", ylabel="Расстояние слияния")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_assignments(path: Path, ids: list[str], values: np.ndarray, labels: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(("CustomerId", *FEATURES, "Cluster"))
        for item_id, coordinates, label in zip(ids, values, labels):
            writer.writerow((item_id, *coordinates, int(label) + 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--k", type=int, default=5, help="Число кластеров при разрезе дерева")
    parser.add_argument("--output", type=Path, help="CSV с координатами и кластерами")
    parser.add_argument("--dendrogram", type=Path, help="Путь для рисунка")
    args = parser.parse_args()
    original, ids = load_customers(args.data)
    scaled = StandardScaler().fit_transform(original)
    tree = fit_hierarchy(scaled, args.method)
    labels = labels_at_k(tree, args.k)
    print(f"Метод: {args.method}; k={args.k}; средняя ошибка до центроида: {mean_centroid_error(scaled, labels):.6f}")
    if args.dendrogram:
        save_dendrogram(tree, args.method, args.dendrogram)
    if args.output:
        save_assignments(args.output, ids, original, labels)
        print(f"Координаты и кластеры: {args.output}")
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(("CustomerId", *FEATURES, "Cluster"))
        for item_id, coordinates, label in zip(ids, original, labels):
            writer.writerow((item_id, *coordinates, int(label) + 1))


if __name__ == "__main__":
    main()
