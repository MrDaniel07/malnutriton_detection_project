"""
Enhanced training script to achieve >70% AUC.
Tests multiple algorithms and hyperparameters to find the best model.
"""
import pandas as pd
import numpy as np
from data_utils import generate_synthetic_data
from models import get_numeric_columns
import joblib
import os
import json
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score


def cross_validate_model(clf, X, y, cv=5, random_state=42):
    """Cross-validate a model and return mean/std AUC."""
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    aucs = []
    
    for train_idx, valid_idx in skf.split(X, y):
        X_train, X_valid = X[train_idx], X[valid_idx]
        y_train, y_valid = y[train_idx], y[valid_idx]
        
        clf.fit(X_train, y_train)
        prob = clf.predict_proba(X_valid)[:, 1]
        auc = roc_auc_score(y_valid, prob)
        aucs.append(auc)
    
    return np.mean(aucs), np.std(aucs), aucs


def train_and_save():
    print("=" * 70)
    print("ENHANCED MODEL TRAINING - TARGETING >70% AUC")
    print("=" * 70)
    
    # Generate more data for better training
    print("\nGenerating synthetic training data (20,000 samples)...")
    df = generate_synthetic_data(n_samples=20000, random_state=42)
    
    # Add z-scores
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
    
    print(f"Data prepared: {len(df)} rows")
    print(f"Malnutrition cases: {df['any_mal'].sum()} ({df['any_mal'].sum()/len(df)*100:.1f}%)")
    
    # Get features
    feature_cols = get_numeric_columns(df, exclude_cols=['any_mal', 'malnourished'])
    print(f"Features: {len(feature_cols)}")
    
    # Prepare data
    df_clean = df[list(feature_cols) + ['any_mal']].dropna()
    X = df_clean[feature_cols].values
    y = df_clean['any_mal'].values
    
    # Test different models
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT ALGORITHMS (5-fold Cross-Validation)")
    print("=" * 70)
    
    results = {}
    
    # 1. Logistic Regression with different C values
    print("\n1. Logistic Regression (Testing C parameter):")
    for c_val in [0.1, 0.5, 1.0, 5.0, 10.0]:
        clf = LogisticRegression(C=c_val, solver='liblinear', 
                                  class_weight='balanced', max_iter=1000, random_state=42)
        mean_auc, std_auc, fold_aucs = cross_validate_model(clf, X, y, cv=5, random_state=42)
        results[f'LogisticRegression_C{c_val}'] = {
            'mean_auc': mean_auc,
            'std_auc': std_auc,
            'fold_aucs': fold_aucs,
            'model': clf
        }
        print(f"   C={c_val:5.1f}: AUC = {mean_auc:.4f} ± {std_auc:.4f}  |  Fold AUCs: {[f'{x:.4f}' for x in fold_aucs]}")
    
    # 2. Random Forest with different parameters
    print("\n2. Random Forest (Testing n_estimators):")
    for n_est in [50, 100, 200]:
        clf = RandomForestClassifier(n_estimators=n_est, max_depth=10, 
                                      class_weight='balanced', random_state=42, n_jobs=-1)
        mean_auc, std_auc, fold_aucs = cross_validate_model(clf, X, y, cv=5, random_state=42)
        results[f'RandomForest_e{n_est}'] = {
            'mean_auc': mean_auc,
            'std_auc': std_auc,
            'fold_aucs': fold_aucs,
            'model': clf
        }
        print(f"   n_est={n_est:3d}: AUC = {mean_auc:.4f} ± {std_auc:.4f}  |  Fold AUCs: {[f'{x:.4f}' for x in fold_aucs]}")
    
    # 3. Gradient Boosting with different parameters
    print("\n3. Gradient Boosting (Testing n_estimators):")
    for n_est in [50, 100, 200]:
        clf = GradientBoostingClassifier(n_estimators=n_est, max_depth=5, 
                                         learning_rate=0.1, random_state=42)
        mean_auc, std_auc, fold_aucs = cross_validate_model(clf, X, y, cv=5, random_state=42)
        results[f'GradientBoosting_e{n_est}'] = {
            'mean_auc': mean_auc,
            'std_auc': std_auc,
            'fold_aucs': fold_aucs,
            'model': clf
        }
        print(f"   n_est={n_est:3d}: AUC = {mean_auc:.4f} ± {std_auc:.4f}  |  Fold AUCs: {[f'{x:.4f}' for x in fold_aucs]}")
    
    # Find best model
    best_name = max(results, key=lambda x: results[x]['mean_auc'])
    best_result = results[best_name]
    best_auc = best_result['mean_auc']
    best_std = best_result['std_auc']
    
    print("\n" + "=" * 70)
    print(f"BEST MODEL: {best_name}")
    print(f"AUC: {best_auc:.4f} ± {best_std:.4f}")
    print(f"AUC Varies: {best_std:.4f} (indicates consistency across folds)")
    print("=" * 70)
    
    # Retrain best model on full data
    print(f"\nRetraining best model on full data...")
    best_clf_type = best_name.split('_')[0]
    
    if best_clf_type == 'LogisticRegression':
        c_val = float(best_name.split('C')[1])
        final_model = LogisticRegression(C=c_val, solver='liblinear', 
                                        class_weight='balanced', max_iter=1000, random_state=42)
    elif best_clf_type == 'RandomForest':
        n_est = int(best_name.split('e')[1])
        final_model = RandomForestClassifier(n_estimators=n_est, max_depth=10, 
                                            class_weight='balanced', random_state=42, n_jobs=-1)
    else:  # GradientBoosting
        n_est = int(best_name.split('e')[1])
        final_model = GradientBoostingClassifier(n_estimators=n_est, max_depth=5, 
                                                learning_rate=0.1, random_state=42)
    
    final_model.fit(X, y)
    
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
    joblib.dump(final_model, 'models/pretrained_model.joblib')
    
    print("Saving model metadata...")
    metadata = {
        'feature_cols': feature_cols,
        'feature_defaults': feature_defaults,
        'metrics': {
            'auc': float(best_auc),
            'auc_std': float(best_std),
            'auc_variation': f"{best_std:.4f} (cross-fold variance)",
            'model_type': best_name,
            'num_features': len(feature_cols),
            'training_samples': len(df),
            'all_results': {k: {'mean_auc': v['mean_auc'], 'std_auc': v['std_auc']} for k, v in results.items()}
        }
    }
    
    with open('models/model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n✅ TRAINING COMPLETE!")
    print("=" * 70)
    print(f"Model: {best_name}")
    print(f"AUC: {best_auc:.4f} ± {best_std:.4f}")
    print(f"AUC Variation: Std Dev = {best_std:.4f} (varies {best_std:.1%} across folds)")
    print(f"Features: {len(feature_cols)}")
    print(f"Training Samples: {len(df)}")
    print("=" * 70)
    print("   ✓ Model: models/pretrained_model.joblib")
    print("   ✓ Metadata: models/model_metadata.json")


if __name__ == '__main__':
    train_and_save()
