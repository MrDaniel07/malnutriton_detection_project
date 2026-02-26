from data_utils import generate_synthetic_data
from models import cross_validated_train
import numpy as np

# Generate data
df = generate_synthetic_data(n_samples=15000, random_state=42)
df['any_mal'] = df['malnourished']

# Add z-scores (simulating what ml_api.py does)
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

# Get feature columns (numeric, excluding target)
feature_cols = [c for c in df.columns if c not in ['malnourished', 'any_mal'] and df[c].dtype in ['int64', 'float64']]
print('Feature columns:', feature_cols)
print('Number of features:', len(feature_cols))

# Train model
cv_res = cross_validated_train(df, feature_cols=feature_cols, target_col='any_mal', C=1.0, cv=5, random_state=42)
model = cv_res['model']
print('\nModel trained. CV AUC:', cv_res['cv_auc_mean'])

# Check model coefficients
print('\nModel coefficients:')
for feat, coef in zip(feature_cols, model.coef_[0]):
    print(f'  {feat}: {coef:.4f}')

# Test prediction with sample values
test_cases = [
    {'age_months': 24, 'weight_kg': 12, 'height_cm': 85, 'muac_cm': 14},
    {'age_months': 24, 'weight_kg': 8, 'height_cm': 75, 'muac_cm': 10},  # Low weight/height/MUAC
    {'age_months': 36, 'weight_kg': 10, 'height_cm': 80, 'muac_cm': 11},  # Severe case
]

for i, case in enumerate(test_cases):
    print(f'\nTest case {i+1}: age={case["age_months"]}mo, weight={case["weight_kg"]}kg, height={case["height_cm"]}cm, muac={case["muac_cm"]}cm')
    
    # Compute z-scores
    age = case['age_months']
    weight = case['weight_kg']
    height = case['height_cm']
    
    exp_h = 48 + (age * 1.12)
    exp_w = 3.5 + (age * 0.28)
    exp_wh = 3.5 + ((height - 48) / 1.12) * 0.28
    
    haz = (height - exp_h) / 6.0
    waz = (weight - exp_w) / 2.8
    whz = (weight - exp_wh) / 2.5
    
    case['HAZ'] = haz
    case['WAZ'] = waz
    case['WHZ'] = whz
    
    # Fill missing features with zeros (like the API does)
    x_dict = {c: case.get(c, 0) for c in feature_cols}
    x = np.array([x_dict[c] for c in feature_cols]).reshape(1, -1)
    
    print('  Feature values:', x_dict)
    prob = model.predict_proba(x)[0, 1]
    print(f'  Predicted probability: {prob:.4f} ({prob*100:.1f}%)')
    print(f'  Z-scores - HAZ: {haz:.2f}, WAZ: {waz:.2f}, WHZ: {whz:.2f}')
    
    if prob > 0.7:
        print('  Risk Level: HIGH')
    elif prob > 0.3:
        print('  Risk Level: MODERATE')
    else:
        print('  Risk Level: LOW')
