import itertools
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auction_helpers as h


def frame(n=600, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(dict(
        age=rng.integers(0, 12, n), mileage=rng.uniform(1e4, 2e5, n), benchmark=rng.uniform(3e3, 3e4, n),
        floor_ratio=rng.uniform(.5, 1.3, n), make=rng.choice(['a', 'b', None], n),
        condition=rng.choice(['x', 'y'], n), location=rng.choice(['p', 'q'], n),
        seller_group=rng.choice(['dealer', 'fleet'], n),
        auction_date=pd.Timestamp('2007-01-01') + pd.to_timedelta(rng.integers(0, 400, n), 'D')))


class OptimizerTests(unittest.TestCase):
    def test_matches_exhaustive_search(self):
        q = np.array([[.9, .5, .3], [.8, .6, .2], [.95, .7, .4]])
        v = np.array([[10, 15, 20], [9, 16, 21], [12, 17, 19]])
        choice, info = h.optimize(q, v, .65)
        best = max(sum(v[i, c[i]] for i in range(3)) for c in itertools.product(range(3), repeat=3)
                   if sum(q[i, c[i]] for i in range(3)) >= 3 * .65)
        self.assertAlmostEqual(v[np.arange(3), choice].sum(), best)
        self.assertEqual(info['status'], 0)

    def test_infeasible_target(self):
        choice, info = h.optimize(np.array([[.2, .4]]), np.array([[2, 3]]), .8)
        self.assertIsNone(choice)
        self.assertEqual(info['status'], 'infeasible')

    def test_value_accounting(self):
        d = pd.DataFrame(dict(known_sale_fee=[50.], retained_value=[900.], holding_cost=[30.]))
        out = h.value(np.array([[.5]]), np.array([[1000.]]), d)
        self.assertAlmostEqual(out[0, 0], 1000 - .5 * 50 + .5 * (900 - 30))


class SplitAndSupportTests(unittest.TestCase):
    def test_chronological_split(self):
        a, b, c = h.split_dates(frame())
        self.assertLess(a.auction_date.max(), b.auction_date.min())
        self.assertLess(b.auction_date.max(), c.auction_date.min())
        self.assertEqual(len(a) + len(b) + len(c), 600)

    def test_candidates_stay_within_supported_bounds(self):
        d = frame(2000)
        maps = h.support_fit(d)
        grid, _ = h.candidates(d.head(50), maps, None, None)
        lo, hi, _ = h.bounds_for(d.head(50), maps)
        self.assertTrue((grid >= lo[:, None] - 1e-12).all() and (grid <= hi[:, None] + 1e-12).all())


class ModelHelperTests(unittest.TestCase):
    def test_features_exclude_outcomes_and_fill_missing(self):
        d = frame().assign(sold=1, price=1.0)
        cols = ['age', 'log_mileage', 'log_benchmark', 'month_sin', 'month_cos', 'floor_ratio',
                'make', 'condition', 'location', 'seller_group']
        x = h.make_features(d, pd.Timestamp('2006-11-01'), ['make', 'condition', 'location', 'seller_group'], cols)
        self.assertEqual(list(x.columns), cols)
        self.assertNotIn('None', set(x.make))
        self.assertIn('<missing>', set(x.make))

    def test_spline_is_linear_basis_plus_nonlinear_terms(self):
        s = h.RestrictedCubicSpline((.1, .5, .9)).fit(np.linspace(0, 1, 100))
        out = s.transform(np.linspace(0, 1, 5))
        self.assertEqual(out.shape, (5, 2))
        with self.assertRaises(ValueError):
            h.RestrictedCubicSpline().fit(np.zeros(50))

    def test_correction_modes(self):
        rng = np.random.default_rng(1)
        q = rng.uniform(.1, .9, 2000)
        g = rng.choice(['dealer', 'fleet'], 2000)
        y = rng.binomial(1, np.clip(q * .7, 0, 1))
        np.testing.assert_array_equal(h.correct(h.fit_correction('raw', q, g, y), q, g), q)
        fixed = h.correct(h.fit_correction('global_sigmoid', q, g, y), q, g)
        self.assertLess(abs(fixed.mean() - y.mean()), abs(q.mean() - y.mean()))
        with self.assertRaises(ValueError):
            h.correct(h.fit_correction('group_sigmoid', q, g, y), q[:2], np.array(['dealer', 'new']))


if __name__ == '__main__':
    unittest.main()
