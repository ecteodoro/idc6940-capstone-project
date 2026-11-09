"""Export the generated replication datasets of the main policy study.

The study (notebook 05) generates each replication in memory from its seed and
keeps only results. This script re-runs the same generator, with the same
seeds, and writes the vehicle-level data:

  data/datasets/<scenario>/rep_NN.csv.gz                   observable fields
  data/datasets/<scenario>/rep_NN_evaluation_only.csv.gz   latent signals and true probabilities
  data/datasets/manifest.csv                               seeds, sizes, checksums

Usage (from the project directory):
  python scripts/export_datasets.py             # all four main scenarios, 30 replications
  python scripts/export_datasets.py --reps 2    # quick test
  python scripts/export_datasets.py --verify    # also refit replication 0 and compare with the stored study metrics
"""
import argparse, hashlib, json, os, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # notebook cells use paths relative to the project directory
MAIN = [('binding', 'historical'), ('binding', 'randomized'), ('bargaining', 'historical'), ('bargaining', 'randomized')]


def load_notebook_namespace():
    """Execute the setup, generator and refit cells of notebook 05 (not the study itself)."""
    nb = json.loads((ROOT / '05_single_run_policy_study.ipynb').read_text())
    wanted = ['OUT=Path(', 'def features(d)', 'def generate(', 'def refit(']
    ns = {}
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source'])
        if any(w in source for w in wanted):
            exec(compile(source, '<notebook 05>', 'exec'), ns)
    return ns


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reps', type=int, default=30)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    ns = load_notebook_namespace()
    out = ROOT / 'data' / 'datasets'
    rows = []
    for institution, assignment in MAIN:
        folder = out / f'{institution}_{assignment}'
        folder.mkdir(parents=True, exist_ok=True)
        for rep in range(args.reps):
            seed = 50000 + rep
            path = folder / f'rep_{rep:02}.csv.gz'
            evalpath = folder / f'rep_{rep:02}_evaluation_only.csv.gz'
            if not path.exists():
                vehicles, evaluation = ns['generate'](seed, institution, assignment, 50000)
                vehicles.to_csv(path, index=False, compression='gzip')
                evaluation.to_csv(evalpath, index=False, compression='gzip')
            else:
                vehicles = pd.read_csv(path)
            rows.append(dict(scenario=f'{institution}_{assignment}', replication=rep, seed=seed, n=len(vehicles),
                             conversion=float(vehicles.sold.mean()), file=str(path.relative_to(out)),
                             sha256=sha256(path), evaluation_file=str(evalpath.relative_to(out)), evaluation_sha256=sha256(evalpath)))
            print(institution, assignment, rep + 1, flush=True)
    pd.DataFrame(rows).to_csv(out / 'manifest.csv', index=False)
    if args.verify:
        vehicles = pd.read_csv(out / 'binding_historical' / 'rep_00.csv.gz', parse_dates=['auction_date'])
        train, val, test = ns['split_dates'](vehicles)
        model = ns['refit'](train, val, 'binding')
        q, _ = ns['predict'](model, test)
        from sklearn.metrics import log_loss
        stored = json.loads((ROOT / 'data' / 'study' / 'binding_historical' / 'metadata_00.json').read_text())['log_loss']
        print('refit test log loss', log_loss(test.sold, q), 'stored', stored)


if __name__ == '__main__':
    main()
