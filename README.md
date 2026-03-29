# Healthify

A stateless blood report analysis backend built with FastAPI and scikit-learn. It accepts blood parameter values, runs multiple anomaly detection and classification models, and returns structured risk assessments with SHAP-based explanations. No database required.

---

## Features

- **Report parsing** - accepts CSV, PDF, and image uploads; extracts and normalises blood parameters
- **AI simplification** - converts raw values into plain-language summaries via OpenAI
- **Z-score anomaly detection** - per-parameter scoring with age- and sex-adjusted reference ranges
- **Isolation Forest detection** - multivariate ML-based anomaly scoring across 24 blood parameters
- **Rule-based risk engine** - weighted condition scoring from blood markers and user-reported symptoms
- **Logistic Regression classifier** - multi-class condition prediction trained on 6,791 labeled samples across 12 conditions
- **SHAP explanations** - top-5 feature contributions per prediction with direction and percentage

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2 |
| ML | scikit-learn, SHAP, NumPy, pandas |
| AI | OpenAI API |
| Parsing | pdfplumber, Pillow |
| Logging | structlog |
| Tests | pytest, pytest-asyncio, pytest-cov |
| Runtime | Python 3.11+ |

---

## Project Structure

```
healthify/
├── backend/
│   ├── main.py                    # App factory, startup model validation
│   ├── config.py                  # pydantic-settings config
│   ├── api/
│   │   ├── v1/
│   │   │   ├── health.py          # GET /api/v1/health
│   │   │   ├── reports.py         # POST /api/v1/reports/upload
│   │   │   ├── analysis.py        # Z-score, IF, compare, predict, explain
│   │   │   └── risk.py            # Symptoms list, risk assessment
│   │   └── schemas/
│   │       ├── common.py          # APIResponse[T] envelope
│   │       ├── report.py
│   │       ├── analysis.py
│   │       └── risk.py
│   ├── core/
│   │   ├── parser.py              # CSV/text parameter extraction
│   │   ├── pdf_parser.py          # PDF extraction via pdfplumber
│   │   ├── image_parser.py        # Image OCR via OpenAI vision
│   │   ├── simplifier.py          # Plain-language summaries via OpenAI
│   │   ├── validator.py           # Parameter sanity checks
│   │   ├── disclaimer.py          # Severity-based medical disclaimers
│   │   └── reference_ranges.py (ml/) # Age/sex-adjusted normal ranges
│   └── ml/
│       ├── zscore_detector.py     # Z-score per parameter
│       ├── isolation_forest.py    # Isolation Forest inference
│       ├── risk_engine.py         # Weighted rule-based scoring
│       ├── classifier.py          # Logistic Regression inference
│       └── explainer.py           # SHAP LinearExplainer
├── scripts/
│   ├── prepare_training_data.py   # Merges CBC Kaggle datasets for IF training
│   ├── prepare_classifier_data.py # Merges labeled Kaggle datasets
│   ├── train_isolation_forest.py  # Trains and saves IF model
│   └── train_classifier.py        # Trains and saves LR classifier
├── data/
│   ├── reference_ranges.json      # Normal ranges per parameter, age, sex
│   ├── symptom_condition_map.json # 11 conditions with markers and symptoms
│   └── safety_conditions.json     # Critical value thresholds
├── models/                        # Serialized .joblib artifacts (gitignored)
├── tests/
│   ├── unit/                      # Per-module unit tests
│   ├── integration/               # API endpoint tests via TestClient
│   └── e2e/                       # Full upload-to-risk flow
├── API_REFERENCE.md
└── pyproject.toml
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/medhxnsh/Healthily.git
cd Healthily
pip install -e ".[dev]"
```

### 2. Environment variables

```bash
cp .env.example .env
# Set OPENAI_API_KEY in .env (required for report simplification and image parsing)
```

### 3. Train the models

The models are not committed. Run the training scripts once before starting the server.

```bash
# Download CBC datasets from Kaggle into data/kaggle/ first
python scripts/prepare_training_data.py
python scripts/train_isolation_forest.py

python scripts/prepare_classifier_data.py
python scripts/train_classifier.py
```

Required Kaggle datasets (place in `data/kaggle/`):

| File | Used for |
|------|---------|
| `diagnosed_cbc_data_v4.csv` | IF training |
| `cbc information.xlsx` | IF training |
| `diabetes.csv` | Classifier |
| `kidney_disease.csv` | Classifier |
| `indian_liver_patient.csv` | Classifier |
| `thyroid_dataset.csv` | Classifier |
| `heart.csv` | Classifier |

### 4. Run the server

```bash
uvicorn backend.main:app --reload
```

Interactive docs: `http://localhost:8000/docs`

---

## API Overview

All responses use a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "disclaimer": "This analysis is for informational purposes only..."
}
```

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/reports/upload` | Upload CSV/PDF/image report |
| POST | `/api/v1/analysis/zscore` | Z-score anomaly detection |
| POST | `/api/v1/analysis/isolation-forest` | Isolation Forest anomaly detection |
| POST | `/api/v1/analysis/compare` | Side-by-side Z-score vs IF comparison |
| GET | `/api/v1/risk/symptoms` | List all recognised symptom names |
| POST | `/api/v1/risk/assess` | Rule-based condition risk scoring |
| POST | `/api/v1/analysis/predict` | ML classifier + rule-based comparison |
| POST | `/api/v1/analysis/explain` | SHAP feature contributions |

Full request/response documentation is in [API_REFERENCE.md](./API_REFERENCE.md).

---

## Running Tests

```bash
pytest
```

Coverage is enforced at 80%. To run without coverage:

```bash
pytest --no-cov -q
```

---

## ML Models

### Isolation Forest

- Trained on 12,050 CBC samples merged from Kaggle
- 24 blood parameters; missing values filled with training medians
- StandardScaler applied before fit
- Confidence level based on feature coverage: high (50%+), medium (20-50%), low (<20%)

### Logistic Regression Classifier

- Trained on 6,791 labeled samples across 12 conditions
- `class_weight='balanced'` to handle class imbalance
- 5-fold StratifiedKFold CV, weighted F1: 0.745
- 12 conditions: iron deficiency anemia, type 2 diabetes, prediabetes, hypothyroidism, hyperthyroidism, vitamin D deficiency, vitamin B12 deficiency, high cholesterol, liver disease, chronic kidney disease, gout, healthy

### SHAP Explanations

- `shap.LinearExplainer` on the trained Logistic Regression model
- Returns top 5 features per condition class sorted by absolute SHAP value
- Direction: `increases_risk` or `decreases_risk`

---

## Safety Layer

The risk engine applies a hard safety threshold check on every request. If any blood value crosses a critical limit (e.g., glucose >200, hemoglobin <7, platelets <50,000), the response sets `requires_immediate_attention: true` and overrides all lifestyle tips with a prompt to seek medical attention immediately.

---

## Notes

- The system is fully stateless. No database, no session state, no user accounts.
- All ML inference is synchronous and cached with `@lru_cache` on model load.
- OpenAI is only required for report upload simplification and image parsing. All analysis endpoints work without it.
- Model files are large binary artifacts and are not committed to this repository.
