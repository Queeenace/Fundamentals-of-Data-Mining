"""Разделительная кластеризация клиентов банка."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


FEATURES = ("Age", "Education", "YearsEmployed", "Income", "CardDebt", "OtherDebt", "DebtIncomeRatio")
DEFAULT_DATA = Path(__file__).parent / "data" / "customers.csv"


@dataclass
class ClusterResult:
    labels: np.ndarray
    representatives: np.ndarray
    error: float
    objective: float


def load_customers(path: Path) -> tuple[np.ndarray, list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("Набор данных пуст")
    try:
        values = np.array([[float(row[name]) for name in FEATURES] for row in rows], dtype=float)
        ids = [row["CustomerId"] for row in rows]
    except (KeyError, ValueError) as exc:
        raise ValueError("В файле отсутствуют необходимые числовые признаки") from exc
    if not np.isfinite(values).all():
        raise ValueError("Признаки должны быть конечными числами")
    return values, ids


def add_noise(values: np.ndarray, fraction: float, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    if not 0 <= fraction <= 1:
        raise ValueError("Доля шума должна находиться в интервале [0, 1]")
    result = values.copy()
    count = round(len(values) * fraction)
    changed = np.zeros(len(values), dtype=bool)
    if count == 0:
        return result, changed
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(values), count, replace=False)
    changed[indices] = True
    # Для каждого выбранного клиента изменяем один или несколько признаков.
    scales = np.std(values, axis=0)
    for index in indices:
        columns = rng.choice(values.shape[1], rng.integers(1, values.shape[1] + 1), replace=False)
        result[index, columns] += rng.normal(0, 0.5 * scales[columns])
    return result, changed


def _medoids(distances: np.ndarray, k: int, seed: int, restarts: int = 4) -> tuple[np.ndarray, np.ndarray, float]:
    n = len(distances)
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        centers = rng.choice(n, k, replace=False)
        for _ in range(100):
            labels = np.argmin(distances[:, centers], axis=1)
            updated = centers.copy()
            for cluster in range(k):
                members = np.flatnonzero(labels == cluster)
                if len(members):
                    local = distances[np.ix_(members, members)].sum(axis=1)
                    updated[cluster] = members[np.argmin(local)]
                else:
                    free = np.setdiff1d(np.arange(n), updated, assume_unique=False)
                    updated[cluster] = free[np.argmax(np.min(distances[np.ix_(free, updated)], axis=1))]
            if np.array_equal(updated, centers):
                break
            centers = updated
        labels = np.argmin(distances[:, centers], axis=1)
        cost = float(distances[np.arange(n), centers[labels]].sum())
        if best is None or cost < best[2]:
            best = centers.copy(), labels.copy(), cost
    assert best is not None
    return best


def cluster(values: np.ndarray, k: int, algorithm: str, seed: int = 42) -> ClusterResult:
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("Нужна двумерная матрица конечных чисел")
    if not 2 <= k <= len(values):
        raise ValueError("Число кластеров должно быть от 2 до числа объектов")
    if algorithm == "kmeans":
        model = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(values)
        labels = model.labels_
        centers = model.cluster_centers_
        objective = float(model.inertia_)
    elif algorithm == "kmedoids":
        distances = cdist(values, values)
        indices, labels, objective = _medoids(distances, k, seed)
        centers = values[indices]
    else:
        raise ValueError("Алгоритм: kmeans или kmedoids")
    # Общая ошибка позволяет сравнить алгоритмы при одинаковом масштабе признаков.
    error = float(np.linalg.norm(values - centers[labels], axis=1).mean())
    return ClusterResult(labels, centers, error, objective)


def write_assignments(path: Path, ids: list[str], values: np.ndarray, labels: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(("CustomerId", *FEATURES, "Cluster"))
        for item_id, coordinates, label in zip(ids, values, labels):
            writer.writerow((item_id, *coordinates, int(label) + 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--algorithm", choices=("kmeans", "kmedoids"), required=True)
    parser.add_argument("--noise", type=float, default=0, help="Доля изменяемых объектов, от 0 до 1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, help="CSV с координатами и кластерами")
    args = parser.parse_args()
    original, ids = load_customers(args.data)
    values, changed = add_noise(original, args.noise, args.seed)
    scaled = StandardScaler().fit(original).transform(values)
    result = cluster(scaled, args.k, args.algorithm, args.seed)
    print(f"Объектов: {len(values)}; изменено шумом: {changed.sum()}")
    print(f"Алгоритм: {args.algorithm}; k={args.k}; средняя ошибка: {result.error:.6f}")
    print(f"Целевая функция алгоритма: {result.objective:.6f}")
    if args.output:
        write_assignments(args.output, ids, values, result.labels)
        print(f"Координаты и кластеры: {args.output}")
    else:
        writer = csv.writer(__import__("sys").stdout)
        writer.writerow(("CustomerId", *FEATURES, "Cluster"))
        for item_id, coordinates, label in zip(ids, values, result.labels):
            writer.writerow((item_id, *coordinates, int(label) + 1))


if __name__ == "__main__":
    main()
