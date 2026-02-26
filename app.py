import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from data_utils import generate_synthetic_data, load_csv
from models import (
    train_evaluate,
    predict_single,
    load_mics_child,
    preprocess_mics_child,
    cross_validated_train,
    save_model,
    export_model_with_metadata,
    calibrate_muac_thresholds,
    apply_muac_thresholds,
    get_numeric_columns,
)


st.set_page_config(page_title="Early Malnutrition Detection (Prototype)", layout="wide")

st.title("Early Malnutrition Detection — Prototype (Nigeria-focused)")

st.sidebar.header("Data Source & Training")
use_sample = st.sidebar.radio("Data source:", ("Synthetic sample", "Upload CSV", "Use MICS (2016-17 child file)", "Load generated synthetic CSV (Lagos/Ogun)"))

if use_sample == "Synthetic sample":
    n_samples = st.sidebar.slider("Synthetic samples", 200, 10000, 2000, step=200)
    df = generate_synthetic_data(n_samples=n_samples)
elif use_sample == "Load generated synthetic CSV (Lagos/Ogun)":
    try:
        df = load_csv('csv_output/large_synthetic.csv')
        # Compute any_mal from z-scores if not already present
        if 'any_mal' not in df.columns and all(c in df.columns for c in ['WHZ', 'HAZ', 'WAZ']):
            df['any_mal'] = ((df['WHZ'] < -2) | (df['HAZ'] < -2) | (df['WAZ'] < -2)).astype(int)
        st.sidebar.success(f"Loaded {len(df)} rows from generated CSV (Lagos/Ogun, under 10 years)")
    except Exception as e:
        st.sidebar.error(f"Failed to load: {e}")
        st.stop()
else:
    uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded is not None:
        df = load_csv(uploaded)
    else:
        st.sidebar.info("Upload a CSV file or choose the synthetic sample.")
        st.stop()

if use_sample == "Use MICS (2016-17 child file)":
    # try to find child files in workspace
    sav_paths = glob.glob(os.path.join("MICS_Datasets", "**", "ch.sav"), recursive=True)
    if not sav_paths:
        st.sidebar.error("No MICS child .sav files found under MICS_Datasets.")
        st.stop()
    choice = st.sidebar.selectbox("Choose MICS child file", sav_paths)
    if choice:
        with st.spinner("Loading MICS file..."):
            df_raw, meta = load_mics_child(choice)
        st.sidebar.success("Loaded")
        st.sidebar.write(os.path.basename(choice))

        # Filter Lagos/Abuja
        if st.sidebar.checkbox("Filter to Lagos & Abuja (recommended)", value=True):
            df = df_raw[df_raw['HH7'].isin([24.0, 37.0])].copy()
        else:
            df = df_raw

        with st.expander("Preview original MICS variables (first 20)"):
            st.write({k: meta.column_names_to_labels.get(k) for k in list(df_raw.columns)[:20]})

        # Preprocess with helper
        if st.sidebar.button("Preprocess and prepare features"):
            with st.spinner("Preprocessing MICS data..."):
                df_pre, prep_meta = preprocess_mics_child(df)
            st.success("Preprocessing done")
            st.dataframe(df_pre.head())
            df = df_pre
            st.session_state['preprocessing_meta'] = prep_meta

        # If MUAC is present, allow calibration
        muac_col = st.session_state.get('preprocessing_meta', {}).get('muac_column')
        if muac_col:
            if st.sidebar.button('Calibrate MUAC thresholds'):
                with st.spinner('Calibrating MUAC thresholds...'):
                    try:
                        cal = calibrate_muac_thresholds(df, muac_col=muac_col, target_col='any_mal')
                        st.session_state['preprocessing_meta']['muac_thresholds_cm'] = {'severe': cal['severe_cm'], 'moderate': cal['moderate_cm']}
                        # apply thresholds to feature dataframe
                        df = apply_muac_thresholds(df, muac_col=muac_col, severe_cm=cal['severe_cm'], moderate_cm=cal['moderate_cm'])
                        st.success(f"Calibrated MUAC severe={cal['severe_cm']:.2f} cm, moderate={cal['moderate_cm']:.2f} cm")
                    except Exception as e:
                        st.error(f"Calibration failed: {e}")


