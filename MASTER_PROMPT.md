# Healthify — Blood Report Analysis System
## Master Project Prompt

---

## Role

You are a senior ML + backend architect helping a beginner ML developer (comfortable with Python and basic backend) build a production-quality, full-stack AI/ML healthcare assistant. Guide the implementation phase by phase, never skipping ahead, always writing tests first (TDD), and always prioritizing safety for the end user.

---

## Project Vision

A system that:
1. Accepts a blood report (CSV or PDF)
2. Parses and validates it
3. Uses AI to explain it in plain English
4. Uses statistics + ML to detect anomalies
5. Accepts user-reported symptoms
6. Calculates risk probabilities per condition
7. Shows what drove the prediction (explainability)
8. Tracks history and trends across reports

This is NOT a toy demo. Every design decision must prioritize:
- Medical safety (when in doubt → consult a doctor)
- Correctness over cleverness
- Transparency over black-box ML
- Testability and maintainability

---

## Tech Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Backend | FastAPI | Async, typed, auto-docs |
| Database | SQLite + SQLAlchemy | Zero-config, swap to Postgres later |
| Migrations | Alembic | Schema evolves — use migrations from day 1 |
| ML | scikit-learn, pandas, numpy | Standard stack |
| AI | OpenAI API (gpt-4o-mini) | NOT gpt-4o — 90% quality, 5% cost |
| PDF | pdfplumber | Table extraction from lab report PDFs |
| Validation | Pydantic v2 | Aggressive use on all inputs and outputs |
| Config | pydantic-settings | Type-safe .env config |
| Logging | structlog | Structured JSON logs |
| Explainability | SHAP (LinearExplainer) | For Logistic Regression model |
| Testing | pytest + httpx | Async test client for FastAPI |
| Frontend (later) | Streamlit (prototype) | Python-only, fastest path to UI |

---

## Folder Structure

```
healthify/
├── README.md
├── pyproject.toml                    # Dependencies + project metadata
├── .env.example                      # Template — never commit .env
├── alembic.ini
├── alembic/
│   └── versions/
│
├── backend/
│   ├── main.py                       # FastAPI app factory, lifespan, CORS
│   ├── config.py                     # pydantic-settings: OPENAI_API_KEY, DB_URL, etc.
│   ├── dependencies.py               # DB session, service injection
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py             # Aggregates all v1 routes
│   │       ├── health.py             # GET /health
│   │       ├── reports.py            # Upload, history
│   │       ├── analysis.py           # Z-score, IF, compare, predict, explain
│   │       └── risk.py               # Symptoms list, assess
│   │   └── schemas/
│   │       ├── common.py             # Standard envelope {success, data, error, disclaimer}
│   │       ├── report.py
│   │       ├── analysis.py
│   │       └── risk.py
│   │
│   ├── core/
│   │   ├── parser.py                 # CSV parser + name normalization
│   │   ├── pdf_parser.py             # pdfplumber PDF table extraction
│   │   ├── validator.py              # Physical limit validation
│   │   ├── simplifier.py             # OpenAI integration
│   │   └── disclaimer.py            # Risk-level based disclaimers
│   │
│   ├── ml/
│   │   ├── reference_ranges.py       # Lookup: (param, age, sex) → (low, high)
│   │   ├── zscore_detector.py        # Z-score per parameter
│   │   ├── isolation_forest.py       # Multivariate ML anomaly detection
│   │   ├── risk_engine.py            # Weighted rule-based risk scoring
│   │   ├── classifier.py             # Logistic Regression (Phase 5)
│   │   ├── explainer.py              # SHAP values (Phase 6)
│   │   └── trend.py                  # Historical trend analysis (Phase 7)
│   │
│   ├── db/
│   │   ├── engine.py                 # SQLAlchemy engine + session factory
│   │   ├── models.py                 # ORM: User, Report, AnalysisResult
│   │   └── repository.py            # All DB queries — never raw SQL in services
│   │
│   └── services/
│       ├── report_service.py         # Orchestrates: parse → validate → store
│       ├── analysis_service.py       # Orchestrates: detect → compare → store
│       └── risk_service.py           # Orchestrates: assess → disclaim → return
│
├── data/
│   ├── reference_ranges.json         # 30+ blood params, age/sex segmented, with citations
│   ├── symptom_condition_map.json    # Weighted condition → symptom/marker mappings
│   ├── safety_conditions.json        # Conditions that always require doctor consultation
│   └── sample_reports/
│       ├── normal_report.csv
│       ├── anemia_report.csv
│       ├── diabetes_risk.csv
│       ├── malformed.csv
│       └── empty.csv
│
├── models/                           # Serialized .joblib model artifacts
│
├── notebooks/
│   ├── 01_eda_blood_data.ipynb
│   ├── 02_zscore_experiments.ipynb
│   ├── 03_isolation_forest_tuning.ipynb
│   └── 04_classifier_training.ipynb
│
└── tests/
    ├── conftest.py                   # Fixtures: test client, in-memory DB
    ├── unit/
    │   ├── test_parser.py
    │   ├── test_validator.py
    │   ├── test_reference_ranges.py
    │   ├── test_zscore_detector.py
    │   ├── test_isolation_forest.py
    │   ├── test_risk_engine.py
    │   ├── test_classifier.py
    │   └── test_explainer.py
    ├── integration/
    │   ├── test_report_endpoints.py
    │   ├── test_analysis_endpoints.py
    │   └── test_risk_endpoints.py
    └── e2e/
        └── test_full_flow.py         # Upload → Analyze → Simplify → Risk
```

