# Early Malnutrition Detection System - Full Stack Setup

A complete AI-powered system for detecting early malnutrition in Nigerian children with a modern, clinical web interface.

## ✨ Latest Updates (v2.0)

- **Modern Clinical UI**: Professional white, blue, and black design with premium gradients
- **Dynamic Body Model**: Human figure scales proportionally with measurements (height, weight, MUAC)
- **Enhanced Animations**: Smooth transitions, shimmer effects, and interactive UX
- **WHO Reference Integration**: Body visualization uses WHO West Africa growth standards as upper bounds
- **Cleaner Design**: Removed disclaimers, improved visual hierarchy, better clinical feedback

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Web Frontend                         │
│  (frontend.html - Modern clinical UI with dynamic body model)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/JSON
                           │ (Port 3000)
┌──────────────────────────▼──────────────────────────────────────┐
│                   Flask API Backend                             │
│  (ml_api.py - REST endpoints for model training & prediction)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Python
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              Machine Learning Models & Data                     │
│  • models.py        - Logistic regression implementation        │
│  • data_utils.py    - Data loading & preprocessing              │
│  • large_synthetic.csv - Training dataset (20k rows)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (3 Steps)

### 1. Install Flask API Dependencies

```bash
cd /Users/wikiwoo/Documents/WORKSPACE/python_proj

# Install Flask and required packages
pip install flask flask-cors scikit-learn pandas numpy joblib

# OR use the requirements file:
pip install -r requirements_api.txt
```

### 2. Start the Flask API Backend

```bash
python ml_api.py
```

Output:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### 3. Open Frontend in Browser

```bash
# In a new terminal, navigate to the project and open the frontend
open frontend.html

# OR use a Python simple HTTP server to serve it (recommended):
python -m http.server 8000
```

Then visit: `http://localhost:8000/frontend.html`

The frontend will:
1. Automatically load data from the Flask API
2. Train the model with 5-fold cross-validation
3. Display the interactive malnutrition risk predictor
4. Show a dynamically scaling body visualization

---

## Features

### 🎨 Modern Clinical UI

