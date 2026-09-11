"""Reproduce mining experiments; timing excludes CSV reading, sorting and export."""
import csv
import hashlib
import json
import platform
import random
import statistics
import time
from collections import Counter
from itertools import combinations
from pathlib import Path
from apriori import mine, read_baskets, result_rows

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / 'data/baskets.csv'
    baskets = read_baskets(source)
    thresholds = [1, 3, 5, 10, 15]
    repeats = 15
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    for threshold in thresholds:
        mine(baskets, f'{threshold}%')  # Один прогрев перед измерениями.
    schedule = thresholds * repeats
    # Перемешиваем запуски, чтобы уменьшить влияние порядка порогов.
    random.Random(42).shuffle(schedule)
    timings = {s: [] for s in thresholds}
    for threshold in schedule:
        # Измеряем только построение масок и поиск частых наборов.
        start = time.perf_counter_ns()
        found, levels = mine(baskets, f'{threshold}%')
        timings[threshold].append((time.perf_counter_ns() - start) / 1e6)
    summary = []
    # Независимо считаем комбинации товаров прямым перебором корзин.
    all_found, _ = mine(baskets, '1%')
    maximum = max(map(len, all_found), default=0)
    brute = Counter(items for basket in baskets for k in range(1, maximum + 1)
                    for items in combinations(sorted(basket), k))
    for threshold in thresholds:
        found, levels = mine(baskets, f'{threshold}%')
        minimum = (len(baskets) * threshold + 99) // 100
        assert found == {key: count for key, count in brute.items() if count >= minimum}
        lengths = Counter(map(len, found))
        values = timings[threshold]
        summary.append({'threshold_percent': threshold, 'minimum_count': minimum,
                        'median_ms': statistics.median(values), 'min_ms': min(values),
                        'max_ms': max(values), 'total': len(found),
                        'by_length': dict(sorted(lengths.items())), 'levels': levels})
        # Сохраняем полный результат в обоих вариантах сортировки.
        for order in ['support', 'lex']:
            (results / f'itemsets_{threshold:02d}_{order}.json').write_text(
                json.dumps(result_rows(found, len(baskets), order), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (results / 'timings.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['threshold_percent', 'repeat', 'time_ms'])
        for threshold in thresholds:
            writer.writerows((threshold, i + 1, value) for i, value in enumerate(timings[threshold]))
    metadata = {'transactions': len(baskets), 'unique_items': len(set().union(*baskets)),
                'mean_length': statistics.mean(map(len, baskets)), 'max_length': max(map(len, baskets)),
                'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'python': platform.python_version(), 'platform': platform.platform(),
                'processor': platform.processor(), 'repeats': repeats, 'shuffle_seed': 42,
                'verification': 'Horizontal exhaustive counting through maximum frequent length matched all thresholds.',
                'summary': summary}
    (results / 'experiments.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