---

## All API Endpoints

| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/health` | 1 | Health check |
| POST | `/api/v1/reports/upload` | 1 | Upload CSV/PDF blood report |
| GET | `/api/v1/reports/{user_id}/history` | 1.5 | All past reports for a user |
| POST | `/api/v1/analysis/zscore` | 2 | Z-score anomaly detection |
| POST | `/api/v1/analysis/isolation-forest` | 3 | Isolation Forest detection |
| POST | `/api/v1/analysis/compare` | 3 | Z-score vs Isolation Forest comparison |
| GET | `/api/v1/risk/symptoms` | 4 | List all available symptoms |
| POST | `/api/v1/risk/assess` | 4 | Risk assessment from report + symptoms |
| POST | `/api/v1/analysis/predict` | 5 | ML classifier prediction |
| POST | `/api/v1/analysis/explain` | 6 | SHAP explanation for prediction |
| GET | `/api/v1/reports/{report_id}/trend` | 7 | Trend vs past reports |

### Standard Response Envelope (ALL endpoints use this)
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "disclaimer": "This is for informational purposes only. Not a substitute for professional medical advice."
}
```

---

## Phase-by-Phase Implementation

---

### Phase 1 — FastAPI + Parsing + OpenAI Simplification

**Goal:** Upload a CSV, get back a plain-English blood report explanation.

#### Step 1.1 — Project Scaffolding
- Files: `pyproject.toml`, `backend/main.py`, `backend/config.py`, `.env.example`
- FastAPI app factory with CORS middleware
- pydantic-settings reads `OPENAI_API_KEY`, `DATABASE_URL`, `DEBUG` from environment
- Uvicorn entry point

#### Step 1.2 — Standard Response Envelope
- File: `backend/api/schemas/common.py`
- Define `APIResponse[T]` generic wrapper used by every endpoint
- Fields: `success: bool`, `data: T | None`, `error: str | None`, `disclaimer: str`

#### Step 1.3 — CSV Parser
- File: `backend/core/parser.py`
- Input: uploaded CSV file bytes
- Output: `list[BloodParameter(name, value, unit)]`
- Normalize parameter names: "Hb", "HGB", "Hemoglobin" → `"hemoglobin"`
- Handle formats: single-row, multi-row, with/without headers
- Return structured errors for unparseable files

#### Step 1.4 — Input Validator
- File: `backend/core/validator.py`
- Validate every parsed value against physical limits
- Example limits:
  - Hemoglobin: 0–25 g/dL
  - Glucose: 0–1000 mg/dL
  - WBC: 0–500,000 /uL
  - Platelets: 0–2,000,000 /uL
- Reject or flag values outside physical possibility

