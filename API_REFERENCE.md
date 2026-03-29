# Healthify — API Reference

**Base URL:** `http://localhost:8000`
**All responses** use the same envelope — check `success` first, then read `data`.

---

## Response Envelope

Every endpoint returns this wrapper:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "disclaimer": "This analysis is for informational purposes only..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if the request succeeded |
| `data` | object \| null | Payload — present when `success` is `true` |
| `error` | string \| null | Human-readable error message — present when `success` is `false` |
| `disclaimer` | string \| null | Medical safety notice — always show this to the user |

**Error example:**
```json
{
  "success": false,
  "data": null,
  "error": "No blood parameters could be found in the uploaded file.",
  "disclaimer": null
}
```

---

## Disclaimer levels

The `disclaimer` string changes based on severity. Always render it.

| Situation | Disclaimer text (approximate) |
|-----------|-------------------------------|
| All normal | "This analysis is for informational purposes only…" |
| 1–2 anomalies | "Some findings may require attention… consider consulting a healthcare professional." |
| 3+ anomalies | "Your report contains findings that should be evaluated by a doctor…" |
| Critical value | "IMPORTANT: Your results contain critically abnormal values. Please seek medical attention promptly." |

---

## Endpoints

### 1. Health Check

```
GET /api/v1/health
```

No parameters. Returns server status.

**Response `data`:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### 2. Upload Blood Report

```
POST /api/v1/reports/upload
Content-Type: multipart/form-data
```

Upload a blood report file. Parses it, validates values, looks up reference ranges, and returns an AI-generated plain-English explanation.

**Request fields (form-data):**

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `file` | file | Yes | — | CSV, PDF, JPG, JPEG, PNG, or WEBP. Max 10 MB. |
| `age` | integer | No | `30` | Patient age. Range: 0–120. Affects reference ranges. |
| `sex` | string | No | `"male"` | `"male"` or `"female"`. Affects reference ranges. |

**Accepted file formats:**
- `.csv` — plain CSV with parameter names and values
- `.pdf` — lab report PDF (table or text extraction)
- `.jpg` / `.jpeg` / `.png` / `.webp` — photo of a blood report (AI vision extraction)

**Response `data`:**

```json
{
  "parameter_count": 8,
  "anomaly_count": 2,
  "parameters": [
    {
      "name": "hemoglobin",
      "raw_name": "HGB",
      "value": 10.2,
      "unit": "g/dL",
      "status": "low",
      "is_critical": false,
      "ref_low": 12.0,
      "ref_high": 16.0,
      "ref_unit": "g/dL"
    }
  ],
  "unrecognized": ["someUnknownColumn"],
  "validation_errors": [],
  "simplification": "Hemoglobin measures the oxygen-carrying protein in red blood cells...",
  "simplification_cached": false
}
```

**`parameters` array — each item:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Canonical parameter name (e.g. `"hemoglobin"`) |
| `raw_name` | string | Name as it appeared in the file (e.g. `"HGB"`) |
| `value` | number | Numeric value |
| `unit` | string | Unit string (e.g. `"g/dL"`) |
| `status` | string | `"low"` / `"normal"` / `"high"` / `"unknown"` |
| `is_critical` | boolean | `true` if value is at a medically critical level |
| `ref_low` | number \| null | Lower bound of normal range |
| `ref_high` | number \| null | Upper bound of normal range |
| `ref_unit` | string \| null | Unit of the reference range |

