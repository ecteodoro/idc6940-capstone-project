# Vehicle auction floor optimization — IDC6940

The week 6 **Introduction and Methods** is the governing specification. The original proposal is background only. This project uses public Larsen data and generated synthetic records; **no employer data or employer-derived summaries are used**.

## Start here

Use Python 3.12 and the project environment:

```sh
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m jupyterlab
```

For a fresh environment, first run `python3 -m venv .venv`. Select that environment as the notebook kernel. Run notebooks from the `idc6940-capstone-project` directory. The lock file records tested packages; `requirements.txt` states compatibility ranges.

## Notebook workflow

| Notebook | Role |
|---|---|
| `01_larsen_source_audit.ipynb` | Validate public source fields, missingness, eligibility, and distributions. |
| `02_calibration_and_simulation.ipynb` | Fit calibration models and generate 50,000 vehicles per initial scenario. |
| `03_train_and_evaluate.ipynb` | Original chronological prediction-model comparison and test diagnostics. |
| `04_probability_calibration.ipynb` | Supplementary probability repair using separately generated target-period labeled cohorts. |
| `05_single_run_policy_study.ipynb` | Primary chronological prediction/optimization study, oracle, replications, sensitivities, and bootstrap. |
| `06_study_results_and_report.ipynb` | Methods-aligned results: source and synthetic distributions, calibration, prediction, optimization, uncertainty, 13 paper figures, oracle checks, and report. |

Run 01–03 before 05–06. Notebook 06 has a `PAPER` flag in its first plotting cell: `True` (default) writes untitled, print-sized figures to `paper/figures/`; `False` writes the full-size titled figures to `data/study/figures/`. Notebook 04 addresses a separate representative-cohort calibration question: it does not demonstrate forecasting without target-period labels. Notebook 05 therefore selects its primary correction using chronological validation only. Notebook 03 remains the original baseline, not the corrected supplementary model.

`auction_project.ipynb` is the superseded, uncalibrated demonstration. Its outputs are not capstone findings.

## Data and source protection

`Larsen_used_car_bargaining_data_and_code/` is the original read-only source archive. It is never rewritten by these notebooks. Source-file hashes are retained and verified. Dealer and fleet/lease observations are modeled separately during calibration. `idnew` is a run identifier, not a vehicle-history link.

All generated material goes under `data/`:

- `source_audit/`: source diagnostics, field mappings, and eligibility counts.
- `calibration/`: fitted calibration models, coefficients, assumptions, comparison tables, metadata, and the synthetic data dictionary.
- `synthetic/`: observable scenario CSVs and a separate `evaluation_only.csv`; independent calibration cohorts have their own subdirectory.
- `training/binding_historical/`: initial train/validation/test splits and predictive results.
- `training/calibration_repair/`: supplementary corrected model and independent-cohort diagnostics. `final_*` files contain its final verification.
- `study/`: primary study checkpoints, policy results, numerical checks, uncertainty tables, figures, and `study_report.md`.
- `study_initial_checks/`: superseded pilot checkpoints; do not combine them with final study results.
- `demo/` and `notebook_demo/`: earlier uncalibrated demonstrations.

Never use `evaluation_only.csv`, private signals, true generator probabilities, current-run high bids, or realized outcomes as predecision predictors. The study oracle integrates unobserved signals; it does not observe their realized values.

## Single-run study design

The full run includes 30 independently generated and refitted datasets for each of four main scenarios: binding/bargaining prices crossed with historical/randomized floors. Each main dataset has 50,000 vehicles. Date-preserving splits are approximately 60% training, 20% validation, and 20% testing. Prediction diagnostics use the test split; policy evaluation uses a seeded random portfolio of 200 test vehicles per replication.

The optimizer and oracle face identical supported candidate sets. Candidate support uses training seller-group/condition/age cells, with documented fallbacks and assumed operational limits. The supported assigned-floor baseline clips reference floors outside these bounds and is named accordingly. The candidate set remains fixed across conversion targets.

Nine single-factor sensitivities have 30 paired refits each: low/high holding costs, low/high retained values, a 10,000-vehicle sample, absent/stronger private information, and weak/strong demand. Five hundred date-block bootstrap resamples refit the models and recompute policies on a fixed test portfolio. Four isolated computational workers process independent tasks; the run checkpoints completed work.

If changing the study specification, relocate or remove the affected **generated** checkpoint directory before rerunning notebook 05. Existing checkpoints are intentionally reused. Never remove or edit the source archive to restart an analysis.

## Interpretation and limits

These are simulated outcomes, not evidence of actual auction improvements. Calibration matches selected source distributions and moments; full price distributions still differ, particularly where binding floors exclude below-reserve transactions observed in bargaining. Make is an available vehicle category, not a verified segment classification. Costs, private-information effects, the causal floor response, and the high-bid mechanism retain stated assumptions.

A predicted expected-conversion constraint does not guarantee actual conversion or calibrated intervention effects. Report true expected feasibility and realized target failures separately. Feasible paired comparisons and all-pair comparisons are separate tables. Oracle integration is approximate and accompanied by resolution checks and independent Monte Carlo checks; near-boundary feasibility is flagged.

The single-run study does not implement repeated auctions, which the Methods explicitly defers. Model and calibration `.pkl`/`.joblib` files are for trusted local reuse only.

## Source attribution

B. J. Larsen, “The efficiency of real-world bargaining: Evidence from wholesale used-auto auctions,” *Review of Economic Studies*, 88(2), 851–882, 2021. Variable interpretation follows the copied replication `Readme.pdf` and `step1_regression.do`. Original public records are not relabeled as synthetic records or exported with source identifiers.
