import io
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import roc_auc_score, roc_curve, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import joblib


def train_evaluate(df, feature_cols=None, target_col="malnourished", C=1.0, test_size=0.2, random_state=42):
    if feature_cols is None:
        feature_cols = [c for c in df.columns if c != target_col]

    # Drop rows with NaN in selected features or target
    df_clean = df[feature_cols + [target_col]].dropna()
    if len(df_clean) < 10:
        raise ValueError(f"Not enough clean samples after removing NaN: {len(df_clean)}")
    
    X = df_clean[feature_cols].values
    y = df_clean[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)

    model = LogisticRegression(C=C, solver="liblinear", class_weight="balanced", max_iter=1000)
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    auc = roc_auc_score(y_test, y_prob)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)

    # ROC figure
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    fig_roc, ax = plt.subplots(figsize=(6, 4))
    sns.lineplot(x=fpr, y=tpr, ax=ax)
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC curve (AUC = {auc:.3f})")

    # Feature coefficients
    coef = model.coef_.ravel()
    coef_df = pd.DataFrame({"feature": feature_cols, "coef": coef})
    coef_df = coef_df.reindex(coef_df.coef.abs().sort_values(ascending=False).index)

    metrics = {
        "auc": float(auc),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }

    return {
        "model": model,
        "metrics": metrics,
        "roc_fig": fig_roc,
        "feature_importance": coef_df,
        "X_test": X_test,
        "y_test": y_test,
        "feature_cols": feature_cols,
    }


def predict_single(model, feature_cols, values_dict):
    """Predict probability for a single example given a dict of feature values."""
    x = np.array([values_dict.get(c, 0) for c in feature_cols]).reshape(1, -1)
    prob = float(model.predict_proba(x)[:, 1])
    pred = int(model.predict(x)[0])
    return {"probability": prob, "prediction": pred}


def load_mics_child(sav_path):
    """Load a MICS child file (.sav) and return DataFrame + metadata."""
    import pyreadstat
    df, meta = pyreadstat.read_sav(sav_path)
    return df, meta


def preprocess_mics_child(df, states_include=(24.0, 37.0)):
    """Preprocess MICS child dataframe for Lagos/Abuja and build target.

    Returns a cleaned DataFrame with columns: age (AG2), weight (AN3), height (AN4),
    muac if present, breastfeeding/diarrhea indicators if present, and binary `any_mal`.
    """
    d = df.copy()
    if 'HH7' in d.columns:
        d = d[d['HH7'].isin(list(states_include))].copy()

    # ensure z-score columns exist
    for col in ['WHZ', 'HAZ', 'WAZ']:
        if col not in d.columns:
            d[col] = np.nan

    # composite malnutrition label
    d['wasting'] = d['WHZ'] < -2
    d['stunting'] = d['HAZ'] < -2
    d['underweight'] = d['WAZ'] < -2
    d['any_mal'] = (d['wasting'] | d['stunting'] | d['underweight']).astype(int)

    # Detect MUAC column heuristically
    muac_col = None
    for c in d.columns:
        if c.lower().startswith('muac') or 'muac' in c.lower():
            muac_col = c
            break

    # Detect sample weight column heuristically (chweight, sampleweight, weight)
    weight_col = None
    for c in d.columns:
        cl = c.lower()
        if cl in ('chweight', 'child_weight', 'childsampleweight'):
            weight_col = c
            break
    if weight_col is None:
        for c in d.columns:
            if c.lower().endswith('weight') or c.lower().endswith('wt'):
                weight_col = c
                break

    # Symptoms / feeding flags: try to include common MICS variables
    symptom_cols = {}
    # recent diarrhea often recorded as 'BD5' or similar - search by label would be better but do heuristics
    for c in d.columns:
        if any(k in c.lower() for k in ['diarr', 'diarrhoea', 'diarrhea']):
            symptom_cols['recent_diarrhea'] = d[c]
            break
    # breastfeeding indicators
    for c in d.columns:
        if any(k in c.lower() for k in ['breast', 'breastfed', 'bd3']):
            symptom_cols['breastfeeding'] = d[c]
            break

    # select features
    features = {}
    if 'AG2' in d.columns:
        features['age_months'] = d['AG2']
    if 'AN3' in d.columns:
        features['weight_kg'] = d['AN3']
    if 'AN4' in d.columns:
        features['height_cm'] = d['AN4']
    if muac_col:
        features['muac_cm'] = d[muac_col]
        # MUAC risk flags
        features['muac_severe'] = (d[muac_col] < 11.5).astype(int)
        features['muac_moderate'] = ((d[muac_col] >= 11.5) & (d[muac_col] < 12.5)).astype(int)

    # include any discovered symptom vars
    for name, series in symptom_cols.items():
        features[name] = series

    # include sampling weight if found
    if weight_col:
        features['sample_weight'] = d[weight_col]

    X = pd.DataFrame(features)
    out = pd.concat([X, d[['any_mal']]], axis=1)

    # metadata describing preprocessing
    metadata = {
        'states_included': list(states_include),
        'muac_column': muac_col,
        'sample_weight_column': weight_col,
        'included_features': list(X.columns),
        'muac_thresholds_cm': {'severe': 11.5, 'moderate': 12.5},
    }

    cleaned = out.dropna(subset=list(X.columns) + ['any_mal'])
    return cleaned, metadata


