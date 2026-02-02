import streamlit as st
import pandas as pd
import numpy as np
from data_utils import generate_synthetic_data, load_csv
from models import train_evaluate, predict_single


st.set_page_config(page_title="Early Malnutrition Detection (Prototype)", layout="wide")

st.title("Early Malnutrition Detection — Prototype (Nigeria-focused)")

st.sidebar.header("Data Source & Training")
use_sample = st.sidebar.radio("Data source:", ("Synthetic sample", "Upload CSV"))

if use_sample == "Synthetic sample":
    n_samples = st.sidebar.slider("Synthetic samples", 200, 10000, 2000, step=200)
    df = generate_synthetic_data(n_samples=n_samples)
else:
    uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded is not None:
        df = load_csv(uploaded)
    else:
        st.sidebar.info("Upload a CSV file or choose the synthetic sample.")
        st.stop()

st.sidebar.markdown("---")
st.sidebar.header("Training Options")
C = st.sidebar.number_input("Regularization C (smaller = stronger reg)", min_value=0.01, max_value=10.0, value=1.0, step=0.01)
test_size = st.sidebar.slider("Test set fraction", 0.05, 0.5, 0.2)
random_state = st.sidebar.number_input("Random seed", value=42)

feature_cols = [c for c in df.columns if c != "malnourished"]

with st.expander("Preview data (first 10 rows)"):
    st.dataframe(df.head(10))

st.markdown("### Train model")
if st.button("Train logistic regression"):
    with st.spinner("Training..."):
        result = train_evaluate(df, feature_cols=feature_cols, C=C, test_size=test_size, random_state=int(random_state))
    st.success("Training complete")

    st.subheader("Metrics")
    st.write(f"AUC: **{result['metrics']['auc']:.3f}**")
    st.write("Confusion matrix:")
    st.write(result["metrics"]["confusion_matrix"]) 
    st.subheader("Feature importance (coefficients)")
    st.dataframe(result["feature_importance"].assign(coef=lambda d: d.coef.round(4)))

    st.subheader("ROC curve")
    st.pyplot(result["roc_fig"])

    st.markdown("---")
    st.subheader("Interactive single prediction")
    cols = st.columns(3)
    inputs = {}
    for i, feat in enumerate(feature_cols):
        # pick sensible widgets based on feature name
        if "age" in feat:
            val = cols[i % 3].slider(feat, 0, 60, int(df[feat].median()))
        elif "weight" in feat:
            val = cols[i % 3].slider(feat, 2.0, 30.0, float(df[feat].median()))
        elif "height" in feat:
            val = cols[i % 3].slider(feat, 45.0, 140.0, float(df[feat].median()))
        elif "muac" in feat:
            val = cols[i % 3].slider(feat, 7.0, 25.0, float(df[feat].median()))
        elif feat in ("breastfeeding", "recent_diarrhea"):
            val = cols[i % 3].selectbox(feat, (0, 1), index=int(df[feat].median()))
        elif "immunizations" in feat:
            val = cols[i % 3].slider(feat, 0, 12, int(df[feat].median()))
        elif "income" in feat:
            val = cols[i % 3].number_input(feat, value=float(df[feat].median()))
        else:
            val = cols[i % 3].number_input(feat, value=float(df[feat].median()))
        inputs[feat] = val

    if st.button("Predict for this child"):
        pred = predict_single(result["model"], result["feature_cols"], inputs)
        prob = pred["probability"]
        st.metric("Predicted malnutrition probability", f"{prob:.2%}")
        if prob > 0.7:
            st.error("High risk — prototype model. Refer to clinical guidance.")
        elif prob > 0.3:
            st.warning("Moderate risk — prototype model. Consider further screening.")
        else:
            st.success("Low risk by model. This is a prototype, not clinical advice.")

    st.markdown("---")
    st.info("Disclaimer: This prototype uses synthetic data or user-supplied CSV for demonstration. It is not a medical diagnostic tool. For clinical screening, use validated tools and professional guidance.")
