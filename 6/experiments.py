"""Сравнение четырёх способов иерархической кластеризации."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from hierarchical import METHODS, fit_hierarchy, labels_at_k, mean_centroid_error, save_assignments, save_dendrogram
from hierarchical import DEFAULT_DATA, load_customers


ROOT = Path(__file__).parent


def read_partition(path: Path) -> np.ndarray:
    with path.open(newline="", encoding="utf-8") as source:
        return np.array([int(row["Cluster"]) for row in csv.DictReader(source)])


def main() -> None:
    original, ids = load_customers(DEFAULT_DATA)
    scaled = StandardScaler().fit_transform(original)
    projected = PCA(n_components=2).fit_transform(scaled)
    baseline_kmeans = read_partition(ROOT.parent / "5" / "results" / "kmeans_k5_noise0.csv")
    baseline_medoids = read_partition(ROOT.parent / "5" / "results" / "kmedoids_k5_noise0.csv")
    scores = []
    labels_by_method = {}
    for method in METHODS:
        tree = fit_hierarchy(scaled, method)
        save_dendrogram(tree, method, ROOT / "figures" / f"dendrogram_{method}.png")
        for k in range(3, 10):
            labels = labels_at_k(tree, k)
            error = mean_centroid_error(scaled, labels)
            silhouette = silhouette_score(scaled, labels) if k == 5 else float("nan")
            ari_kmeans = adjusted_rand_score(baseline_kmeans, labels) if k == 5 else float("nan")
            ari_medoids = adjusted_rand_score(baseline_medoids, labels) if k == 5 else float("nan")
            scores.append((method, k, error, silhouette, ari_kmeans, ari_medoids))
            print(f"{method:8} k={k}: ошибка={error:.4f}")
            if k == 5:
                labels_by_method[method] = labels
                save_assignments(ROOT / "results" / f"{method}_k5.csv", ids, original, labels)
    with (ROOT / "results" / "experiments.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(("method", "k", "mean_centroid_error", "silhouette_k5", "ARI_vs_kmeans_k5", "ARI_vs_kmedoids_k5"))
        writer.writerows(scores)
    plot_scatter(projected, labels_by_method)
    plot_comparison(scores, scaled, baseline_kmeans, baseline_medoids)


def plot_scatter(projected: np.ndarray, labels_by_method: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=True, sharey=True)
    for axis, method in zip(axes.flat, METHODS):
        axis.scatter(projected[:, 0], projected[:, 1], c=labels_by_method[method], s=10, alpha=0.7, cmap="tab10")
        axis.set(title=f"{method}, k=5", xlabel="Главная компонента 1", ylabel="Главная компонента 2")
        axis.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "clusters_by_linkage.png", dpi=180)
    plt.close(fig)


def plot_comparison(scores: list[tuple], values: np.ndarray, kmeans: np.ndarray, medoids: np.ndarray) -> None:
    fig, axis = plt.subplots(figsize=(9, 5))
    for method in METHODS:
        data = [row for row in scores if row[0] == method]
        axis.plot([row[1] for row in data], [row[2] for row in data], marker="o", label=method)
    from hierarchical import mean_centroid_error
    axis.scatter([5], [mean_centroid_error(values, kmeans)], marker="x", s=110, label="k-Means, k=5")
    axis.scatter([5], [mean_centroid_error(values, medoids)], marker="+", s=130, label="k-Medoids, k=5")
    axis.set(xlabel="Число кластеров k", ylabel="Среднее расстояние до центроида", xticks=list(range(3, 10)))
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "comparison_with_partitioning.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