- **Color Scheme**: Professional white background with blue (#2563eb, #0ea5e9) and dark navy accents
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Smooth Animations**: Gradient animations, shimmer effects, and fluid transitions
- **Clinical Typography**: Clear hierarchy with professional fonts and spacing

### 👤 Dynamic Body Visualization

The human body model scales in real-time based on patient measurements:

- **Height-based scaling**: Body grows/shrinks with height (45-140 cm range)
- **Weight-based scaling**: Limb thickness increases with weight (2-30 kg range)
- **MUAC-dependent coloring**: 
  - 🔴 Red: MUAC < 75% of reference (severe malnutrition)
  - 🟡 Orange: MUAC 75-90% of reference (moderate malnutrition)  
  - 🟢 Green: MUAC > 90% of reference (normal growth)
- **Real-time updates**: Measurements update as you move sliders
- **WHO reference values**: Uses these standards for 60 months (5 years) West African child:
  - Height: 115 cm
  - Weight: 20 kg
  - MUAC: 17 cm

### Backend API Endpoints

#### `POST /api/health`
Health check endpoint.
```bash
curl http://localhost:5000/api/health
```

#### `POST /api/load-data`
Load training dataset (default: 20,000 synthetic records).
```bash
curl -X POST http://localhost:5000/api/load-data \
  -H "Content-Type: application/json" \
  -d '{"source": "synthetic"}'
```

Response:
```json
{
  "status": "success",
  "rows": 20000,
  "columns": 1064,
  "malnutrition_cases": 5146
}
```

#### `POST /api/train`
Train logistic regression model with cross-validation.
```bash
curl -X POST http://localhost:5000/api/train \
  -H "Content-Type: application/json" \
  -d '{"C": 1.0, "cv_folds": 5}'
```

Response:
```json
{
  "status": "success",
  "metrics": {
    "auc": 0.9877,
    "auc_std": 0.0026,
    "num_features": 27,
    "training_samples": 19961
  },
  "features": ["HH1", "HH2", "LN", "UF1", "UF2", ...]
}
```

#### `POST /api/predict`
Make prediction for a single patient.
```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "patient_data": {
      "age_months": 24,
      "weight_kg": 10,
      "height_cm": 75,
      "muac_cm": 13,
      "HH1": 50,
      "HH2": 45
    }
  }'
```

Response:
```json
{
  "status": "success",
  "probability": 0.78,
  "percentage": "78.0%",
  "risk_level": "HIGH",
  "risk_color": "red",
  "feedback": "High malnutrition risk. Immediate clinical assessment recommended. Consider referral to nutrition specialist.",
  "patient_data": {...}
}
```

#### `GET /api/model-info`
Get model information and feature list.
```bash
curl http://localhost:5000/api/model-info
```

#### `GET /api/feature-stats`
Get statistics for all features (for slider ranges).
```bash
curl http://localhost:5000/api/feature-stats
```

#### `POST /api/save-model`
Save trained model to disk.
```bash
curl -X POST http://localhost:5000/api/save-model \
  -H "Content-Type: application/json" \
  -d '{"path": "models/malnutrition_model"}'
```

---

## Frontend Components

### Left Panel: Patient Data Entry
- **CSV Upload**: Drag-and-drop or click to train model on bulk patient data
- **Age Slider**: Adjust from 0-60 months
- **Weight Slider**: Adjust from 2-30 kg
- **Height Slider**: Adjust from 45-140 cm
- **MUAC Slider**: Adjust from 7-25 cm (Mid Upper Arm Circumference)
- **Live Value Display**: Current value shown in blue badge

### Center Panel: Anthropometric Visualization
- **Dynamic SVG Body Model**: Scales with patient measurements
- **Color-Coded Body**: 
  - Red for high malnutrition risk
  - Orange for moderate risk
  - Green for normal growth
- **Measurement Labels**: Shows height, weight, and MUAC on the figure
- **Growth Status**: Indicator showing normal/monitor/deficit status

### Right Panel: Risk Assessment Results
- **Risk Badge**: Color-coded (RED/ORANGE/GREEN) with risk level
- **Probability Percentage**: Large, animated number showing risk percentage
- **Progress Bar**: Visual representation with shimmer animation
- **Clinical Feedback**: Specific clinical guidance based on risk level
- **NO DISCLAIMER**: Clean, clinical presentation

---

## Risk Assessment Levels

| Risk Level | Probability | Color | Action |
|------------|-------------|-------|--------|
| 🔴 HIGH | > 70% | Red | Immediate clinical assessment recommended |
| 🟡 MODERATE | 30-70% | Orange | Follow-up screening and counseling |
| 🟢 LOW | < 30% | Green | Continue routine monitoring |

---

## File Structure

```
python_proj/
├── app.py                          # Streamlit UI (original)
├── ml_api.py                       # Flask REST API backend (UPDATED)
├── frontend.html                   # React web interface (MODERNIZED)
├── models.py                       # ML model implementation
├── data_utils.py                   # Data loading utilities
├── requirements_api.txt            # Flask dependencies
├── csv_output/
│   └── large_synthetic.csv         # Training dataset (20,000 rows)
└── README_FULLSTACK.md             # This file
```

---

## Deployment Options

### Option 1: Local Development

```bash
# Terminal 1: Start Flask API
python ml_api.py

# Terminal 2: Serve frontend
python -m http.server 8000
# Visit http://localhost:8000/frontend.html
```

### Option 2: Docker Containerization

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements_api.txt .
RUN pip install -r requirements_api.txt

COPY . .

EXPOSE 5000
CMD ["python", "ml_api.py"]
```

Build and run:
```bash
docker build -t malnutrition-api .
docker run -p 5000:5000 malnutrition-api
```

### Option 3: Cloud Deployment (Heroku)

```bash
# Install Heroku CLI
# Login and create app
heroku create malnutrition-detection-api

# Deploy
git push heroku main

# Set frontend to point to Heroku URL:
# Update frontend.html: const API_BASE = 'https://malnutrition-detection-api.herokuapp.com/api'
```

### Option 4: React Native Mobile App

For React Native integration:

1. Install React Native CLI
2. Create project: `npx react-native init MalnutritionApp`
3. Install axios: `npm install axios`
4. Adapt the React web component to React Native components
5. Replace fetch with axios calls to the Flask API

---

## Training Your Own Data

### CSV Format Requirements

Your CSV file should contain:

**Required columns (one of these):**
- `any_mal` (existing target: 0/1 for healthy/malnourished)

**OR**
- `WHZ` (Weight-for-Height Z-score)
- `HAZ` (Height-for-Age Z-score)
- `WAZ` (Weight-for-Age Z-score)

**Recommended numeric features:**
- `age_months` - Child age in months
- `weight_kg` - Weight in kilograms
- `height_cm` - Height in centimeters
- `muac_cm` - MUAC in centimeters
- `HH1`, `HH2`, `HH7` - MICS household indicators
- And other numeric MICS columns

Example format:
```
age_months,weight_kg,height_cm,muac_cm,WHZ,HAZ,WAZ,HH1,HH7
24,10.5,82,13.2,-1.5,-1.2,-1.8,50,24
36,14.2,95,14.5,-0.8,-0.5,-1.0,50,24
```

### Upload Steps

1. Click **"Batch Predict CSV"** in the left panel
2. Select your CSV file
3. Wait for the batch prediction to complete
4. Review per-patient risk levels and probabilities in the results table

---

## Model Performance

**Logistic Regression (Lagos/Ogun Region on 20k Synthetic Data)**

| Metric | Value |
|--------|-------|
| Cross-Validated AUC | 0.9877 ± 0.0026 |
| Accuracy | 97.7% |
| Precision (Malnutrition) | 91% |
| Recall (Malnutrition) | 97% |
| Training Samples | 19,961 |
| Features Used | 27 numeric |

**Top Predictive Features:**
1. WHZ (Weight-for-Height Z-score) - coefficient: -8.48
2. WAZ (Weight-for-Age Z-score) - coefficient: -6.36
3. HAZ (Height-for-Age Z-score) - coefficient: -3.64
4. CDOI (Child Date of Interview) - coefficient: +0.66
5. CDOB (Child Date of Birth) - coefficient: -0.64

---

## Troubleshooting

### Issue: "Connection refused" when frontend tries to call API

**Solution:** Make sure Flask API is running on port 5000
```bash
python ml_api.py
```

### Issue: CORS error in browser console

**Solution:** Flask-CORS is already included in ml_api.py, but check:
1. Flask app has `CORS(app)` enabled
2. Browser is on http://localhost:8000, API on http://localhost:5000

### Issue: CSV upload fails

**Solution:** Ensure your CSV has:
1. Numeric columns for features
2. Either `WHZ`, `HAZ`, `WAZ` columns OR `any_mal` column
3. No special characters in filenames

### Issue: Model takes too long to train

**Solution:** Reduce cv_folds in training:
```json
{"cv_folds": 3}
```

### Issue: Body visualization not updating

**Solution:** Check browser console for errors. Make sure:
1. React is loading properly
2. API is responding with predictions
3. JavaScript is enabled

---

## Next Steps

1. **Mobile App**: Develop React Native or Flutter version for field deployment
2. **Database**: Add PostgreSQL backend to store patient records
3. **Authentication**: Implement JWT for secure API access
4. **Analytics**: Track prediction accuracy over time
5. **Multi-language**: Add Yoruba, Hausa, Igbo support
6. **Offline Mode**: Enable app to work without internet connection

---

## References

- WHO Child Growth Standards: https://www.who.int/tools/child-growth-standards
- MICS Surveys: https://mics.unicef.org/
- Flask Documentation: https://flask.palletsprojects.com/
- React Documentation: https://react.dev/

---

## Support

For issues or questions:
1. Check the API logs in terminal running `ml_api.py`
2. Review browser console for client-side errors
3. Check CSV file formatting for training issues
4. Verify Flask and dependencies are properly installed

