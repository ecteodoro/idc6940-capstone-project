import itertools
import unittest
import numpy as np
import ast
import json
from pathlib import Path

notebook = json.loads((Path(__file__).resolve().parents[1] / 'auction_project.ipynb').read_text())
for cell in notebook['cells']:
    if cell['cell_type'] != 'code':
        continue
    source = ''.join(cell['source'])
    parsed = ast.parse(source)
    if any(isinstance(node, ast.ClassDef) for node in parsed.body):
        continue
    definitions = [node for node in parsed.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    exec(compile(ast.Module(body=definitions, type_ignores=[]), '<notebook definitions>', 'exec'), globals())
FEATURES = ['age', 'mileage', 'condition', 'floor_ratio']


class ProjectTests(unittest.TestCase):
    def test_optimizer_matches_exhaustive_search(self):
        q = np.array([[.9,.5,.3],[.8,.6,.2],[.95,.7,.4]])
        v = np.array([[10,15,20],[9,16,21],[12,17,19]])
        choice, metadata = optimize(q,v,.65)
        feasible = [sum(v[i,c[i]] for i in range(3)) for c in itertools.product(range(3),repeat=3) if sum(q[i,c[i]] for i in range(3))>=3*.65]
        self.assertAlmostEqual(v[np.arange(3),choice].sum(),max(feasible))
        self.assertEqual(metadata['status'],0)
    def test_infeasible_target(self):
        choice, status = optimize(np.array([[.2,.4]]),np.array([[2,3]]),.8)
        self.assertIsNone(choice)
        self.assertEqual(status['status'],'infeasible')
    def test_generator_and_temporal_split(self):
        df = simulate(2000,42)
        self.assertTrue(df.equals(simulate(2000,42)))
        self.assertTrue(df.loc[df.sold.eq(0),'price'].isna().all())
        sold = df[df.sold.eq(1)]
        self.assertTrue((sold.price>=sold.floor_ratio*sold.benchmark).all())
        a,b,c = split_dates(df)
        self.assertLess(a.auction_date.max(),b.auction_date.min())
        self.assertLess(b.auction_date.max(),c.auction_date.min())
    def test_response_and_cost_accounting(self):
        frame = simulate(1000,1).iloc[:2]
        ratios=np.array([[.7,1.1],[.7,1.1]])
        q,p=responses(frame,ratios)
        self.assertTrue((q[:,0]>q[:,1]).all())
        self.assertTrue((p[:,0]<p[:,1]).all())
        np.testing.assert_allclose(seller_value(np.array([0,1]),np.array([1000,1000]),np.array([900,900]),50,30,.8),[690,950])

if __name__ == '__main__':
    unittest.main()
