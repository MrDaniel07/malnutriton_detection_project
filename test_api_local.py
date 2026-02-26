#!/usr/bin/env python
"""Test the API prediction endpoint locally"""
import requests
import json

API_BASE = 'http://localhost:5000/api'

# First, load data
print("Loading data...")
load_res = requests.post(f'{API_BASE}/load-data', json={'source': 'synthetic'})
print(f"Load data response: {load_res.json()}\n")

# Train model
print("Training model...")
train_res = requests.post(f'{API_BASE}/train', json={'C': 1.0, 'cv_folds': 5})
print(f"Train response: {train_res.json()}\n")

# Make predictions with different test cases
test_cases = [
    {'age_months': 24, 'weight_kg': 12, 'height_cm': 85, 'muac_cm': 14, 'name': 'Normal case'},
    {'age_months': 24, 'weight_kg': 8, 'height_cm': 75, 'muac_cm': 10, 'name': 'Low weight/MUAC'},
    {'age_months': 36, 'weight_kg': 10, 'height_cm': 80, 'muac_cm': 11, 'name': 'Severe case'},
]

for case in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {case.pop('name')}")
    print(f"Input: {case}")
    
    pred_res = requests.post(f'{API_BASE}/predict', json={'patient_data': case})
    result = pred_res.json()
    
    if result['status'] == 'success':
        print(f"Result: {result['risk_level']} - {result['probability']*100:.1f}%")
        print(f"Feedback: {result['feedback'][:100]}...")
    else:
        print(f"ERROR: {result.get('message')}")