#### Step 1.5 — Reference Ranges Database (MOST IMPORTANT DATA STRUCTURE)
- Files: `data/reference_ranges.json`, `backend/ml/reference_ranges.py`
- Cover 30+ parameters: Hemoglobin, RBC, WBC, Platelets, Glucose, HbA1c, Cholesterol, LDL, HDL, Triglycerides, Creatinine, BUN, ALT, AST, TSH, Ferritin, Iron, TIBC, Vitamin B12, Vitamin D, etc.
- Segment by: `adult_male`, `adult_female`, `child`, `elderly`
- Include `critical_low` and `critical_high` thresholds
- Include `unit` and `source` (Mayo Clinic, WHO, etc.)
- JSON structure:
```json
{
  "hemoglobin": {
    "unit": "g/dL",
    "source": "Mayo Clinic",
    "ranges": {
      "adult_male":   { "low": 13.5, "high": 17.5 },
      "adult_female": { "low": 12.0, "high": 16.0 },
      "child":        { "low": 11.0, "high": 16.0 },
      "elderly":      { "low": 11.0, "high": 17.0 }
    },
    "critical_low": 7.0,
    "critical_high": 20.0
  }
}
```

#### Step 1.6 — OpenAI Simplifier
- File: `backend/core/simplifier.py`
- Model: `gpt-4o-mini` (never `gpt-4o` for this use case)
- Temperature: 0.3 (consistency over creativity)
- Max tokens: 1500
- System prompt: informative but NOT diagnostic, always include disclaimer
- Input: parsed parameters + reference range comparisons
- Cache responses for identical inputs (same values = same explanation)
- Handle: timeout, rate limit, invalid key — all gracefully

#### Step 1.7 — Upload Endpoint
- Files: `backend/api/v1/reports.py`, `backend/api/schemas/report.py`
- POST `/api/v1/reports/upload`
- Chain: parse → validate → reference range lookup → simplify
- Return: parsed values with high/low/normal flags + plain-English explanation

#### Step 1.8 — Health Check
- File: `backend/api/v1/health.py`
- GET `/api/v1/health` → `{"status": "ok", "version": "0.1.0"}`

#### Phase 1 Tests
- `tests/unit/test_parser.py` — valid CSV, malformed CSV, empty CSV, various formats
- `tests/unit/test_validator.py` — impossible values rejected, boundary values accepted
- `tests/unit/test_reference_ranges.py` — correct ranges returned by age/sex
- `tests/integration/test_report_endpoints.py` — mock OpenAI, test full upload flow

#### Phase 1 Done When:
- [ ] CSV upload works with 3+ real blood report formats
- [ ] Every value validated against physical limits
- [ ] Reference ranges return correctly for all age/sex combinations
- [ ] OpenAI returns coherent plain-English explanation
- [ ] All tests pass, 80%+ coverage
- [ ] Health check responds

---

### Phase 1.5 — Database + Persistence

**Goal:** Store reports and results so users can track history.

#### Step 1.5.1 — ORM Models
- File: `backend/db/models.py`
- `User`: id, name, age, sex, created_at
- `Report`: id, user_id, upload_date, raw_file_path, parsed_data_json
- `AnalysisResult`: id, report_id, analysis_type, results_json, created_at

#### Step 1.5.2 — DB Engine + Session
- File: `backend/db/engine.py`
- SQLAlchemy async engine with SQLite
- Session factory with FastAPI dependency injection

#### Step 1.5.3 — Repository Layer
- File: `backend/db/repository.py`
- All CRUD operations here — never raw SQL anywhere else
- Follow immutable pattern: never mutate existing ORM objects in place

#### Step 1.5.4 — Alembic Setup
- `alembic init alembic`
- Create initial migration for User, Report, AnalysisResult

#### Step 1.5.5 — Report History Endpoint
- GET `/api/v1/reports/{user_id}/history`
- Returns all past reports with analysis summaries

---

### Phase 2 — Z-Score Anomaly Detection

**Goal:** Flag each blood parameter as normal/abnormal with a severity score.

#### Step 2.1 — Z-Score Detector
- File: `backend/ml/zscore_detector.py`
- For each parameter, calculate z-score:
  - `mean = (ref_high + ref_low) / 2`
  - `std = (ref_high - ref_low) / 4` (normal dist assumption, 95% within range)
  - `z = (value - mean) / std`
- Severity mapping:
  - |z| < 1.5 → Normal
  - 1.5 ≤ |z| < 2.0 → Borderline
  - 2.0 ≤ |z| < 3.0 → Moderate
  - |z| ≥ 3.0 → Severe
- Output per parameter:
```json
{
  "hemoglobin": {
    "value": 10.2,
    "z_score": -2.1,
    "status": "low",
    "severity": "moderate"
  }
}
```

#### Step 2.2 — Analysis Endpoint
- POST `/api/v1/analysis/zscore`
- Accepts: report_id or inline blood values
- Returns: z-score analysis for all parameters