st.sidebar.markdown("---")
st.sidebar.header("Training Options")
C = st.sidebar.number_input("Regularization C (smaller = stronger reg)", min_value=0.01, max_value=10.0, value=1.0, step=0.01)
test_size = st.sidebar.slider("Test set fraction", 0.05, 0.5, 0.2)
random_state = st.sidebar.number_input("Random seed", value=42)

# Determine target column based on available columns
target_col = None
if 'any_mal' in df.columns:
    target_col = 'any_mal'
elif 'malnourished' in df.columns:
    target_col = 'malnourished'

feature_cols = [c for c in df.columns if c != target_col and target_col is not None] if target_col else [c for c in df.columns if c != "malnourished"]

with st.expander("Preview data (first 10 rows)"):
    st.dataframe(df.head(10))

st.markdown("### Train model")
if st.button("Train logistic regression"):
    try:
        result = None
        with st.spinner("Training..."):
            # If MICS-preprocessed dataframe was used, allow cross-validated training
            if 'any_mal' in df.columns:
                feature_cols = get_numeric_columns(df, exclude_cols=['any_mal'])
                if not feature_cols:
                    st.error("No numeric features found for training.")
                else:
                    cv = st.sidebar.slider('CV folds', 2, 10, 5)
                    cv_res = cross_validated_train(df, feature_cols=feature_cols, C=C, cv=cv, random_state=int(random_state), sample_weight_col=st.session_state.get('preprocessing_meta', {}).get('sample_weight_column'))
                    result = {'model': cv_res['model'], 'metrics': {'auc': cv_res['cv_auc_mean'], 'confusion_matrix': []}, 'feature_cols': feature_cols}
                    if 'preprocessing_meta' in st.session_state:
                        result['preprocessing'] = st.session_state['preprocessing_meta']
            else:
                feature_cols = get_numeric_columns(df, exclude_cols=[target_col] if target_col else [])
                if not feature_cols:
                    st.error("No numeric features found for training.")
                else:
                    result = train_evaluate(df, feature_cols=feature_cols, C=C, test_size=test_size, random_state=int(random_state))
        
        if result is not None:
            st.success("Training complete")
            # persist result so it survives reruns
            st.session_state['result'] = result

            st.subheader("Metrics")
            st.write(f"AUC: **{result['metrics']['auc']:.3f}**")
            if result['metrics'].get('confusion_matrix'):
                st.write("Confusion matrix:")
                st.write(result["metrics"]["confusion_matrix"]) 
            if 'feature_importance' in result:
                st.subheader("Feature importance (coefficients)")
                st.dataframe(result["feature_importance"].assign(coef=lambda d: d.coef.round(4)))

            if 'roc_fig' in result:
                st.subheader("ROC curve")
                st.pyplot(result["roc_fig"])
    except Exception as e:
        st.error("Training failed — see error details below")
        st.exception(e)

# Prediction section (now OUTSIDE the button block so it persists)
st.markdown("---")
st.subheader("Interactive single prediction")
# get trained model/result from session state
result = st.session_state.get('result')
if result is None:
    st.warning('No trained model found — train a model first to enable prediction.')
else:
    st.markdown("#### Option 1: Predict using dataset values")
    feature_cols = result.get('feature_cols', [])
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
        # reload result (in case UI rerun changed locals)
        result = st.session_state.get('result')
        if result is None:
            st.error('No trained model available. Train a model first.')
        else:
            pred = predict_single(result["model"], result["feature_cols"], inputs)
            prob = pred["probability"]
            st.metric("Predicted malnutrition probability", f"{prob:.2%}")
            if prob > 0.7:
                st.error("🔴 High risk — prototype model. Refer to clinical guidance.")
            elif prob > 0.3:
                st.warning("🟡 Moderate risk — prototype model. Consider further screening.")
            else:
                st.success("🟢 Low risk by model.")

st.markdown("---")
if st.button('Save trained model'):
    result = st.session_state.get('result')
    if result:
        out_path = st.text_input('Model path (prefix, .joblib/meta.json will be added)', value='models/malnutrition_model')
        if out_path:
            preprocessing = result.get('preprocessing', {})
            model_path, meta_path = export_model_with_metadata(result['model'], result['feature_cols'], preprocessing, out_path)
            st.success(f"Model saved to {model_path} and metadata to {meta_path}")
    else:
        st.error("No trained model to save.")