**Other `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `parameter_count` | integer | Number of valid parameters parsed |
| `anomaly_count` | integer | Number of parameters outside normal range |
| `unrecognized` | string[] | Column names that could not be matched to any known parameter |
| `validation_errors` | string[] | Values rejected as physically impossible (e.g. Hemoglobin = 500) |
| `simplification` | string \| null | Full AI-generated plain-English explanation of all parameters. `null` if OpenAI call failed. |
| `simplification_cached` | boolean | `true` if the explanation came from cache (same inputs submitted before) |

**HTTP error codes:**

| Code | Reason |
|------|--------|
| 413 | File exceeds 10 MB |
| 422 | Unsupported file type, invalid `age`/`sex` values |

---

### 3. Z-Score Analysis

```
POST /api/v1/analysis/zscore
Content-Type: application/json
```

Run statistical anomaly detection on blood parameters. Each parameter gets a Z-score and severity rating.

**Request body:**

```json
{
  "parameters": [
    { "name": "hemoglobin", "value": 10.2, "unit": "g/dL" },
    { "name": "glucose",    "value": 210.0, "unit": "mg/dL" }
  ],
  "age": 30,
  "sex": "female"
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `parameters` | array | No | `[]` | List of blood parameters |
| `parameters[].name` | string | Yes | — | Canonical parameter name (see parameter list below) |
| `parameters[].value` | number | Yes | — | Numeric value |
| `parameters[].unit` | string | No | `""` | Unit string |
| `age` | integer | No | `30` | Range: 0–120 |
| `sex` | string | No | `"male"` | `"male"` or `"female"` |

**Response `data`:**

```json
{
  "scores": {
    "hemoglobin": {
      "value": 10.2,
      "unit": "g/dL",
      "z_score": -2.08,
      "status": "low",
      "severity": "moderate",
      "ref_low": 12.0,
      "ref_high": 16.0,
      "is_critical": false
    },
    "glucose": {
      "value": 210.0,
      "unit": "mg/dL",
      "z_score": 2.95,
      "status": "high",
      "severity": "severe",
      "ref_low": 70.0,
      "ref_high": 100.0,
      "is_critical": false
    }
  },
  "summary": {
    "total_parameters": 2,
    "anomaly_count": 2,
    "severe_count": 1,
    "has_critical": false
  }
}
```

**`scores` — each parameter:**

| Field | Type | Description |
|-------|------|-------------|
| `value` | number | Input value |
| `unit` | string | Unit string |
| `z_score` | number | Deviation from mean in standard deviations. Negative = low, positive = high. |
| `status` | string | `"low"` / `"normal"` / `"high"` |
| `severity` | string | `"normal"` / `"borderline"` / `"moderate"` / `"severe"` |
| `ref_low` | number | Lower bound of normal range |
| `ref_high` | number | Upper bound of normal range |
| `is_critical` | boolean | `true` if value crosses the critical threshold |

**Severity thresholds (Z-score magnitude):**

| Severity | Z-score range |
|----------|--------------|
| normal | \|z\| < 1.0 |
| borderline | 1.0 ≤ \|z\| < 2.0 |
| moderate | 2.0 ≤ \|z\| < 3.0 |
| severe | \|z\| ≥ 3.0 |

**`summary`:**

| Field | Type | Description |
|-------|------|-------------|
| `total_parameters` | integer | Parameters with a known reference range |
| `anomaly_count` | integer | Parameters outside normal range |
| `severe_count` | integer | Parameters with severity `"severe"` |
| `has_critical` | boolean | Any parameter at a critical level |

> Parameters with no known reference range are silently skipped and will not appear in `scores`.

---

### 4. Isolation Forest Analysis

```
POST /api/v1/analysis/isolation-forest
Content-Type: application/json
```

Run ML-based multivariate anomaly detection. Scores the entire panel as a whole rather than per-parameter. Trained on 12,050 rows from 9 Kaggle datasets.

**Request body:** same shape as Z-score.

```json
{
  "parameters": [
    { "name": "hemoglobin", "value": 6.5 },
    { "name": "rbc",        "value": 2.8 },
    { "name": "mcv",        "value": 62.0 }
  ],
  "age": 30,
  "sex": "female"
}
```

**Response `data`:**

```json
{
  "anomaly_score": -0.142,
  "is_anomalous": true,
  "confidence": "medium"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `anomaly_score` | number | Continuous score. Positive values indicate a normal panel, negative values indicate an anomalous pattern. Typical range: −0.25 to +0.15. |
| `is_anomalous` | boolean | `true` when `anomaly_score` < −0.10 |
| `confidence` | string | `"high"` (≥50% of known features provided) / `"medium"` (20–50%) / `"low"` (<20%) |

> Missing parameters are filled with training-set median values. Confidence reflects how much of the panel was actually provided.

---

### 5. Compare (Z-score vs Isolation Forest)

```
POST /api/v1/analysis/compare
Content-Type: application/json
```

Runs both detectors in one call and returns side-by-side results. Use this when you want to show both methods to the user.

**Request body:** same shape as Z-score / Isolation Forest.

**Response `data`:**

```json
{
  "zscore": {
    "scores": { ... },
    "summary": {
      "total_parameters": 6,
      "anomaly_count": 3,
      "severe_count": 1,
      "has_critical": false
    }
  },
  "isolation_forest": {
    "anomaly_score": -0.142,
    "is_anomalous": true,
    "confidence": "high"
  },
  "agreement": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `zscore` | object | Full Z-score result (same schema as endpoint 3) |
| `isolation_forest` | object | Full IF result (same schema as endpoint 4) |
| `agreement` | boolean | `true` if both methods reach the same conclusion (both flag anomaly, or both say normal) |

> When `agreement` is `false`, prefer showing the Z-score breakdown — it gives per-parameter detail. Use the IF score as a secondary signal.

---

## Canonical Parameter Names

Use these exact strings in the `name` field of every request. The parser also accepts common aliases (e.g. `"HGB"`, `"Hb"`, `"A1c"`) but the API always returns canonical names.

| Name | Description | Typical unit |
|------|-------------|-------------|
| `hemoglobin` | Hemoglobin | g/dL |
| `rbc` | Red blood cell count | M/uL |
| `wbc` | White blood cell count | /uL |
| `platelets` | Platelet count | /uL |
| `hematocrit` | Hematocrit | % |
| `mcv` | Mean corpuscular volume | fL |
| `mch` | Mean corpuscular hemoglobin | pg |
| `mchc` | Mean corpuscular Hgb concentration | g/dL |
| `glucose` | Blood glucose | mg/dL |
| `hba1c` | Glycated hemoglobin | % |
| `cholesterol` | Total cholesterol | mg/dL |
| `ldl` | LDL cholesterol | mg/dL |
| `hdl` | HDL cholesterol | mg/dL |
| `triglycerides` | Triglycerides | mg/dL |
| `creatinine` | Creatinine | mg/dL |
| `bun` | Blood urea nitrogen | mg/dL |
| `uric_acid` | Uric acid | mg/dL |
| `alt` | Alanine aminotransferase | U/L |
| `ast` | Aspartate aminotransferase | U/L |
| `alp` | Alkaline phosphatase | U/L |
| `bilirubin_total` | Total bilirubin | mg/dL |
| `bilirubin_direct` | Direct bilirubin | mg/dL |
| `albumin` | Albumin | g/dL |
| `protein_total` | Total protein | g/dL |
| `tsh` | Thyroid stimulating hormone | mIU/L |
| `t3` | Triiodothyronine | ng/dL |
| `t4` | Thyroxine | ug/dL |
| `ferritin` | Ferritin | ng/mL |
| `iron` | Serum iron | ug/dL |
| `tibc` | Total iron binding capacity | ug/dL |
| `vitamin_b12` | Vitamin B12 | pg/mL |
| `vitamin_d` | Vitamin D | ng/mL |
| `sodium` | Sodium | mEq/L |
| `potassium` | Potassium | mEq/L |
| `calcium` | Calcium | mg/dL |

---

### 6. List Symptoms

```
GET /api/v1/risk/symptoms
```

Returns all symptom name strings the risk engine understands. Use these exact values in `POST /risk/assess`.

**Response `data`:** `string[]`

```json
["abdominal_pain", "anxiety", "blurred_vision", "bone_pain", "brittle_nails",
 "chest_pain", "cold_hands_feet", "cold_sensitivity", "constipation",
 "decreased_urination", "depression", "dizziness", "dry_skin",
 "excessive_thirst", "fatigue", "frequent_urination", "hair_loss",
 "heat_sensitivity", "jaundice", "joint_pain", "joint_redness",
 "joint_swelling", "memory_problems", "muscle_weakness", "nausea",
 "numbness_tingling", "pale_skin", "rapid_heartbeat", "shortness_of_breath",
 "slow_wound_healing", "swelling_ankles", "tremors", "weight_gain",
 "weight_loss"]
```

---

### 7. Risk Assessment

```
POST /api/v1/risk/assess
Content-Type: application/json
```

Run blood anomaly detection internally then score each condition using blood markers + user-reported symptoms. Apply a safety layer for critical values.

**Request body:**

```json
{
  "parameters": [
    {"name": "hemoglobin", "value": 9.5,  "unit": "g/dL"},
    {"name": "mcv",        "value": 68.0, "unit": "fL"},
    {"name": "ferritin",   "value": 6.0,  "unit": "ng/mL"},
    {"name": "iron",       "value": 35.0, "unit": "ug/dL"},
    {"name": "tibc",       "value": 420.0,"unit": "ug/dL"}
  ],
  "age": 28,
  "sex": "female",
  "symptoms": ["fatigue", "dizziness", "pale_skin"]
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `parameters` | array | No | `[]` | Same parameter objects as Z-score endpoint |
| `age` | integer | No | `30` | Range: 0–120 |
| `sex` | string | No | `"male"` | `"male"` or `"female"` |
| `symptoms` | string[] | No | `[]` | Use strings from `GET /risk/symptoms` — unknown strings are silently ignored |

**Response `data`:**

```json
{
  "conditions": [
    {
      "name": "iron_deficiency_anemia",
      "display_name": "Iron Deficiency Anemia",
      "risk_percent": 72,
      "severity": "moderate",
      "requires_doctor": true,
      "message": "Based on these findings, a consultation with a physician is advisable to evaluate this further.",
      "lifestyle_tips": []
    },
    {
      "name": "vitamin_b12_deficiency",
      "display_name": "Vitamin B12 Deficiency",
      "risk_percent": 12,
      "severity": "moderate",
      "requires_doctor": false,
      "message": "No specific action required at this time.",
      "lifestyle_tips": [
        "Increase intake of animal products: meat, fish, eggs, dairy",
        "If vegetarian or vegan, a B12 supplement is strongly recommended"
      ]
    }
  ],
  "requires_immediate_attention": false,
  "top_condition": "iron_deficiency_anemia"
}
```

**`conditions` — each item:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Canonical condition identifier |
| `display_name` | string | Human-readable condition name |
| `risk_percent` | integer | 0–100 risk score |
| `severity` | string | `"low"` / `"moderate"` / `"high"` |
| `requires_doctor` | boolean | `true` if this condition always needs professional evaluation |
| `message` | string | Contextual guidance message — always display this |
| `lifestyle_tips` | string[] | Practical tips — only populated for mild, non-doctor conditions below 30% risk |

**Top-level `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `conditions` | array | All conditions, sorted by `risk_percent` descending |
| `requires_immediate_attention` | boolean | `true` if any raw value crosses a critical safety threshold (e.g. glucose >200, Hb <7, creatinine >3). When `true`, the disclaimer is escalated to CRITICAL and the UI should display an urgent warning. |
| `top_condition` | string \| null | Name of the highest-scoring condition |

**Safety thresholds that trigger `requires_immediate_attention`:**

| Parameter | Trigger | Reason |
|-----------|---------|--------|
| glucose | > 200 mg/dL | Possible uncontrolled diabetes |
| glucose | < 50 mg/dL | Possible hypoglycaemia |
| hba1c | > 8.0% | Poor glycaemic control |
| hemoglobin | < 7.0 g/dL | Severe anaemia |
| alt / ast | > 200 U/L | Possible acute liver injury |
| creatinine | > 3.0 mg/dL | Possible kidney failure |
| bun | > 100 mg/dL | Possible kidney failure or dehydration crisis |
| potassium | > 6.0 or < 2.5 mEq/L | Cardiac arrhythmia risk |
| sodium | > 155 or < 120 mEq/L | Neurological risk |
| platelets | < 50,000 /uL | Severe bleeding risk |
| wbc | > 30,000 or < 2,000 /uL | Infection / leukaemia risk |

**Known conditions:**

| Condition name | Display name |
|----------------|-------------|
| `iron_deficiency_anemia` | Iron Deficiency Anemia |
| `type_2_diabetes` | Type 2 Diabetes |
| `prediabetes` | Prediabetes |
| `hypothyroidism` | Hypothyroidism |
| `hyperthyroidism` | Hyperthyroidism |
| `vitamin_d_deficiency` | Vitamin D Deficiency |
| `vitamin_b12_deficiency` | Vitamin B12 Deficiency |
| `high_cholesterol` | High Cholesterol |
| `liver_disease` | Liver Disease |
| `chronic_kidney_disease` | Chronic Kidney Disease |
| `gout` | Gout |

---

### 8. ML Prediction

```
POST /api/v1/analysis/predict
Content-Type: application/json
```

Runs the trained Logistic Regression classifier alongside the rule-based risk engine and returns a side-by-side comparison.

**Request body:** same shape as `/risk/assess`

```json
{
  "parameters": [
    {"name": "hemoglobin", "value": 8.0, "unit": "g/dL"},
    {"name": "mcv",        "value": 62.0, "unit": "fL"}
  ],
  "age": 30,
  "sex": "female",
  "symptoms": ["fatigue", "dizziness"]
}
```

**Response `data`:**

```json
{
  "ml_prediction": {
    "top_condition": "iron_deficiency_anemia",
    "top_probability": 0.84,
    "probabilities": [
      {"condition": "iron_deficiency_anemia", "display_name": "Iron Deficiency Anemia", "probability": 0.84},
      {"condition": "healthy",                "display_name": "Healthy",                "probability": 0.07},
      {"condition": "microcytic_anemia",      "display_name": "Microcytic Anemia",      "probability": 0.05}
    ]
  },
  "rule_based": {
    "top_condition": "iron_deficiency_anemia",
    "risk_percent": 72
  },
  "agreement": true,
  "confidence": "high"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ml_prediction.top_condition` | string | Condition with highest predicted probability |
| `ml_prediction.top_probability` | float | 0–1 probability of top condition |
| `ml_prediction.probabilities` | array | All 12 conditions sorted by probability descending |
| `rule_based.top_condition` | string | Top condition from Phase 4 rule engine |
| `rule_based.risk_percent` | integer | Risk % from rule engine (0–100) |
| `agreement` | boolean | `true` when both methods pick the same top condition |
| `confidence` | string | `"high"` when agreement, `"low"` when they disagree |

**Known ML conditions:** `healthy`, `iron_deficiency_anemia`, `normocytic_hypochromic_anemia`, `normocytic_normochromic_anemia`, `microcytic_anemia`, `macrocytic_anemia`, `thrombocytopenia`, `leukemia`, `type_2_diabetes`, `chronic_kidney_disease`, `liver_disease`, `hypothyroidism`

---

### 9. SHAP Explanation

```
POST /api/v1/analysis/explain
Content-Type: application/json
```

Returns the top 5 blood parameters that drove the ML prediction, with direction and percentage contribution. Built on SHAP LinearExplainer.

**Request body:** same as `/predict`, with one optional extra field:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `condition` | string | No | Canonical condition to explain. If omitted, the top predicted condition is explained automatically. |

```json
{
  "parameters": [
    {"name": "hemoglobin", "value": 8.0},
    {"name": "mcv",        "value": 62.0},
    {"name": "mch",        "value": 17.0}
  ],
  "age": 30,
  "sex": "female",
  "symptoms": [],
  "condition": "iron_deficiency_anemia"
}
```

**Response `data`:**

```json
{
  "prediction": {
    "top_condition": "iron_deficiency_anemia",
    "top_probability": 0.84,
    "probabilities": [...]
  },
  "explained_condition": "iron_deficiency_anemia",
  "explanations": [
    {"feature": "hemoglobin",  "contribution": 0.32, "direction": "increases_risk", "percentage": "38%"},
    {"feature": "mcv",         "contribution": 0.21, "direction": "increases_risk", "percentage": "25%"},
    {"feature": "mch",         "contribution": 0.18, "direction": "increases_risk", "percentage": "21%"},
    {"feature": "hematocrit",  "contribution": 0.08, "direction": "increases_risk", "percentage": "9%"},
    {"feature": "rbc",         "contribution": -0.06,"direction": "decreases_risk", "percentage": "7%"}
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `prediction` | object | Full ML prediction (same as `/predict`) |
| `explained_condition` | string | Which condition was explained |
| `explanations` | array | Up to 5 features, sorted by \|contribution\| descending |
| `explanations[].feature` | string | Canonical parameter name |
| `explanations[].contribution` | float | Raw SHAP value — positive pushes toward this condition, negative pushes away |
| `explanations[].direction` | string | `"increases_risk"` or `"decreases_risk"` |
| `explanations[].percentage` | string | Share of total absolute contribution, e.g. `"38%"` |

---

## Quick Start (curl examples)

**Health check:**
```bash
curl http://localhost:8000/api/v1/health
```

**Upload a CSV report:**
```bash
curl -X POST http://localhost:8000/api/v1/reports/upload \
  -F "file=@blood_report.csv" \
  -F "age=28" \
  -F "sex=female"
```

**Z-score analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/zscore \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2, "unit": "g/dL"},
      {"name": "glucose",    "value": 210.0, "unit": "mg/dL"}
    ],
    "age": 28,
    "sex": "female"
  }'
```

**Isolation Forest analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/isolation-forest \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2, "unit": "g/dL"},
      {"name": "rbc",        "value": 3.1,  "unit": "M/uL"},
      {"name": "mcv",        "value": 65.0, "unit": "fL"}
    ],
    "age": 28,
    "sex": "female"
  }'
