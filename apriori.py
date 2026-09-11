"""Apriori with vertical transaction bitsets. Mining requires only Python 3.10+."""
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from itertools import combinations
from pathlib import Path


def parse_support(value):
    """Accept a fraction (0.03) or a percentage (3%)."""
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
    # No header. Ignore physically blank rows; preserve repeated transactions.
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
    minimum = int((support * n).to_integral_value(rounding=ROUND_CEILING))
    masks = {}
    for index, basket in enumerate(baskets):
        bit = 1 << index
        for item in set(basket):
            masks[item] = masks.get(item, 0) | bit
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
                candidate = left + (right[-1],)
                if any(subset not in level for subset in combinations(candidate, k - 1)):
                    continue
                candidates += 1
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
    keys = sorted(found, key=(lambda x: (-found[x], x)) if order == 'support' else None)
    return [{'items': list(key), 'length': len(key), 'count': found[key],
             'support': found[key] / n} for key in keys]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--support', required=True, help='0.03 or 3%%')
    parser.add_argument('--order', choices=['support', 'lex'], default='support')
    parser.add_argument('--encoding', default='auto')
    parser.add_argument('--output', type=Path, help='JSON output; default: stdout')
    args = parser.parse_args()
    try:
        baskets = read_baskets(args.dataset, args.encoding)
        found, levels = mine(baskets, args.support)
    except (ValueError, OSError, UnicodeError) as error:
        parser.error(str(error))
    payload = {'transactions': len(baskets), 'threshold': str(parse_support(args.support)),
               'order': args.order, 'levels': levels,
               'itemsets': result_rows(found, len(baskets), args.order)}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    else:
        print(text)


if __name__ == '__main__':
    main()
