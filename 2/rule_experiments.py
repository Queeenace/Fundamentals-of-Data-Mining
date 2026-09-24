"""Эксперименты с порогом достоверности ассоциативных правил."""
import csv
import json
import platform
import random
import statistics
import time
from pathlib import Path

from apriori import format_rules, generate_rules, mine, read_baskets
from plots import save_rule_charts

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / 'data/baskets.csv'
    baskets = read_baskets(source)
    support_percent = 1
    confidence_thresholds = list(range(20, 51, 5))
    repeats = 100
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)

    # Частые наборы не зависят от confidence, поэтому Apriori запускается один раз.
    found, levels = mine(baskets, f'{support_percent}%')
    for threshold in confidence_thresholds:
        generate_rules(found, len(baskets), f'{threshold}%')

    schedule = confidence_thresholds * repeats
    random.Random(42).shuffle(schedule)
    timings = {threshold: [] for threshold in confidence_thresholds}
    for threshold in schedule:
        start = time.perf_counter_ns()
        generate_rules(found, len(baskets), f'{threshold}%')
        timings[threshold].append((time.perf_counter_ns() - start) / 1e6)

    summary = []
    for threshold in confidence_thresholds:
        rules = generate_rules(found, len(baskets), f'{threshold}%',
                               max_total_length=7)
        values = timings[threshold]
        summary.append({
            'confidence_percent': threshold,
            'median_ms': statistics.median(values),
            'min_ms': min(values),
            'max_ms': max(values),
            'rules': len(rules),
        })
        for order in ['support', 'lex']:
            ordered = generate_rules(found, len(baskets), f'{threshold}%', order, 7)
            (results / f'rules_{threshold:02d}_{order}.json').write_text(
                json.dumps(ordered, ensure_ascii=False, indent=2) + '\n',
                encoding='utf-8')

    # Для содержательного анализа используем компактный список из 19 правил.
    analysis_rules = generate_rules(found, len(baskets), '40%', 'support', 7)
    (results / 'rules_analysis_40_support.json').write_text(
        json.dumps(analysis_rules, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    (results / 'rules_analysis_40.txt').write_text(
        format_rules(analysis_rules) + '\n', encoding='utf-8')
    with (results / 'rule_timings.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['confidence_percent', 'repeat', 'time_ms'])
        for threshold in confidence_thresholds:
            writer.writerows((threshold, index + 1, value)
                             for index, value in enumerate(timings[threshold]))

    metadata = {
        'transactions': len(baskets),
        'support_percent': support_percent,
        'confidence_thresholds_percent': confidence_thresholds,
        'repeats': repeats,
        'shuffle_seed': 42,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'frequent_itemsets': len(found),
        'maximum_itemset_length': max(map(len, found), default=0),
        'apriori_levels': levels,
        'analysis_confidence_percent': 40,
        'analysis_rule_count': len(analysis_rules),
        'summary': summary,
    }
    (results / 'rule_experiments.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    save_rule_charts(summary)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
