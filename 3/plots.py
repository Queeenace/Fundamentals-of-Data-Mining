"""Диаграммы качества и читаемые схемы верхних уровней деревьев."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

METRICS = {"accuracy": "Аккуратность", "precision": "Точность",
           "recall": "Полнота", "f1": "F-мера"}


def quality_chart(rows, path: Path):
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 12})
    fig, ax = plt.subplots(figsize=(9, 5.2))
    xs = [row["train_share"] * 100 for row in rows]
    styles = ("-o", "--s", "-.^", ":D")
    for (key, label), style in zip(METRICS.items(), styles):
        ax.plot(xs, [row["quality"][key] * 100 for row in rows], style,
                color="black", label=label)
    ax.set(xlabel="Доля обучающей выборки, %", ylabel="Значение показателя, %",
           xticks=xs, ylim=(40, 100))
    ax.grid(alpha=.25)
    ax.legend(ncol=2, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def tree_chart(tree: dict, title: str, path: Path, levels=2):
    """Показывает первые уровни; полный состав дерева сохранён в JSON."""
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10})
    fig, ax = plt.subplots(figsize=(14, 6.8))
    ax.axis("off")

    def visit(node, depth, x, span, parent=None, edge=""):
        y = 1 - depth / (levels + .25)
        if parent is not None:
            ax.plot([parent[0], x], [parent[1] - .055, y + .055], color="black", lw=.8)
            ax.text((parent[0] + x) / 2, (parent[1] + y) / 2, edge,
                    ha="center", va="center", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
        if "feature" in node:
            feature = node["feature"].replace("numeric__", "").replace("category__", "")
            label = f"{feature} ≤ {node['threshold']:.1f}\nn={node['count']}, >50K={node['positive']}"
        else:
            label = f"{node['prediction']}\nn={node['count']}"
        if depth == levels and "feature" in node:
            label += "\n(ветвь продолжается)"
        ax.text(x, y, label, ha="center", va="center", fontsize=13,
                bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "black"})
        if depth < levels and "feature" in node:
            visit(node["left"], depth + 1, x - span, span / 2, (x, y), "да")
            visit(node["right"], depth + 1, x + span, span / 2, (x, y), "нет")

    visit(tree, 0, .5, .245)
    ax.set_xlim(-.03, 1.03)
    ax.set_ylim(-.05, 1.12)
    ax.set_title(title, fontsize=16, pad=10)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
