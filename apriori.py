"""Поиск частых наборов и ассоциативных правил алгоритмом Apriori."""
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from itertools import combinations
from pathlib import Path


def parse_support(value):
    """Читаем порог как долю (0.03) или процент (3%)."""
    try:
        s = str(value).strip()
        result = Decimal(s[:-1]) / 100 if s.endswith('%') else Decimal(s)
        if not result.is_finite() or not 0 < result <= 1:
            raise ValueError
        return result
    except (InvalidOperation, ValueError):
        raise ValueError('Support must be in (0, 1], for example 0.03 or 3%.') from None


def read_baskets(path, encoding='auto'):
    raw = Path(path).read_bytes()
    if encoding == 'auto':
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1251')
    else:
        text = raw.decode(encoding)
    import io
    # Заголовка нет. Убираем повторы товаров, сохраняя отдельные покупки.
    rows = [frozenset(x.strip() for x in row if x.strip())
            for row in csv.reader(io.StringIO(text))]
    baskets = [row for row in rows if row]
    if not baskets:
        raise ValueError('Dataset contains no nonempty baskets.')
    return baskets


def mine(baskets, support):
    """Return {sorted item tuple: absolute count} and per-level diagnostics.

    Join frequent (k-1)-sets sharing a prefix, prune when any (k-1)-subset
    is infrequent, count via intersection of parent transaction masks.
    """
    support = parse_support(support)
    n = len(baskets)
    if not n:
        raise ValueError('Dataset contains no baskets.')
    # Округляем вверх: набор должен достигать заданной доли корзин.
    minimum = int((support * n).to_integral_value(rounding=ROUND_CEILING))
    masks = {}
    # Каждый бит показывает присутствие товара в конкретной корзине.
    for index, basket in enumerate(baskets):
        bit = 1 << index
        for item in set(basket):
            masks[item] = masks.get(item, 0) | bit
    # Начинаем с частых одиночных товаров.
    level = {(item,): mask for item, mask in masks.items()
             if mask.bit_count() >= minimum}
    diagnostics = [{'length': 1, 'candidates': len(masks), 'frequent': len(level)}]
    found = {items: mask.bit_count() for items, mask in level.items()}
    k = 2
    while level:
        keys = sorted(level)
        next_level = {}
        candidates = 0
        for i, left in enumerate(keys):
            for right in keys[i + 1:]:
                if left[:-1] != right[:-1]:
                    break
                # Объединяем наборы с одинаковым префиксом.
                candidate = left + (right[-1],)
                # Отсекаем кандидата, если хотя бы одно подмножество нечастое.
                if any(subset not in level for subset in combinations(candidate, k - 1)):
                    continue
                candidates += 1
                # Пересечение масок даёт корзины со всеми товарами кандидата.
                mask = level[left] & level[right]
                count = mask.bit_count()
                if count >= minimum:
                    next_level[candidate] = mask
                    found[candidate] = count
        diagnostics.append({'length': k, 'candidates': candidates,
                            'frequent': len(next_level)})
        level = next_level
        k += 1
    return found, diagnostics


def result_rows(found, n, order='support'):
    if order not in ('support', 'lex'):
        raise ValueError('Unknown ordering.')
    # При равной поддержке используем лексикографический порядок.
    keys = sorted(found, key=(lambda x: (-found[x], x)) if order == 'support' else None)
    return [{'items': list(key), 'length': len(key), 'count': found[key],
             'support': found[key] / n} for key in keys]


def generate_rules(found, n, confidence, order='support', max_total_length=None):
    """Строим правила A -> B из частых наборов и считаем support и confidence."""
    confidence = parse_support(confidence)
    if order not in ('support', 'lex'):
        raise ValueError('Unknown ordering.')
    if max_total_length is not None and max_total_length < 2:
        raise ValueError('Maximum rule length must be at least 2.')
    rules = []
    for itemset, count in found.items():
        if len(itemset) < 2:
            continue
        if max_total_length is not None and len(itemset) > max_total_length:
            continue
        # Каждое непустое собственное подмножество становится антецедентом.
        for length in range(1, len(itemset)):
            for antecedent in combinations(itemset, length):
                antecedent = tuple(sorted(antecedent))
                consequent = tuple(item for item in itemset if item not in antecedent)
                rule_confidence = count / found[antecedent]
                if rule_confidence < confidence:
                    continue
                readable = f"{', '.join(antecedent)} → {', '.join(consequent)}"
                rules.append({
                    'antecedent': list(antecedent),
                    'consequent': list(consequent),
                    'rule': readable,
                    'total_length': len(itemset),
                    'count': count,
                    'support': count / n,
                    'confidence': rule_confidence,
                })
    if order == 'support':
        rules.sort(key=lambda row: (-row['support'], -row['confidence'],
                                    row['antecedent'], row['consequent']))
    else:
        rules.sort(key=lambda row: (row['antecedent'], row['consequent']))
    return rules


def format_rules(rules):
    """Возвращаем компактный удобочитаемый список правил."""
    if not rules:
        return 'Ассоциативные правила не найдены.'
    return '\n'.join(
        f"{row['rule']} | поддержка: {row['support']:.4%} | "
        f"достоверность: {row['confidence']:.4%}"
        for row in rules
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--support', required=True, help='0.03 or 3%%')
    parser.add_argument('--confidence', required=True, help='0.4 or 40%%')
    parser.add_argument('--order', choices=['support', 'lex'], default='support')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    parser.add_argument('--max-rule-length', type=int)
    parser.add_argument('--encoding', default='auto')
    parser.add_argument('--output', type=Path, help='JSON output; default: stdout')
    args = parser.parse_args()
    try:
        baskets = read_baskets(args.dataset, args.encoding)
        found, levels = mine(baskets, args.support)
        rules = generate_rules(found, len(baskets), args.confidence, args.order,
                               args.max_rule_length)
    except (ValueError, OSError, UnicodeError) as error:
        parser.error(str(error))
    payload = {'transactions': len(baskets),
               'support_threshold': str(parse_support(args.support)),
               'confidence_threshold': str(parse_support(args.confidence)),
               'order': args.order, 'levels': levels,
               'itemsets': result_rows(found, len(baskets), args.order),
               'rules': rules}
    text = (json.dumps(payload, ensure_ascii=False, indent=2)
            if args.format == 'json' else format_rules(rules))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    else:
        print(text)


if __name__ == '__main__':
    main()