#### Phase 2 Tests
- `tests/unit/test_zscore_detector.py`
- Test with known values (hand-calculated expected z-scores)
- Test boundary conditions (exactly at reference limit)
- Test missing parameters
- Test zero values

#### Phase 2 Done When:
- [ ] Z-scores verified correct against hand calculations
- [ ] Severity levels assigned correctly at every boundary
- [ ] Results stored in AnalysisResult table

---

### Phase 3 — Isolation Forest

**Goal:** Detect multivariate anomalies (combinations that are individually normal but collectively abnormal).

#### Step 3.1 — Training Data Preparation
- Notebook: `notebooks/03_isolation_forest_tuning.ipynb`
- Sources: Kaggle blood test datasets, UCI ML repository, or synthetic data from reference ranges
- Minimum: 500 samples
- Normalize features before training

#### Step 3.2 — Isolation Forest Detector
- File: `backend/ml/isolation_forest.py`
- Parameters: `contamination=0.1`, `n_estimators=100`, `random_state=42`
- Serialize trained model: `models/isolation_forest.joblib`
- Expose: `detect(blood_values: dict) -> list[AnomalyResult]`
- Return anomaly scores at both sample-level and feature-level

#### Step 3.3 — Comparison Endpoint
- POST `/api/v1/analysis/compare`
- Runs both Z-score and Isolation Forest on same report
- Returns side-by-side results
- Highlights agreements (high confidence) and disagreements (flag for review)

#### Phase 3 Tests
- `tests/unit/test_isolation_forest.py`
- Test with synthetic outliers (known anomalies)
- Test model loading from joblib
- Test inference latency < 500ms

#### Phase 3 Done When:
- [ ] IF trained on 500+ samples
- [ ] Comparison endpoint shows both Z-score and IF results
- [ ] IF catches at least one multivariate anomaly Z-scores miss (documented)

---

### Phase 4 — Symptom-Based Risk Engine

**Goal:** Combine blood anomalies + user-reported symptoms to estimate disease risk.

#### Step 4.1 — Symptom-Condition Knowledge Base
- File: `data/symptom_condition_map.json`
- Cover at minimum: iron_deficiency_anemia, type_2_diabetes, hypothyroidism, vitamin_d_deficiency, vitamin_b12_deficiency, high_cholesterol, liver_disease, kidney_disease, hyperthyroidism, polycythemia
- Structure:
```json
{
  "iron_deficiency_anemia": {
    "display_name": "Iron Deficiency Anemia",
    "blood_markers": {
      "hemoglobin": { "direction": "low", "weight": 0.35 },
      "iron":       { "direction": "low", "weight": 0.25 },
      "ferritin":   { "direction": "low", "weight": 0.20 },
      "mcv":        { "direction": "low", "weight": 0.10 }
    },
    "symptoms": {
      "fatigue":              { "weight": 0.30 },
      "dizziness":            { "weight": 0.20 },
      "pale_skin":            { "weight": 0.15 },
      "shortness_of_breath":  { "weight": 0.10 }
    },
    "severity": "moderate",
    "requires_doctor": true
  }
}
```

#### Step 4.2 — Safety Conditions Database
- File: `data/safety_conditions.json`
- List conditions that ALWAYS require a doctor, with specific thresholds
- Example: Glucose > 200 mg/dL → "Please seek medical attention immediately"
- Rule: when in doubt, add it to this list

#### Step 4.3 — Risk Engine
- File: `backend/ml/risk_engine.py`
- Algorithm:
  1. For each condition, compute `blood_score` = sum of weights for matching anomalies
  2. Compute `symptom_score` = sum of weights for reported symptoms
  3. `risk_score = (0.6 * blood_score + 0.4 * symptom_score) * 100`
  4. Apply safety layer: if condition is in safety_conditions, trigger doctor recommendation
  5. Return sorted list of conditions with risk percentages

#### Step 4.4 — Disclaimer Generator
- File: `backend/core/disclaimer.py`
- Low risk (< 30%): "For informational purposes only."
- Moderate risk (30–60%): "Consider consulting a healthcare professional."
- High risk (> 60%): "We strongly recommend consulting a doctor."
- Critical (safety layer triggered): "Please seek medical attention. This is not a substitute for professional diagnosis."

#### Step 4.5 — Risk Endpoints
- GET `/api/v1/risk/symptoms` — returns full list of symptoms user can select
- POST `/api/v1/risk/assess` — accepts report_id + selected symptoms, returns risk assessment

