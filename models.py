import io
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns


def train_evaluate(df, feature_cols=None, target_col="malnourished", C=1.0, test_size=0.2, random_state=42):
    if feature_cols is None:
        feature_cols = [c for c in df.columns if c != target_col]

    X = df[feature_cols].values
    y = df[target_col].values

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
