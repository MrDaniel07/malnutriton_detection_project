"""
Optimized training script focusing on Logistic Regression with more data.
Target: >70% AUC
"""
import pandas as pd
import numpy as np
from data_utils import generate_synthetic_data
from models import get_numeric_columns
import joblib
import os
import json
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score


def cross_validate_model(clf, X, y, cv=5, random_state=42):
    """Cross-validate a model and return mean/std AUC."""
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    aucs = []
    fold_details = []
    
    for fold_idx, (train_idx, valid_idx) in enumerate(skf.split(X, y)):
        X_train, X_valid = X[train_idx], X[valid_idx]
        y_train, y_valid = y[train_idx], y[valid_idx]
        
        clf.fit(X_train, y_train)
        prob = clf.predict_proba(X_valid)[:, 1]
        auc = roc_auc_score(y_valid, prob)
        aucs.append(auc)
        fold_details.append({
            'fold': fold_idx + 1,
            'auc': auc,
            'pos_examples': y_valid.sum(),
            'neg_examples': len(y_valid) - y_valid.sum()
        })
    
    return np.mean(aucs), np.std(aucs), aucs, fold_details


def train_and_save():
    print("=" * 80)
    print("OPTIMIZED MODEL TRAINING - TARGET: >70% AUC")
    print("=" * 80)
    
    # Test with different data sizes to find optimal training size
    print("\nTESTING DIFFERENT DATA SIZES:")
    print("-" * 80)
    
    data_sizes = [20000, 30000, 40000, 50000]
    best_overall_auc = 0
    best_config = None
    best_model = None
    
    for data_size in data_sizes:
        print(f"\nTraining with {data_size:,} samples...")
        df = generate_synthetic_data(n_samples=data_size, random_state=42)
        
        # Add z-scores
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
        
        # Map target
        if 'malnourished' in df.columns:
            df['any_mal'] = df['malnourished']
        elif 'any_mal' not in df.columns:
            df['any_mal'] = ((df['WHZ'] < -2) | (df['HAZ'] < -2) | (df['WAZ'] < -2)).astype(int)
        
        feature_cols = get_numeric_columns(df, exclude_cols=['any_mal', 'malnourished'])
        
        # Prepare data
        df_clean = df[list(feature_cols) + ['any_mal']].dropna()
        X = df_clean[feature_cols].values
        y = df_clean['any_mal'].values
        
        print(f"  Samples: {len(df):,}, Malnutrition rate: {y.sum()/len(y)*100:.2f}%")
        
        # Test different C values
        best_auc_for_size = 0
        best_c_for_size = None
        
        for c_val in [0.01, 0.1, 0.5, 1.0, 2.0, 5.0]:
            clf = LogisticRegression(C=c_val, solver='liblinear', 
                                      class_weight='balanced', max_iter=1000, random_state=42)
            mean_auc, std_auc, fold_aucs, fold_details = cross_validate_model(clf, X, y, cv=5, random_state=42)
            
            if mean_auc > best_auc_for_size:
                best_auc_for_size = mean_auc
                best_c_for_size = c_val
                best_params_for_size = (mean_auc, std_auc, fold_aucs, fold_details, clf)
            
            if mean_auc > best_overall_auc:
                best_overall_auc = mean_auc
                best_config = {
                    'data_size': data_size,
                    'c_value': c_val,
                    'auc_mean': mean_auc,
                    'auc_std': std_auc,
                    'fold_aucs': fold_aucs,
                    'fold_details': fold_details,
                    'feature_cols': feature_cols,
                    'df': df,
                    'X': X,
                    'y': y
                }
                best_model = clf
        
        mean_auc, std_auc, _, _, _ = best_params_for_size
        print(f"  Best C={best_c_for_size}: AUC = {mean_auc:.4f} ± {std_auc:.4f}")
    
    # Print best configuration found
    print("\n" + "=" * 80)
    print("BEST CONFIGURATION FOUND:")
    print("=" * 80)
    print(f"Data Size: {best_config['data_size']:,} samples")
    print(f"C Value: {best_config['c_value']}")
    print(f"AUC: {best_config['auc_mean']:.4f} ± {best_config['auc_std']:.4f}")
    print(f"\nCross-Validation Details (5-fold):")
    print("-" * 80)
    
    for detail in best_config['fold_details']:
        fold_num = detail['fold']
        fold_auc = detail['auc']
        print(f"  Fold {fold_num}: AUC = {fold_auc:.4f} (Positive: {detail['pos_examples']}, Negative: {detail['neg_examples']})")
    
    print(f"\nAUC Variation (Standard Deviation): {best_config['auc_std']:.4f}")
    print("  → This shows how much AUC varies across different data splits")
    print(f"  → Lower value = more consistent performance")
    
    # Calculate percentage above threshold
    auc_percent = best_config['auc_mean'] * 100
    print(f"\nAUC as percentage: {auc_percent:.2f}%")
    if auc_percent >= 70:
        print("✅ TARGET ACHIEVED: AUC >= 70%")
    else:
        percent_remaining = 70 - auc_percent
        print(f"⚠️  {percent_remaining:.2f}% remaining to reach 70% target")
    
    # Retrain on full data with best config
    print("\n" + "=" * 80)
    print("RETRAINING FINAL MODEL ON FULL DATA...")
    print("=" * 80)
    
    final_model = LogisticRegression(C=best_config['c_value'], solver='liblinear', 
                                     class_weight='balanced', max_iter=1000, random_state=42)
    final_model.fit(best_config['X'], best_config['y'])
    
    # Compute feature defaults
    feature_defaults = {}
    for col in best_config['feature_cols']:
        try:
            feature_defaults[col] = float(best_config['df'][col].mean())
        except:
            feature_defaults[col] = 0.0
    
    # Save model and metadata
    os.makedirs('models', exist_ok=True)
    
    print("Saving model...")
    joblib.dump(final_model, 'models/pretrained_model.joblib')
    
    print("Saving model metadata...")
    metadata = {
        'feature_cols': best_config['feature_cols'],
        'feature_defaults': feature_defaults,
        'metrics': {
            'auc': float(best_config['auc_mean']),
            'auc_std': float(best_config['auc_std']),
            'auc_percent': float(auc_percent),
            'auc_variation_info': f"Standard deviation = {best_config['auc_std']:.4f} (varies across CV folds)",
            'model_type': f"LogisticRegression (C={best_config['c_value']})",
            'num_features': len(best_config['feature_cols']),
            'training_samples': best_config['data_size'],
            'fold_auc_details': [
                {'fold': d['fold'], 'auc': f"{d['auc']:.4f}"} 
                for d in best_config['fold_details']
            ]
        }
    }
    
    with open('models/model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✅ TRAINING COMPLETE")
    print("=" * 80)
    print(f"AUC: {best_config['auc_mean']:.4f} ± {best_config['auc_std']:.4f} ({auc_percent:.2f}%)")
    print(f"Features: {len(best_config['feature_cols'])}")
    print(f"Training Samples: {best_config['data_size']:,}")
    print("\nFiles saved:")
    print("  ✓ models/pretrained_model.joblib")
    print("  ✓ models/model_metadata.json")
    print("=" * 80)


if __name__ == '__main__':
    train_and_save()
