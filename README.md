# Governed Clinical Trial Patient Screening & Regulatory Audit Agent

> **Lyzr Safe AI & Agent API Architecture Hackathon MVP**  
> *Deterministic Clinical Trial Eligibility Screening, Zero-PHI Safe AI Ingestion Gate, and FDA 21 CFR Part 11 Regulatory Audit Dossiers.*

[![CI/CD Pipeline](https://github.com/Chithra582/clientsafe-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Chithra582/clientsafe-agent/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/pytest-33%20passed-brightgreen)](https://github.com/Chithra582/clientsafe-agent)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/Chithra582/clientsafe-agent)
[![Regulatory](https://img.shields.io/badge/FDA-21%20CFR%20Part%2011-purple)](https://github.com/Chithra582/clientsafe-agent)
[![Safe AI](https://img.shields.io/badge/Lyzr%20Safe%20AI-Zero--PHI-emerald)](https://github.com/Chithra582/clientsafe-agent)

---

## 1. Problem Statement & Context

Clinical trial recruitment delays account for up to **40% of all drug development delays**. Study coordinators manually cross-reference 100+ page clinical protocols against dense, unstructured Electronic Health Records (EHRs) and lab panels.

Standard Large Language Models fail in this regulated domain:
1. **Hallucinated Biomarker Thresholds**: Standard LLMs hallucinate numbers (e.g. evaluating an eGFR of 48 mL/min as meeting a ">= 50" requirement), potentially enrolling ineligible patients and endangering lives.
2. **PHI Leakage into Inference Logs**: Unmasked patient identifiers (Names, MRNs, SSNs, DOBs) leak into cloud inference and prompt telemetry.
3. **Lack of Regulatory Auditability**: Regulators (FDA 21 CFR Part 11) require immutable, step-by-step mathematical reasoning with page and line citations—not opaque natural language summaries.

### The Solution: ClinSafe Agent
An autonomous, governed multi-agent clinical screening platform implementing the **Lyzr Triad** (`Environment`, `Agent`, `Inference`) and **Lyzr Safe AI**:
- **Zero-PHI Scrubbing Gate**: Presidio and HIPAA Safe Harbor regex strip 100% of raw patient identifiers before any inference log or agent receives the record.
- **Purely Deterministic Evaluation Engine**: Biomarker thresholds and inclusion/exclusion logic are evaluated strictly in deterministic code, eliminating mathematical hallucinations.
- **Medical Safety Agent**: Cross-checks patient comorbidities and medications against local subsets of **SNOMED-CT**, **ICD-10-CM**, and **LOINC** codes.
- **Human-In-The-Loop (HITL) Governance**: When confidence drops below **90%**, the agent automatically triggers an HITL pause and dispatches an alert webhook (e.g., to Slack/Teams).
- **FDA 21 CFR Part 11 Audit Dossier**: Generates downloadable PDF and JSON dossiers with per-criterion protocol page citations and digital signature seals.
- **Lyzr AIMS Event Stream**: Streams live telemetry of decisions, latency, and compliance status across all Triad layers.
- **Enterprise Database & Broker Adapter**: Production-ready support for **PostgreSQL** and **RabbitMQ** with seamless SQLite/In-Memory fallback.
- **Dedicated Secrets Management**: Multi-tier secrets resolution supporting **HashiCorp Vault**, Docker secrets, and environment providers.

---

## 2. Architecture & The Lyzr Triad

```mermaid
flowchart TD
    subgraph Ingestion["01 | Environment Layer: Ingestion"]
        P[Clinical Protocol PDF / TXT\nPhase 3 NSCLC Study ONCO-2026-X] --> ING[Ingestion Engine]
        E[Patient EHR Records JSON / Text / PDF] --> ING
    end

    subgraph SafeAI["02 | Lyzr Safe AI: PHI Scrubbing Gate"]
        ING --> PHI[PHI Scrubbing Agent\nPresidio + Clinical Regex]
        PHI --> SCR[De-identified Record & Cryptographic Diff\nZero Raw PHI Past Gate]
    end

    subgraph AgentLayer["03 | Agent Layer: Protocol Extraction"]
        P --> CRIT[Protocol Criteria Agent\nStructured JSON Rule Extraction]
        CRIT --> RULES[Structured Criteria Rules JSON\neGFR, ANC, Platelets, Washout, ECOG]
    end

    subgraph InferenceLayer["04 | Deterministic Inference & Medical Safety"]
        SCR --> DET[Deterministic Screening Agent\nPure Code Operator Evaluator\nNO LLM Hallucinations]
        RULES --> DET
        DET --> SAF[Medical Safety Agent\nOntology Lookups: SNOMED, ICD-10, LOINC]
    end

    subgraph Governance["05 | Governance & Human-In-The-Loop"]
        DET --> CONF[Confidence Scorer]
        SAF --> CONF
        CONF -->|Confidence >= 90%| DEC[Final Decision:\nELIGIBLE / INELIGIBLE]
        CONF -->|Confidence < 90%| HITL[HITL Regulatory Pause\nWebhook Dispatched to Slack/Teams]
    end

    subgraph AuditLayer["06 | Lyzr AIMS & Regulatory Audit Layer"]
        DEC --> AUD[Audit Agent & Lyzr AIMS Streamer]
        HITL --> AUD
        AUD --> PDF[FDA 21 CFR Part 11 Audit Dossier\nPDF + JSON with Page Citations]
        AUD --> AIMS[Lyzr AIMS Live Event Stream Dashboard]
    end
```

---

## 3. Pipeline Stages (7-Step Sequence)

| Stage | Module | Functionality |
|---|---|---|
| **1. Ingestion** | `backend/routes/ingestion.py` | Multi-format parser for protocol PDFs (via `pdfplumber`/`pypdf`) and synthetic EHR records (JSON, TXT, PDF). |
| **2. PHI Scrubbing** | `agents/phi_scrubber_agent.py` | Redacts SSN, MRN, Names, DOBs, Addresses, Phone numbers before LLM inference. Outputs cryptographic SHA-256 diff proof. |
| **3. Protocol Criteria** | `agents/protocol_criteria_agent.py` | Extracts inclusion and exclusion rules into structured JSON conditions (operators, cutoffs, units, protocol source page). |
| **4. Screening Engine** | `agents/screening_agent.py` | Deterministically executes rule matching in pure Python code (eliminating LLM numerical hallucination). |
| **5. Medical Safety** | `agents/medical_safety_agent.py` | Validates contraindications, drug washouts, and active autoimmune flares against local SNOMED-CT, ICD-10-CM, and LOINC tables. |
| **6. Confidence & HITL** | `agents/confidence_scorer.py` | Evaluates multi-agent agreement. Penalizes missing fields (-15%) and ambiguities (-12%). If confidence < 90%, activates HITL pause and webhook. |
| **7. Regulatory Audit** | `agents/audit_agent.py` | Compiles FDA 21 CFR Part 11 compliant audit dossiers (PDF via ReportLab + JSON) citing exact protocol pages for every single criterion. |

---

## 4. Enterprise Architecture & Reliability Upgrades

In response to production readiness standards, the system includes:

### A. CI/CD Automation (`.github/workflows/ci.yml`)
- Multi-version testing matrix across Python 3.11 and 3.12.
- Automated code linting via `flake8`.
- Complete test suite execution with code coverage reporting (`pytest-cov`).
- Automated multi-stage Docker build verification.

### B. Production State & Event Management (`backend/database.py`, `backend/event_bus.py`)
- **Database Adapter**: Dual-engine adapter supporting **PostgreSQL** (`postgresql://...`) in production with connection pooling and **SQLite** for zero-dependency local runs.
- **Indexed Schema**: High-performance indexes on `run_id`, `created_at`, `final_decision`, and `patient_pseudonym`.
- **Event Bus Abstraction**: Pluggable pub-sub broker supporting **RabbitMQ / AMQP** (`amqp://...`), **Redis**, and an asynchronous in-memory queue with disk journaling.

### C. Dedicated Secrets Management (`backend/secrets_manager.py`)
- Secrets resolution hierarchy:
  1. **HashiCorp Vault** KV v2 engine (`VAULT_ADDR`, `VAULT_TOKEN`).
  2. **Docker / Kubernetes Secrets** mounted at `/run/secrets/`.
  3. Secure environment variables (`.env`).
- Automatic key masking in telemetry and audit logs.

---

## 5. Repository Structure

```
clinsafe-agent/
├── .github/
│   └── workflows/
│       └── ci.yml                # Automated CI/CD pipeline (Lint, Test, Docker)
├── agents/                       # Multi-agent logic and orchestration
│   ├── __init__.py
│   ├── aims_streamer.py          # Lyzr AIMS live telemetry and event logger
│   ├── audit_agent.py            # FDA 21 CFR Part 11 Dossier generator (PDF + JSON)
│   ├── confidence_scorer.py      # Governance agreement scoring & HITL webhook pause
│   ├── llm_interface.py          # Pluggable LLM wrapper (Lyzr / OpenAI / Claude / Fallback)
│   ├── medical_safety_agent.py   # SNOMED, ICD-10, LOINC contraindication auditor
│   ├── orchestrator.py           # Pipeline runner coordinating Triad stages
│   ├── phi_scrubber_agent.py     # Presidio & regex PHI redaction with diff audit
│   ├── protocol_criteria_agent.py# Protocol parsing and criteria extraction
│   └── screening_agent.py        # Pure deterministic rule evaluation engine
├── backend/                      # FastAPI web services & state adapters
│   ├── __init__.py
│   ├── config.py                 # Multi-tier configuration & secrets
│   ├── database.py               # Dual PostgreSQL & SQLite database adapter
│   ├── event_bus.py              # RabbitMQ / Redis / Memory pub-sub broker
│   ├── main.py                   # FastAPI server entrypoint
│   ├── models.py                 # Pydantic schemas
│   ├── secrets_manager.py        # HashiCorp Vault / Docker secrets provider
│   └── routes/
│       ├── aims.py               # AIMS live events & dashboard analytics
│       ├── dossier.py            # PDF & JSON dossier downloads
│       ├── ingestion.py          # File upload & synthetic presets
│       ├── screening.py          # Pipeline execution & history
│       └── webhook.py            # HITL webhook receiver & logs
├── data/                         # Ontologies and synthetic test samples
│   ├── ontologies/
│   │   ├── icd10_contraindications.csv
│   │   ├── loinc_biomarkers.csv
│   │   └── snomed_terms.csv
│   └── synthetic_samples/
│       ├── protocol_nsclc_phase3.pdf # Formatted Phase 3 protocol document
│       ├── protocol_nsclc_phase3.txt # Full clinical protocol text
│       ├── patient_01_eligible.json
│       ├── patient_01_note.txt
│       ├── patient_02_ineligible.json
│       ├── patient_02_note.txt
│       ├── patient_03_borderline.json
│       └── patient_03_note.txt
├── frontend/                     # Interactive Clinical Workstation UI
│   ├── app.js                    # Client application logic
│   ├── index.html                # Responsive clinical dashboard (Tailwind CSS)
│   └── styles.css
├── tests/                        # 33 comprehensive unit & integration tests
│   ├── test_aims_streamer.py
│   ├── test_api_endpoints.py
│   ├── test_audit_agent.py
│   ├── test_confidence_scorer.py
│   ├── test_criteria_agent.py
│   ├── test_medical_safety.py
│   ├── test_phi_scrubber.py
│   ├── test_pipeline.py
│   ├── test_screening_agent.py
│   └── test_secrets_and_database.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 6. Quickstart & Installation

### Option A: Local Python Run

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Chithra582/clientsafe-agent.git
   cd clientsafe-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment** (Optional; system runs fully offline via high-precision fallback):
   ```bash
   cp .env.example .env
   ```

4. **Run the FastAPI Server**:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Open the Web Interface**:
   Visit [http://localhost:8000](http://localhost:8000) in your browser.

---

### Option B: Docker Compose

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## 7. Live Demo & Synthetic Test Cases

The application includes 3 realistic synthetic patients accessible via 1-click preset buttons:

### Test Case 1: Jonathan Vance (Clearly Eligible)
- **Clinical Profile**: 60yo Male, Stage IV NSCLC, ECOG 1, eGFR 68 mL/min (>=50), ANC 2800 (>=1500), Platelets 215k (>=100k), Washout 47 days (>=28 days), no autoimmune disease, stable cardiac function.
- **Expected Outcome**: `ELIGIBLE`
- **Confidence Score**: `100.0%`
- **Governance**: Cleared, official FDA PDF dossier generated.

### Test Case 2: Marcus A. Sterling (Clearly Ineligible)
- **Clinical Profile**: 68yo Male, Stage IV NSCLC, ECOG 2 (disqualified: protocol requires <=1), eGFR 38 mL/min (disqualified: protocol requires >=50, CKD Stage 4), Active Ulcerative Colitis (disqualified: autoimmune contraindication ICD-10 K50.90 / SNOMED 40103004).
- **Expected Outcome**: `INELIGIBLE`
- **Confidence Score**: `98.0%` (High certainty disqualification)
- **Failed Rules**: `INC-3`, `INC-4`, `EXC-2`.

### Test Case 3: Eleanor Rigby-Hughes (Borderline / Ambiguous)
- **Clinical Profile**: 54yo Female, Stage IV NSCLC, ECOG 1, eGFR 51 mL/min (borderline close to 50 cutoff), prior nivolumab completed 25 days ago (strictly short of 28-day washout), **Platelet count is unrecorded/missing**.
- **Expected Outcome**: `REQUIRES_HUMAN_OVERVIEW`
- **Confidence Score**: `43.0%` (< 90% threshold)
- **Governance**: **HITL Pause Activated!** Automated webhook dispatched to `POST /api/webhook/hitl`.

---

## 8. Comprehensive Automated Test Suite (33 Tests)

Run the entire unit and integration test suite:

```bash
python -m pytest tests/ -v
```

### Test Suite Summary:
```text
tests/test_aims_streamer.py::test_aims_emit_and_retrieve_events PASSED   [  3%]
tests/test_api_endpoints.py::test_api_health PASSED                      [  6%]
tests/test_api_endpoints.py::test_api_presets PASSED                     [  9%]
tests/test_api_endpoints.py::test_api_screen_preset_patient_1 PASSED     [ 12%]
tests/test_api_endpoints.py::test_api_screen_preset_patient_2 PASSED     [ 15%]
tests/test_api_endpoints.py::test_api_screen_preset_patient_3_hitl PASSED [ 18%]
tests/test_api_endpoints.py::test_api_aims_endpoints PASSED              [ 21%]
tests/test_api_endpoints.py::test_api_webhook_logging PASSED             [ 24%]
tests/test_audit_agent.py::test_dossier_json_generation PASSED           [ 27%]
tests/test_audit_agent.py::test_dossier_pdf_generation_valid_bytes PASSED [ 30%]
tests/test_confidence_scorer.py::test_high_confidence_eligible PASSED    [ 33%]
tests/test_confidence_scorer.py::test_high_certainty_ineligible PASSED   [ 36%]
tests/test_confidence_scorer.py::test_penalties_trigger_hitl_pause_below_90 PASSED [ 39%]
tests/test_criteria_agent.py::test_extract_criteria_from_protocol_text PASSED [ 42%]
tests/test_criteria_agent.py::test_pdf_parsing_fallback PASSED           [ 45%]
tests/test_medical_safety.py::test_safety_check_clean_patient PASSED     [ 48%]
tests/test_medical_safety.py::test_safety_check_active_contraindication PASSED [ 51%]
tests/test_medical_safety.py::test_safety_check_borderline_ambiguity PASSED [ 54%]
tests/test_phi_scrubber.py::test_redaction_of_all_hipaa_identifiers PASSED [ 57%]
tests/test_phi_scrubber.py::test_structured_json_patient_scrubbing PASSED [ 60%]
tests/test_phi_scrubber.py::test_empty_and_already_clean_text PASSED     [ 63%]
tests/test_phi_scrubber.py::test_sha256_provenance_hashes PASSED         [ 66%]
tests/test_pipeline.py::test_phi_scrubber_redacts_all_identifiers PASSED [ 69%]
tests/test_pipeline.py::test_patient_1_clearly_eligible PASSED           [ 72%]
tests/test_pipeline.py::test_patient_2_clearly_ineligible PASSED         [ 75%]
tests/test_pipeline.py::test_patient_3_borderline_triggers_hitl_pause PASSED [ 78%]
tests/test_pipeline.py::test_unstructured_clinical_note_ingestion PASSED [ 81%]
tests/test_screening_agent.py::test_deterministic_evaluation_eligible PASSED [ 84%]
tests/test_screening_agent.py::test_deterministic_evaluation_ineligible_threshold_failure PASSED [ 87%]
tests/test_screening_agent.py::test_deterministic_evaluation_missing_fields PASSED [ 90%]
tests/test_secrets_and_database.py::test_secrets_manager_resolution PASSED [ 93%]
tests/test_secrets_and_database.py::test_database_adapter_crud PASSED    [ 96%]
tests/test_secrets_and_database.py::test_event_bus_pub_sub PASSED        [100%]

======================== 33 passed, 1 warning in 9.92s ========================
```

---

## 9. Regulatory Compliance Standards

- **FDA 21 CFR Part 11**:
  - Section 11.10(e): Computer-generated, time-stamped audit trails recording the date and time of operator entries and actions.
  - Section 11.50: Signed electronic records citing exact source pages, observed values, and mathematical justifications.
- **HIPAA Safe Harbor Method (45 CFR § 164.514(b)(2))**:
  - Removal of all 18 specified individual identifiers before inference.
  - Zero raw PHI leakage certified with before/after cryptographic diff audit.