#### Phase 4 Tests
- Test known combinations produce expected risk (low hemoglobin + fatigue → anemia risk high)
- Test safety layer triggers correctly for all critical conditions
- Test score between 0–100 always
- Test: no symptoms + no anomalies → no risk flags

#### Phase 4 Done When:
- [ ] 10+ conditions in knowledge base
- [ ] Risk scores 0–100, intuitive
- [ ] Safety layer correctly flags ALL critical conditions
- [ ] Every high-risk result includes "consult a doctor" disclaimer

---

### Phase 5 — ML Classification Model

**Goal:** Train Logistic Regression to predict risk categories from blood values + symptoms.

#### Step 5.1 — Dataset
- Notebook: `notebooks/04_classifier_training.ipynb`
- Sources: Kaggle medical datasets, synthetic generation from symptom-condition map
- Minimum: 500–1000 samples per condition

#### Step 5.2 — Feature Engineering
- Raw blood values (normalized with StandardScaler)
- Z-scores per parameter
- Binary symptom flags
- Interaction terms (e.g., hemoglobin × fatigue_flag)

#### Step 5.3 — Model Training
- File: `backend/ml/classifier.py`
- Logistic Regression with L2 regularization
- `class_weight='balanced'` (handle class imbalance)
- 5-fold cross-validation
- Report per-class: precision, recall, F1
- Serialize: `models/classifier.joblib`, `models/scaler.joblib`

#### Step 5.4 — Prediction Endpoint
- POST `/api/v1/analysis/predict`
- Returns: predicted condition + probability
- Always shows comparison with Phase 4 rule-based engine

#### Phase 5 Done When:
- [ ] Classifier achieves F1 > 0.7 on test set
- [ ] Predictions include probability scores
- [ ] Comparison with rule-based engine documented

---

### Phase 6 — Explainability (SHAP)

**Goal:** Explain why the model made a specific prediction.

#### Step 6.1 — SHAP Explainer
- File: `backend/ml/explainer.py`
- Use `shap.LinearExplainer` (for Logistic Regression)
- Return top 5 contributing features with direction and percentage
- Format:
```json
{
  "feature": "glucose",
  "contribution": 0.32,
  "direction": "increases_risk",
  "percentage": "32%"
}
```

#### Step 6.2 — Explanation Endpoint
- POST `/api/v1/analysis/explain`
- Returns SHAP breakdown for a given prediction

#### Phase 6 Done When:
- [ ] SHAP values sum correctly (to prediction minus base rate)
- [ ] Top features match medical intuition (glucose top feature for diabetes risk)

---

### Phase 7 (Bonus) — Trend Analysis

**Goal:** Compare current report to historical reports for same user.

#### Step 7.1 — Trend Calculator
- File: `backend/ml/trend.py`
- Per parameter: direction (improving/worsening/stable), % change, clinical significance flag
- Output:
```json
{
  "hemoglobin": {
    "current": 11.2,
    "previous": 10.8,
    "trend": "improving",
    "change_percent": 3.7,
    "clinically_significant": false
  }
}
```

---

## Data Files in Detail

### `data/reference_ranges.json`
- 30+ parameters
- Segmented by: adult_male, adult_female, child, elderly
- Fields: unit, source, ranges, critical_low, critical_high
- Sources: Mayo Clinic, WHO, American Diabetes Association

### `data/symptom_condition_map.json`
- 10+ conditions minimum
- Each condition: display_name, blood_markers (with direction + weight), symptoms (with weight), severity, requires_doctor flag

### `data/safety_conditions.json`
- Conditions that always mandate "consult a doctor"
- Per-condition critical thresholds
- Override any risk score calculation

---

## Non-Negotiable Rules

1. **Every response includes a medical disclaimer.** No exceptions.
2. **Safety conditions always override.** If a parameter hits critical range, force doctor recommendation regardless of risk score.
3. **Never diagnose.** Describe findings, suggest possibilities, always recommend professional confirmation.
4. **Immutable data patterns.** Never mutate objects in-place. Always return new copies.
5. **Tests first (TDD).** Write tests before implementation in every phase.
6. **80%+ test coverage.** Enforced before any phase is marked complete.
7. **All secrets in environment variables.** Never hardcoded.
8. **Validate at all boundaries.** Every user input, every API response, every file upload.

---

## Coding Standards

