import random
import tempfile
import unittest
from itertools import combinations
from pathlib import Path
from apriori import (format_rules, generate_rules, mine, parse_support,
                     read_baskets, result_rows)


class AprioriTests(unittest.TestCase):
    def test_against_exhaustive_search(self):
        rng = random.Random(42)
        for _ in range(20):
            baskets = [{x for x in 'abcdef' if rng.random() < .5} for _ in range(17)]
            for threshold in ['1%', '30%', '100%']:
                expected = {}
                for k in range(1, 7):
                    for items in combinations('abcdef', k):
                        count = sum(set(items) <= basket for basket in baskets)
                        if count >= parse_support(threshold) * len(baskets):
                            expected[items] = count
                self.assertEqual(mine(baskets, threshold)[0], expected)

    def test_boundary(self):
        baskets = [{'a'}] * 7 + [{'b'}] * 93
        self.assertIn(('a',), mine(baskets, '7%')[0])
        self.assertNotIn(('a',), mine(baskets, '7.001%')[0])

    def test_input_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'b.csv'
            path.write_bytes('яйца,яйца,молоко\n\nяйца\n'.encode('cp1251'))
            baskets = read_baskets(path)
        found, _ = mine(baskets, '50%')
        self.assertEqual(found[('яйца',)], 2)
        self.assertEqual(len(baskets), 2)
        for order in ['support', 'lex']:
            rows = result_rows(found, 2, order)
            key = (lambda r: (-r['count'], r['items'])) if order == 'support' else (lambda r: r['items'])
            self.assertEqual(rows, sorted(rows, key=key))

    def test_invalid(self):
        for value in ['0', '-1', '101%', 'nan', 'inf', 'abc']:
            with self.assertRaises(ValueError):
                parse_support(value)
        with self.assertRaises(ValueError):
            mine([], '.1')

    def test_association_rules(self):
        baskets = [{'a', 'b'}, {'a', 'b'}, {'a', 'c'}, {'b', 'c'}]
        found, _ = mine(baskets, '50%')
        rules = generate_rules(found, len(baskets), '60%', 'support')
        self.assertEqual([row['rule'] for row in rules], ['a → b', 'b → a'])
        self.assertTrue(all(row['support'] == .5 for row in rules))
        self.assertTrue(all(abs(row['confidence'] - 2 / 3) < 1e-12
                            for row in rules))
        self.assertIn('достоверность', format_rules(rules))

    def test_rule_order_and_length_limit(self):
        baskets = [{'a', 'b', 'c'}, {'a', 'b', 'c'}, {'a', 'b'}, {'a'}]
        found, _ = mine(baskets, '25%')
        lex = generate_rules(found, len(baskets), '1%', 'lex', 2)
        self.assertTrue(all(row['total_length'] <= 2 for row in lex))
        keys = [(row['antecedent'], row['consequent']) for row in lex]
        self.assertEqual(keys, sorted(keys))


if __name__ == '__main__':
    unittest.main()