def cross_validated_train(df, feature_cols, target_col='any_mal', C=1.0, cv=5, random_state=42, sample_weight_col=None):
    """Cross-validated training with optional sample weights.

    If `sample_weight_col` is provided and present in `df`, those weights
    are passed to `fit` and used for weighted AUC computation on validation folds.
    """
    # Drop rows with NaN in features or target
    cols_needed = list(feature_cols) + [target_col]
    if sample_weight_col and sample_weight_col in df.columns:
        cols_needed.append(sample_weight_col)
    df_clean = df[cols_needed].dropna()
    if len(df_clean) < 10:
        raise ValueError(f"Not enough clean samples after removing NaN: {len(df_clean)}")
    
    X = df_clean[feature_cols].values
    y = df_clean[target_col].values
    weights = None
    if sample_weight_col and sample_weight_col in df_clean.columns:
        weights = df_clean[sample_weight_col].values

    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    aucs = []
    for train_idx, valid_idx in skf.split(X, y):
        model = LogisticRegression(C=C, solver='liblinear', class_weight='balanced', max_iter=1000)
        if weights is not None:
            model.fit(X[train_idx], y[train_idx], sample_weight=weights[train_idx])
        else:
            model.fit(X[train_idx], y[train_idx])
        prob = model.predict_proba(X[valid_idx])[:, 1]
        if weights is not None:
            aucs.append(roc_auc_score(y[valid_idx], prob, sample_weight=weights[valid_idx]))
        else:
            aucs.append(roc_auc_score(y[valid_idx], prob))

    # fit final model on full data
    final = LogisticRegression(C=C, solver='liblinear', class_weight='balanced', max_iter=1000)
    if weights is not None:
        final.fit(X, y, sample_weight=weights)
    else:
        final.fit(X, y)

    return {'model': final, 'cv_auc_mean': float(np.mean(aucs)), 'cv_auc_std': float(np.std(aucs))}


def calibrate_muac_thresholds(df, muac_col='muac_cm', target_col='any_mal', delta=1.0):
    """Calibrate MUAC thresholds from data.

    Uses ROC on negative MUAC (lower MUAC -> higher risk). Returns (severe_thresh, moderate_thresh).
    The moderate threshold is set to severe + `delta` by default.
    """
    if muac_col not in df.columns:
        raise ValueError(f"MUAC column {muac_col} not found in DataFrame")
    valid = df[[muac_col, target_col]].dropna()
    if valid.empty:
        raise ValueError("No valid MUAC/target rows for calibration")
    y = valid[target_col].astype(int).values
    muac = valid[muac_col].astype(float).values

    # Use -muac so that higher score => higher malnutrition probability
    fpr, tpr, thr = roc_curve(y, -muac)
    youden = tpr - fpr
    idx = int(np.argmax(youden))
    severe = -thr[idx]
    moderate = severe + float(delta)
    return {'severe_cm': float(severe), 'moderate_cm': float(moderate), 'youden_index': float(youden[idx])}


def apply_muac_thresholds(df, muac_col='muac_cm', severe_cm=11.5, moderate_cm=12.5):
    """Apply MUAC thresholds to DataFrame and return copy with flags added."""
    d = df.copy()
    if muac_col not in d.columns:
        raise ValueError(f"MUAC column {muac_col} not found")
    d['muac_severe'] = (d[muac_col] < severe_cm).astype(int)
    d['muac_moderate'] = ((d[muac_col] >= severe_cm) & (d[muac_col] < moderate_cm)).astype(int)
    return d


def save_model(model, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)


def load_model(path):
    return joblib.load(path)


def get_numeric_columns(df, exclude_cols=None, max_missing_pct=10.0):
    """Extract numeric columns from DataFrame with acceptable missing data.
    
    Args:
        df: DataFrame
        exclude_cols: List of column names to exclude (e.g., target column)
        max_missing_pct: Maximum allowed missing data percentage (default 10%)
    
    Returns:
        List of column names that are numeric with <max_missing_pct missing
    """
    if exclude_cols is None:
        exclude_cols = []
    
    numeric_cols = []
    for col in df.columns:
        if col in exclude_cols:
            continue
        # Check if numeric
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        # Check missing percentage
        missing_pct = (df[col].isna().sum() / len(df)) * 100
        if missing_pct <= max_missing_pct:
            numeric_cols.append(col)
    
    return numeric_cols


def export_model_with_metadata(model, feature_cols, preprocessing, path_prefix):
    """Save model and JSON metadata. `path_prefix` is path without extension or with directory+basename.

    Produces: <path_prefix>.joblib and <path_prefix>.meta.json
    """
    import json

    model_path = f"{path_prefix}.joblib" if not str(path_prefix).endswith('.joblib') else path_prefix
    meta_path = f"{path_prefix}.meta.json"
    os.makedirs(os.path.dirname(model_path) or '.', exist_ok=True)
    joblib.dump(model, model_path)

    meta = {
        'model_file': os.path.basename(model_path),
        'feature_columns': list(feature_cols),
        'preprocessing': preprocessing,
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    return model_path, meta_path