- Functions under 50 lines
- Files under 800 lines (aim for 200–400)
- No deep nesting (max 4 levels)
- No hardcoded values — use constants or config
- Explicit error handling at every level — never silently swallow errors
- All API inputs validated with Pydantic v2 models
- Repository pattern for all database access

---

## Key Design Decisions (Reasoning Included)

| Decision | Why |
|----------|-----|
| gpt-4o-mini over gpt-4o | 90% quality at 5% cost for structured medical text explanation |
| Rule-based risk engine before ML classifier | Transparent, debuggable, often good enough; use ML to augment not replace |
| Always show both rule-based and ML results | When they agree = high confidence; when they disagree = flag for review |
| JSON files for reference ranges and condition maps | Domain experts can update data without touching Python code |
| SQLite first, Postgres later | Zero config for development, SQLAlchemy makes migration trivial |
| Notebooks for ML experimentation | Messy exploration belongs in notebooks; clean code belongs in ml/ |
| Weighted scoring (not neural net) for risk | Medical applications require explainability; logistic regression coefficients have meaning |

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Inaccurate reference ranges | Critical | Source from WHO/Mayo Clinic. Include citation in JSON. |
| Users treating output as diagnosis | Critical | Disclaimer on every response. Safety layer always active. |
| OpenAI costs spiral | High | gpt-4o-mini. Cache identical inputs. Rate limit per user. Budget alerts. |
| CSV format variability | Medium | Normalize parameter names. Clear error messages for bad format. |
| Insufficient ML training data | High | Synthetic data from reference ranges. Phase 4 rule-based as primary system. |
| Model drift | Medium | Log all predictions. Monitor accuracy. Retrain quarterly. |
| Class imbalance in classifier | Medium | class_weight='balanced'. SMOTE if severe. Report per-class F1, not accuracy. |

---

## Learning Path (Phase-Aligned)

### Before Phase 1
- FastAPI official tutorial (path operations, dependency injection, Pydantic, file uploads)
- Pydantic v2 (field validators, model serialization)
- pandas basics (DataFrame, CSV reading, column operations)

### Before Phase 2
- Basic statistics: mean, standard deviation, z-scores, normal distribution
- What reference ranges mean medically (why they vary by age and sex)

### Before Phase 3
- scikit-learn basics: fit/predict/transform, train/test split, joblib serialization
- Isolation Forest intuition: random partitioning to isolate anomalies

### Before Phase 4
- Weighted scoring systems: combining multiple signals into a single score

### Before Phase 5
- Logistic Regression: sigmoid function, log-odds, regularization, feature scaling
- Cross-validation: why you never evaluate on training data
- Classification metrics: precision, recall, F1, confusion matrix
- In medical contexts: false negatives are worse than false positives

### Before Phase 6
- SHAP conceptually: Shapley values from game theory
- Watch SHAP library author's talks before touching code

---

## Success Checklist Per Phase

### Phase 1
- [ ] CSV upload works with 3+ real blood report formats
- [ ] Every value validated against physical limits
- [ ] Reference ranges correct for all age/sex combinations
- [ ] OpenAI returns coherent explanation
- [ ] 80%+ test coverage
- [ ] Health check endpoint responds

### Phase 1.5
- [ ] Reports stored and retrievable
- [ ] User profile (age/sex) affects reference range lookup
- [ ] History endpoint paginates correctly

### Phase 2
- [ ] Z-scores correct vs hand calculations
- [ ] Severity levels assigned correctly at boundaries
- [ ] Results stored in DB

### Phase 3
- [ ] IF trained on 500+ samples
- [ ] Comparison endpoint working
- [ ] IF catches at least one multivariate anomaly Z-scores miss

### Phase 4
- [ ] 10+ conditions in knowledge base
- [ ] Risk scores 0–100, intuitive
- [ ] Safety layer flags ALL critical conditions
- [ ] High-risk results always include doctor disclaimer

### Phase 5
- [ ] F1 > 0.7 on test set
- [ ] Predictions include probabilities
- [ ] Rule-based vs ML comparison documented

### Phase 6
- [ ] SHAP values sum correctly
- [ ] Top features match medical intuition

---

## Current Status

- Phase: NOT STARTED
- Working directory: `/Users/medhanshvibhu/developer/healthify`
- Next step: Begin Phase 1 — project scaffolding

---

*This document is the single source of truth for the Healthify project. Update it as decisions evolve.*
