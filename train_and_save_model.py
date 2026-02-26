"""
Script to train the malnutrition detection model and save it for production use.
Run this locally before deployment to pre-train the model.
"""
import pandas as pd
import numpy as np
from data_utils import generate_synthetic_data
from models import cross_validated_train, get_numeric_columns
import joblib
import os
import json


def train_and_save():
    print("Generating synthetic training data (15,000 samples)...")
    df = generate_synthetic_data(n_samples=15000, random_state=42)
    
    # Add z-scores (vectorized for performance)
    print("Computing z-scores...")
    ages = df['age_months'].values
    weights = df['weight_kg'].values
    heights = df['height_cm'].values
    
    expected_height = 48 + (ages * 1.12)
    expected_weight = 3.5 + (ages * 0.28)
    expected_weight_for_height = 3.5 + ((heights - 48) / 1.12) * 0.28
    
    height_sd = 6.0
    weight_sd = 2.8
    whz_sd = 2.5
    
    df['HAZ'] = (heights - expected_height) / height_sd
    df['WAZ'] = (weights - expected_weight) / weight_sd
    df['WHZ'] = (weights - expected_weight_for_height) / whz_sd
    
    # Map target column
    if 'malnourished' in df.columns:
        df['any_mal'] = df['malnourished']
    elif 'any_mal' not in df.columns:
        df['any_mal'] = ((df['WHZ'] < -2) | (df['HAZ'] < -2) | (df['WAZ'] < -2)).astype(int)
    
    print(f"Data prepared: {len(df)} rows, {len(df.columns)} columns")
    print(f"Malnutrition cases: {df['any_mal'].sum()} ({df['any_mal'].sum()/len(df)*100:.1f}%)")
    
    # Get features
    feature_cols = get_numeric_columns(df, exclude_cols=['any_mal'])
    print(f"Training with {len(feature_cols)} features")
    
    # Train model with 5-fold cross-validation
    print("Training model with 5-fold cross-validation...")
    cv_res = cross_validated_train(
        df, 
        feature_cols=feature_cols,
        target_col='any_mal',
        C=1.0, 
        cv=5,
        random_state=42
    )
    
    model = cv_res['model']
    auc_mean = cv_res['cv_auc_mean']
    auc_std = cv_res['cv_auc_std']
    
    print(f"Model trained successfully!")
    print(f"Cross-validation AUC: {auc_mean:.4f} ± {auc_std:.4f}")
    
    # Compute feature defaults
    feature_defaults = {}
    for col in feature_cols:
        try:
            feature_defaults[col] = float(df[col].mean())
        except:
            feature_defaults[col] = 0.0
    
    # Save model and metadata
    os.makedirs('models', exist_ok=True)
    
    print("Saving model...")
    joblib.dump(model, 'models/pretrained_model.joblib')
    
    print("Saving model metadata...")
    metadata = {
        'feature_cols': feature_cols,
        'feature_defaults': feature_defaults,
        'metrics': {
            'auc': float(auc_mean),
            'auc_std': float(auc_std),
            'num_features': len(feature_cols),
            'training_samples': len(df)
        }
    }
    
    with open('models/model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n✅ Model saved successfully!")
    print("   - Model: models/pretrained_model.joblib")
    print("   - Metadata: models/model_metadata.json")
    print(f"   - AUC: {auc_mean:.4f}")
    print(f"   - Features: {len(feature_cols)}")


if __name__ == '__main__':
    train_and_save()