```

**Compare both detectors:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/compare \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2},
      {"name": "rbc",        "value": 3.1},
      {"name": "mcv",        "value": 65.0}
    ],
    "age": 28,
    "sex": "female"
  }'
```

**List symptoms:**
```bash
curl http://localhost:8000/api/v1/risk/symptoms
```

**Risk assessment:**
```bash
curl -X POST http://localhost:8000/api/v1/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2, "unit": "g/dL"},
      {"name": "rbc",        "value": 3.1,  "unit": "M/uL"}
    ],
    "age": 28,
    "sex": "female",
    "symptoms": ["fatigue", "dizziness", "pale skin"]
  }'
```

**ML prediction:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/predict \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2, "unit": "g/dL"},
      {"name": "rbc",        "value": 3.1,  "unit": "M/uL"},
      {"name": "mcv",        "value": 65.0, "unit": "fL"}
    ],
    "age": 28,
    "sex": "female",
    "symptoms": ["fatigue", "pale skin"]
  }'
```

**SHAP explanation:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/explain \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": [
      {"name": "hemoglobin", "value": 10.2, "unit": "g/dL"},
      {"name": "rbc",        "value": 3.1,  "unit": "M/uL"},
      {"name": "mcv",        "value": 65.0, "unit": "fL"}
    ],
    "age": 28,
    "sex": "female",
    "condition": "iron_deficiency_anemia"
  }'
```

---

## Interactive Docs

When the server is running, full interactive docs (Swagger UI) are available at:

```
http://localhost:8000/docs
```

ReDoc version:
```
http://localhost:8000/redoc
```
