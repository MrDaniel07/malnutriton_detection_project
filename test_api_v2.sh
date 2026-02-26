#!/bin/bash
# Test script for Malnutrition Detection System v2.0

echo "🏥 Malnutrition Detection System - API Test Suite"
echo "=================================================="
echo ""

API_URL="http://127.0.0.1:5000/api"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -n "Testing: $test_name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -X GET "$API_URL$endpoint")
    elif [ "$method" = "POST" ] && [ -z "$data" ]; then
        response=$(curl -s -X POST "$API_URL$endpoint" \
            -H "Content-Type: application/json")
    else
        response=$(curl -s -X POST "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    # Check for success
    if echo "$response" | grep -q '"status":"success"'; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Response: $response"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Health Check
echo -e "${BLUE}1. HEALTH CHECK${NC}"
run_test "API Health" "GET" "/health"
echo ""

# Test 2: Load Data
echo -e "${BLUE}2. DATA LOADING${NC}"
run_test "Load Synthetic Data" "POST" "/load-data" \
    '{"source": "synthetic"}'
echo ""

# Test 3: Model Training
echo -e "${BLUE}3. MODEL TRAINING${NC}"
run_test "Train Model (5-fold CV)" "POST" "/train" \
    '{"C": 1.0, "cv_folds": 5}'
sleep 1
echo ""

# Test 4: Single Prediction
echo -e "${BLUE}4. PREDICTION${NC}"
run_test "Predict Single Patient (High Risk)" "POST" "/predict" \
    '{"patient_data": {"age_months": 18, "weight_kg": 8.5, "height_cm": 70, "muac_cm": 12.0, "HH1": 50, "HH2": 45}}'

run_test "Predict Single Patient (Low Risk)" "POST" "/predict" \
    '{"patient_data": {"age_months": 48, "weight_kg": 18.0, "height_cm": 110, "muac_cm": 16.0, "HH1": 50, "HH2": 45}}'
echo ""

# Test 5: Model Info
echo -e "${BLUE}5. MODEL INFORMATION${NC}"
run_test "Get Model Info" "GET" "/model-info"
echo ""

# Test 6: Feature Statistics
echo -e "${BLUE}6. FEATURE STATISTICS${NC}"
run_test "Get Feature Stats" "GET" "/feature-stats"
echo ""

# Test 7: CSV Training
echo -e "${BLUE}7. CSV TRAINING (NEW)${NC}"
echo -n "Testing: Train Model from CSV... "
csv_response=$(curl -s -X POST "$API_URL/train-csv" \
    -F "file=@csv_output/large_synthetic.csv")

if echo "$csv_response" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $csv_response"
    ((TESTS_FAILED++))
fi
echo ""

# Test 8: Save Model
echo -e "${BLUE}8. MODEL PERSISTENCE${NC}"
run_test "Save Model to Disk" "POST" "/save-model" \
    '{"path": "models/test_malnutrition_model"}'
echo ""

# Summary
echo "=================================================="
echo -e "${BLUE}TEST SUMMARY${NC}"
echo "=================================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "🎉 System is ready for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Start the API:  python ml_api.py"
    echo "2. Open frontend:  python -m http.server 8000"
    echo "3. Visit:          http://localhost:8000/frontend.html"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Ensure Flask API is running on port 5000"
    echo "2. Check that all dependencies are installed"
    echo "3. Verify CSV file exists at csv_output/large_synthetic.csv"
    echo "4. Check Flask terminal for error messages"
    exit 1
fi
