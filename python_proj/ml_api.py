"""
Flask API for Early Malnutrition Detection Model
Serves predictions and provides model metadata
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from models import train_evaluate, cross_validated_train, get_numeric_columns, predict_single
from data_utils import load_csv
import joblib
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Global model state
model_state = {
    'model': None,
    'feature_cols': None,
    'metrics': None,
    'training_data': None,
    'feature_defaults': None
}


def build_feature_defaults(df, feature_cols):
    """Build default feature values from training data means."""
    defaults = {}
    for col in feature_cols:
        try:
            defaults[col] = float(df[col].mean())
        except Exception:
            defaults[col] = 0.0
    return defaults


def compute_z_scores(age_months, weight_kg, height_cm):
    """
    Compute approximate z-scores from raw anthropometric measurements.
    Uses simplified linear models based on WHO West Africa reference values.
    
    WHO reference (60 months): 115cm height, 20kg weight, 17cm MUAC
    
    Note: This is a simplified approximation. For production use, implement
    proper WHO reference table lookups with age/sex stratification.
    """
    # Expected values based on age (linear approximation)
    # Calibrated to WHO West Africa standards
    expected_height = 48 + (age_months * 1.12)  # ~115cm at 60 months
    expected_weight = 3 + (age_months * 0.28)   # ~20kg at 60 months
    
    # Standard deviations (approximated from WHO growth charts)
    sd_height = 6.0
    sd_weight = 2.5
    
    # Height-for-Age Z-score (HAZ) - indicates stunting
    HAZ = (height_cm - expected_height) / sd_height
    
    # Weight-for-Age Z-score (WAZ) - indicates underweight
    WAZ = (weight_kg - expected_weight) / sd_weight
    
    # Weight-for-Height Z-score (WHZ) - indicates wasting
    # Expected weight for given height (simplified regression)
    expected_weight_for_height = -15 + (height_cm * 0.3)
    sd_weight_for_height = 2.0
    WHZ = (weight_kg - expected_weight_for_height) / sd_weight_for_height
    
    return {'WHZ': WHZ, 'HAZ': HAZ, 'WAZ': WAZ}


def compose_feedback(risk_level, prob):
    pct = prob * 100
    if risk_level == 'HIGH':
        return (
            f"High malnutrition risk detected ({pct:.1f}%). "
            "Recommend immediate clinical assessment with a qualified provider, "
            "including anthropometry verification, dietary history, and infection screening. "
            "If severe wasting is suspected, consider referral for urgent nutrition support."
        )
    if risk_level == 'MODERATE':
        return (
            f"Moderate malnutrition risk detected ({pct:.1f}%). "
            "Recommend follow-up screening within 2-4 weeks, nutrition counseling for caregivers, "
            "and monitoring of weight gain and MUAC trends. "
            "Assess for recent illness that could affect growth." 
        )
    return (
        f"Low malnutrition risk detected ({pct:.1f}%). "
        "Continue routine growth monitoring and ensure balanced feeding practices. "
        "If symptoms develop or growth stalls, schedule a follow-up assessment."
    )


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'malnutrition-detection-api'})


@app.route('/api/load-data', methods=['POST'])
def load_data():
    """Load training data (synthetic CSV)."""
    try:
        data_source = request.json.get('source', 'synthetic')
        
        if data_source == 'synthetic':
            df = load_csv('csv_output/large_synthetic.csv')
            
            # Compute any_mal if not present
            if 'any_mal' not in df.columns and all(c in df.columns for c in ['WHZ', 'HAZ', 'WAZ']):
                df['any_mal'] = ((df['WHZ'] < -2) | (df['HAZ'] < -2) | (df['WAZ'] < -2)).astype(int)
            
            model_state['training_data'] = df
            
            return jsonify({
                'status': 'success',
                'rows': len(df),
                'columns': len(df.columns),
                'malnutrition_cases': int(df['any_mal'].sum()) if 'any_mal' in df.columns else 0
            })
        else:
            return jsonify({'status': 'error', 'message': 'Invalid data source'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/train', methods=['POST'])
def train_model():
    """Train logistic regression model."""
    try:
        if model_state['training_data'] is None:
            return jsonify({'status': 'error', 'message': 'No data loaded. Call /api/load-data first'}), 400
        
        df = model_state['training_data']
        C = request.json.get('C', 1.0)
        cv_folds = request.json.get('cv_folds', 5)
        
        # Get numeric features
        feature_cols = get_numeric_columns(df, exclude_cols=['any_mal'])
        
        if not feature_cols:
            return jsonify({'status': 'error', 'message': 'No numeric features found'}), 400
        
        # Train with cross-validation
        cv_res = cross_validated_train(
            df, 
            feature_cols=feature_cols,
            target_col='any_mal',
            C=C, 
            cv=cv_folds,
            random_state=42
        )
        
        model_state['model'] = cv_res['model']
        model_state['feature_cols'] = feature_cols
        model_state['feature_defaults'] = build_feature_defaults(df, feature_cols)
        model_state['metrics'] = {
            'auc': float(cv_res['cv_auc_mean']),
            'auc_std': float(cv_res['cv_auc_std']),
            'num_features': len(feature_cols),
            'training_samples': len(df)
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Model trained successfully',
            'metrics': model_state['metrics'],
            'features': feature_cols
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/predict', methods=['POST'])
def predict():
    """Make prediction for a single child."""
    try:
        if model_state['model'] is None:
            return jsonify({'status': 'error', 'message': 'Model not trained. Call /api/train first'}), 400
        
        patient_data = request.json.get('patient_data', {})
        
        # Validate required inputs
        if not patient_data:
            return jsonify({'status': 'error', 'message': 'No patient data provided'}), 400
        
        # Compute z-scores from raw measurements if available
        age = patient_data.get('age_months')
        weight = patient_data.get('weight_kg')
        height = patient_data.get('height_cm')
        
        if age and weight and height:
            z_scores = compute_z_scores(age, weight, height)
            # Add computed z-scores to patient data
            patient_data.update(z_scores)
        
        # Make prediction
        feature_cols = model_state['feature_cols']
        defaults = model_state.get('feature_defaults')
        if defaults is None and model_state['training_data'] is not None:
            defaults = build_feature_defaults(model_state['training_data'], feature_cols)
            model_state['feature_defaults'] = defaults

        filled_data = dict(defaults or {})
        filled_data.update(patient_data)

        pred = predict_single(model_state['model'], feature_cols, filled_data)
        prob = pred['probability']
        
        # Determine risk level and feedback
        if prob > 0.7:
            risk_level = 'HIGH'
            risk_color = 'red'
        elif prob > 0.3:
            risk_level = 'MODERATE'
            risk_color = 'yellow'
        else:
            risk_level = 'LOW'
            risk_color = 'green'
        
        feedback = compose_feedback(risk_level, prob)
        
        # Get current model AUC
        model_auc = model_state.get('metrics', {}).get('auc', None)
        
        return jsonify({
            'status': 'success',
            'probability': float(prob),
            'percentage': f'{prob*100:.1f}%',
            'risk_level': risk_level,
            'risk_color': risk_color,
            'feedback': feedback,
            'model_auc': model_auc,
            'patient_data': patient_data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/model-info', methods=['GET'])
def model_info():
    """Get current model information and feature list."""
    if model_state['model'] is None:
        return jsonify({'status': 'error', 'message': 'No model trained'}), 400
    
    return jsonify({
        'status': 'success',
        'metrics': model_state['metrics'],
        'features': model_state['feature_cols'],
        'model_type': 'Logistic Regression with Balanced Class Weights'
    })


@app.route('/api/feature-stats', methods=['GET'])
def feature_stats():
    """Get statistics for all features (for setting UI slider ranges)."""
    if model_state['training_data'] is None:
        return jsonify({'status': 'error', 'message': 'No data loaded'}), 400
    
    df = model_state['training_data']
    feature_cols = model_state.get('feature_cols', get_numeric_columns(df, exclude_cols=['any_mal']))
    
    stats = {}
    for feat in feature_cols:
        try:
            stats[feat] = {
                'min': float(df[feat].min()),
                'max': float(df[feat].max()),
                'mean': float(df[feat].mean()),
                'median': float(df[feat].median()),
                'std': float(df[feat].std())
            }
        except:
            pass
    
    return jsonify({'status': 'success', 'statistics': stats})


@app.route('/api/save-model', methods=['POST'])
def save_model():
    """Save trained model to disk."""
    try:
        if model_state['model'] is None:
            return jsonify({'status': 'error', 'message': 'No model to save'}), 400
        
        path_prefix = request.json.get('path', 'models/malnutrition_model')
        model_path = f"{path_prefix}.joblib"
        
        os.makedirs(os.path.dirname(model_path) or '.', exist_ok=True)
        joblib.dump(model_state['model'], model_path)
        
        return jsonify({
            'status': 'success',
            'model_path': model_path,
            'message': f'Model saved to {model_path}'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/predict-csv', methods=['POST'])
def predict_csv():
    """Predict malnutrition risk for multiple patient records in a CSV file."""
    try:
        if model_state['model'] is None:
            return jsonify({'status': 'error', 'message': 'Model not trained. Call /api/train first'}), 400

        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'status': 'error', 'message': 'File must be CSV format'}), 400

        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Failed to read CSV: {str(e)}'}), 400

        if len(df) == 0:
            return jsonify({'status': 'error', 'message': 'CSV file is empty'}), 400

        feature_cols = model_state['feature_cols']
        defaults = model_state.get('feature_defaults') or {}

        results = []
        summary_counts = {'HIGH': 0, 'MODERATE': 0, 'LOW': 0}

        column_lookup = {str(col).lower(): col for col in df.columns}

        def pick_value(row, names):
            for name in names:
                col = column_lookup.get(str(name).lower())
                if col is None:
                    col = name
                if col in row and pd.notna(row[col]):
                    return row[col]
            return None

        def to_float(value):
            try:
                return float(value)
            except Exception:
                return None

        for idx, row in df.iterrows():
            row_data = {}
            for col in feature_cols:
                if col in row and pd.notna(row[col]):
                    try:
                        row_data[col] = float(row[col])
                    except Exception:
                        continue

            age = row_data.get('age_months')
            if age is None:
                age = to_float(pick_value(row, ['age_months', 'age']))
                if age is not None:
                    row_data['age_months'] = age

            weight = row_data.get('weight_kg')
            if weight is None:
                weight = to_float(pick_value(row, ['weight_kg', 'weight']))
                if weight is not None:
                    row_data['weight_kg'] = weight

            height = row_data.get('height_cm')
            if height is None:
                height = to_float(pick_value(row, ['height_cm', 'height']))
                if height is not None:
                    row_data['height_cm'] = height

            muac = row_data.get('muac_cm')
            if muac is None:
                muac = to_float(pick_value(row, ['muac_cm', 'muac']))
                if muac is not None:
                    row_data['muac_cm'] = muac

            if age is not None and weight is not None and height is not None:
                if any(col not in row_data for col in ['WHZ', 'HAZ', 'WAZ']):
                    z_scores = compute_z_scores(age, weight, height)
                    row_data.update(z_scores)

            filled_data = dict(defaults)
            filled_data.update(row_data)

            pred = predict_single(model_state['model'], feature_cols, filled_data)
            prob = float(pred['probability'])

            if prob > 0.7:
                risk_level = 'HIGH'
                risk_color = 'red'
            elif prob > 0.3:
                risk_level = 'MODERATE'
                risk_color = 'yellow'
            else:
                risk_level = 'LOW'
                risk_color = 'green'

            summary_counts[risk_level] += 1

            results.append({
                'row': int(idx) + 1,
                'probability': prob,
                'percentage': f'{prob * 100:.1f}%',
                'risk_level': risk_level,
                'risk_color': risk_color,
                'inputs': {
                    'age_months': age,
                    'weight_kg': weight,
                    'height_cm': height,
                    'muac_cm': muac,
                    'WHZ': row_data.get('WHZ'),
                    'HAZ': row_data.get('HAZ'),
                    'WAZ': row_data.get('WAZ')
                }
            })

        return jsonify({
            'status': 'success',
            'total': len(results),
            'summary': {
                'high': summary_counts['HIGH'],
                'moderate': summary_counts['MODERATE'],
                'low': summary_counts['LOW']
            },
            'model_auc': model_state.get('metrics', {}).get('auc', None),
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
