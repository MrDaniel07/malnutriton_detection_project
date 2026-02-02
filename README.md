# Early Malnutrition Detection (Prototype)

This workspace contains a small prototype for experimenting with a logistic regression model to detect early malnutrition risk in young children. It is intended as a demo and educational tool — not a clinical system.

Files added:
- `app.py` — Streamlit interactive app to train and test the model
- `data_utils.py` — synthetic data generator and CSV loader
- `models.py` — training, evaluation, and single-prediction helpers
- `requirements.txt` — Python package requirements

Quick start:

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the interactive app:

```bash
streamlit run app.py
```

Notes:
- The app supports synthetic data (for quick prototyping) or CSV upload. If you supply a CSV, make sure it contains the same feature columns used by the app (see `data_utils.generate_synthetic_data` for names).
- This implementation is a prototype. For production or health use, obtain appropriate data governance approvals, validate on real clinical datasets, and consult domain experts.
