#!/bin/bash
# API Test Examples - Use these to test the Flask backend

API_BASE="http://localhost:5000/api"

echo "===== Early Malnutrition Detection API Tests ====="
echo ""

# Test 1: Health Check
echo "1. Health Check"
echo "curl $API_BASE/health"
curl $API_BASE/health
echo ""
echo ""

# Test 2: Load Data
echo "2. Load Synthetic Data"
echo "curl -X POST $API_BASE/load-data -H 'Content-Type: application/json' -d '{\"source\": \"synthetic\"}'"
curl -X POST $API_BASE/load-data \
  -H "Content-Type: application/json" \
  -d '{"source": "synthetic"}'
echo ""
echo ""

# Test 3: Train Model  
echo "3. Train Model (5-fold cross-validation)"
echo "curl -X POST $API_BASE/train -H 'Content-Type: application/json' -d '{\"C\": 1.0, \"cv_folds\": 5}'"
curl -X POST $API_BASE/train \
  -H "Content-Type: application/json" \
  -d '{"C": 1.0, "cv_folds": 5}'
echo ""
echo ""

# Test 4: Get Model Info
echo "4. Get Model Information"
echo "curl $API_BASE/model-info"
curl $API_BASE/model-info
echo ""
echo ""

# Test 5: Get Feature Statistics
echo "5. Get Feature Statistics (for UI slider ranges)"
echo "curl $API_BASE/feature-stats"
curl $API_BASE/feature-stats | python -m json.tool | head -50
echo ""
echo ""

# Test 6: Prediction - Low Risk Child
echo "6. Make Prediction (Low Risk - Healthy Child)"
echo "Well-nourished child: age=36mo, weight=15.5kg, height=98cm, muac=15.5cm"
curl -X POST $API_BASE/predict \
  -H "Content-Type: application/json" \
  -d '{
    "patient_data": {
      "HH1": 50,
      "HH2": 45,
      "LN": 1,
      "UF1": 1,
      "UF2": 1,
      "UF6": 1,
      "UF7": 1,
      "UF8D": 15,
      "UF8Y": 2020,
      "AG2": 36,
      "AN1": 1,
      "HAP": 0.5,
      "HAZ": 0.5,
      "HAM": -0.2,
      "WAP": 0.5,
      "WAZ": 0.3,
      "WAM": -0.1,
      "WHP": 0.4,
      "WHZ": 0.2,
      "WHM": -0.15,
      "HH7": 24,
      "CDOI": 20230215,
      "CDOB": 20201215,
      "CAGE": 36,
      "CAGED": 36,
      "chweight": 3,
      "wscore": 5
    }
  }' | python -m json.tool
echo ""
echo ""

# Test 7: Prediction - High Risk Child
echo "7. Make Prediction (High Risk - Malnourished Child)"
echo "Malnourished child: age=18mo, weight=8kg, height=70cm, muac=12cm"
curl -X POST $API_BASE/predict \
  -H "Content-Type: application/json" \
  -d '{
    "patient_data": {
      "HH1": 50,
      "HH2": 45,
      "LN": 1,
      "UF1": 1,
      "UF2": 1,
      "UF6": 1,
      "UF7": 1,
      "UF8D": 15,
      "UF8Y": 2020,
      "AG2": 18,
      "AN1": 1,
      "HAP": -2.5,
      "HAZ": -2.3,
      "HAM": -3.1,
      "WAP": -2.0,
      "WAZ": -1.9,
      "WAM": -2.5,
      "WHP": -2.8,
      "WHZ": -2.6,
      "WHM": -3.2,
      "HH7": 24,
      "CDOI": 20230215,
      "CDOB": 20221215,
      "CAGE": 18,
      "CAGED": 18,
      "chweight": 1,
      "wscore": 1
    }
  }' | python -m json.tool
echo ""
echo ""

# Test 8: Save Model
echo "8. Save Trained Model"
echo "curl -X POST $API_BASE/save-model -H 'Content-Type: application/json' -d '{\"path\": \"models/malnutrition_model\"}'"
curl -X POST $API_BASE/save-model \
  -H "Content-Type: application/json" \
  -d '{"path": "models/malnutrition_model"}'
echo ""
echo ""

echo "===== Tests Complete ====="
echo ""
echo "Expected Results:"
echo "✅ Test 1: status: ok"
echo "✅ Test 2: status: success, 20000 rows loaded"
echo "✅ Test 3: status: success, AUC ≈ 0.9877"
echo "✅ Test 4: 27 numeric features"
echo "✅ Test 5: Statistics for each feature (min, max, mean, etc)"
echo "✅ Test 6: probability ~0.1-0.3 (low risk)"
echo "✅ Test 7: probability ~0.7-0.9 (high risk)"
echo "✅ Test 8: Model saved successfully"
