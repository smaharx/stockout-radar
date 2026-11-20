# Stockout Radar notebooks

These notebooks document the data preparation, exploratory analysis, feature engineering, baseline evaluation and model experimentation for Stockout Radar.

## Execution order

1. `01_cleaning.ipynb` — load the UCI workbook, combine its sheets, clean transaction rows and save `data/processed/clean_transactions.csv`.
2. `02_aggregation.ipynb` — aggregate cleaned transactions to a regular product-by-week panel and save `data/processed/weekly_panel.csv`.
3. `03_eda.ipynb` — explore weekly demand, zero-sales weeks, product activity and product history.
4. `04_features.ipynb` — construct the 16 predictors and four-week aggregate target; save `data/processed/model_table.csv`.
5. `05_split_baselines.ipynb` — use the same chronological split helper as the production training code and evaluate simple baselines.
6. `06_models.ipynb` — run exploratory candidate-model experiments, grouped time-series cross-validation and error analysis. It does not overwrite saved project model artifacts.

## Dataset

Download **Online Retail II** from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/502/online+retail). The dataset is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Place the downloaded workbook at:

`data/raw/online_retail_II.xlsx`

The raw workbook and generated CSV files are deliberately not tracked in Git. The dataset is not included in the teacher-submission ZIP; the source URL and required local path are provided here.

## Environment

From the repository root, install the notebook dependencies:

```bash
python -m pip install -r requirements-notebooks.txt
```

Then launch Jupyter from the notebooks directory so the notebooks' relative paths (such as `../data/raw/...`) work:

```bash
cd notebooks
jupyter lab
```

Use Python 3.12 and retain the pinned NumPy, pandas, scikit-learn and joblib versions in `requirements-backend.txt`. They are aligned with the saved model artifact's runtime.

## Relationship to the production implementation

The production feature definitions and inference feature validation live in `src/stockout_radar/features.py`. The official chronological split, candidate model configurations, model selection and training report are implemented in `src/stockout_radar/training.py`. The final served model is `models/stockout_radar_v1.joblib`.

Notebook 06 documents experiments and is not itself the authoritative source for the released production artifact. It deliberately avoids saving over either `models/gb_model.joblib` or `models/stockout_radar_v1.joblib`. The residual quantile shown at the end is exploratory and is not the application's operator-provided safety-stock value.

## Reproducibility note

Run notebooks 01–04 in order to rebuild the local data artifacts. Notebooks 05–06 then use the resulting `model_table.csv`. The production training script writes the authoritative model artifact and `reports/metrics/training_evaluation.json`; do not run model-retraining cells against production data or deployment environments without first reviewing the consequences.
