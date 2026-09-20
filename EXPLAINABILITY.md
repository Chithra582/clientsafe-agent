# Explainability & Decision Governance: ClinSafe Agent

This document provides a comprehensive regulatory and technical explanation of **how ClinSafe Agent decides**, **the data it uses**, and **its operational limitations**, satisfying the transparency requirements of **FDA 21 CFR Part 11**, **EU AI Act (High-Risk AI Systems)**, and the **OpenGAP Specification**.

---

## 1. How the Agent Decides

ClinSafe Agent rejects "black-box" decision making. Instead of relying on free-form generative LLM judgment to determine patient enrollment—which suffers from stochastic hallucination on numbers—the agent employs a **hybrid architecture**: LLMs are restricted to initial information structuring, while **all eligibility decisions are computed deterministically in verified Python code**.

### Decision Pipeline Architecture

```
[Patient Record + Clinical Protocol]
                 │
                 ▼
    ┌──────────────────────────┐
    │ 01. Safe AI Scrubbing    │ ──► Masks 100% of PHI (Names, MRN, SSN, DOB, Phone)
    └──────────────────────────┘     Produces cryptographic SHA-256 before/after diff
                 │
                 ▼
    ┌──────────────────────────┐
    │ 02. Criteria Structuring │ ──► Extracts protocol into structured JSON rules
    └──────────────────────────┘     (field, op, value, unit, source_page)
                 │
                 ▼
    ┌──────────────────────────┐
    │ 03. Pure Code Evaluation │ ──► Evaluates patient values against criteria rules
    └──────────────────────────┘     Pure code execution (No LLM numbers hallucination)
                 │
                 ▼
    ┌──────────────────────────┐
    │ 04. Medical Safety Audit │ ──► Cross-checks contraindications against
    └──────────────────────────┘     SNOMED-CT, ICD-10-CM, and LOINC ontologies
                 │
                 ▼
    ┌──────────────────────────┐
    │ 05. Confidence Scoring   │ ──► Multi-agent agreement - missing lab penalties
    └──────────────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
Confidence >= 90%    Confidence < 90%
       │                   │
[ELIGIBLE / INELIGIBLE] [REQUIRES_HUMAN_OVERVIEW]
                            │
                      (Fires HITL Webhook to Coordinator)
```

### Deterministic Rule Evaluation Logic
Every protocol criterion is converted into a deterministic predicate:
- **Numeric Biomarkers**: Evaluated strictly using arithmetic operators (`>=`, `<=`, `>`, `<`). For example, `eGFR >= 50.0 mL/min`:
  - If patient observed value is `68.0`, predicate resolves to `PASS`.
  - If patient observed value is `38.0`, predicate resolves to `FAIL`.
- **Exclusion Conditions**: Evaluated with negation logic. For example, `EXC-2: Autoimmune disease == True`:
  - If patient has active ulcerative colitis (`True`), exclusion triggers -> rule status `FAIL (Excluded)`.
- **Missing Data Handling**: If a biomarker is missing or unrecorded (e.g. hemolyzed platelet sample), the rule status is explicitly marked `UNKNOWN` rather than guessed.

### Confidence Scoring & Governance Formula
The composite confidence score $C \in [0.10, 1.00]$ is calculated as follows:

$$C = \text{BaseAgreement} - \sum \text{Penalties}$$

1. **Base Agreement**:
   - `Screening ELIGIBLE` + `Safety SAFE`: $1.00$
   - `Screening INELIGIBLE` + `Safety CONTRAINDICATION_FLAGGED`: $0.98$
   - `Screening INELIGIBLE` + `Safety SAFE`: $0.95$
   - `Screening/Safety Disagreement`: $0.65$
   - `Uncertain / Missing Inputs`: $0.82$
2. **Penalties**:
   - Missing required lab biomarker (`UNKNOWN`): $-15\%$ per field.
   - Borderline or ambiguous safety boundary (e.g. eGFR within $\pm 3$ units of threshold, or washout within 3 days of cutoff): $-12\%$ per occurrence.
3. **Human-In-The-Loop (HITL) Regulatory Gate**:
   - If $C < 90.0\%$, the decision is **automatically overridden to `REQUIRES_HUMAN_OVERVIEW`**.
   - An automated webhook notification is dispatched to the Clinical Research Coordinator (CRC) to initiate manual oversight.

---

## 2. The Data It Uses

ClinSafe Agent operates exclusively on explicit, auditable medical datasets:

### 1. Clinical Study Protocols (Input)
- Formats: High-density clinical trial PDFs or standardized protocol text (e.g., Phase 3 NSCLC Study ONCO-2026-X).
- Data Extracted: Protocol identifier, study title, inclusion criteria, exclusion criteria, washout windows, performance scale cutoffs (ECOG/KPS), and target laboratory biomarker thresholds with source page numbers.

### 2. Patient Electronic Health Records (Input)
- Formats: Structured JSON records, FHIR-compliant payloads, or raw unstructured clinical consultation notes.
- Data Extracted: Demographics (age, sex), primary diagnosis, comorbidities, ECOG functional status, prior antineoplastic systemic regimens, completion dates, and laboratory biomarker panels (eGFR, ANC, Platelets, Hemoglobin, Total Bilirubin, ALT, AST, HbA1c).
- Privacy Handling: All raw PII/PHI is scrubbed at ingestion using Microsoft Presidio and clinical regex. Downstream inference agents see only pseudonymized subject IDs (e.g., `SUBJ-FEDCC663`).

### 3. Medical Ontologies & Controlled Vocabularies (Reference)
- **ICD-10-CM**: Standardized diagnostic codes for study indication validation (e.g., `C34.90` for NSCLC) and exclusionary comorbidity detection (e.g., `K50.90` Crohn's/colitis, `I50.9` heart failure, `N18.4` severe renal disease).
- **SNOMED-CT**: Clinical concept definitions and findings for identifying active contraindications and procedures (e.g., `424144002` active autoimmune disease, `723188008` brain metastases).
- **LOINC**: Standardized laboratory observation identifiers, reference ranges, and unit normalization (e.g., `33914-3` for eGFR in mL/min/1.73m2, `777-3` for platelet count, `26499-4` for ANC).

---

## 3. Limitations & Safety Boundaries

ClinSafe Agent is designed with explicit boundaries to prevent autonomous overreach in regulated clinical environments:

### 1. Scope of Local Ontology Tables
- The current implementation utilizes high-coverage, curated local subsets of ICD-10, SNOMED, and LOINC codes for targeted oncology/cardiorenal trials. It does not replace a multi-million-concept enterprise UMLS server. Rare comorbidities outside the curated tables are flagged for human review.

### 2. Requirement for Human Signoff
- ClinSafe Agent is a **clinical decision support (CDS) system**, not an autonomous physician. It produces an auditable recommendation. The final enrollment decision and electronic signature in the FDA audit dossier must be validated by a licensed Clinical Research Coordinator or Principal Investigator.

### 3. Missing Data vs Negation
- In unstructured narrative notes, lack of mention of a condition is not assumed to mean absence unless explicit clinical negation is detected ("no history of", "negative for", "denies"). When critical lab tests are omitted from a panel, the agent marks them `UNKNOWN` and reduces confidence, rather than interpolating or imputing values.

### 4. Non-Standard Lab Units
- When laboratories report values in non-standard units (e.g., $\mu\text{mol/L}$ instead of $\text{mg/dL}$ for bilirubin), the medical safety agent flags a unit discrepancy for verification rather than silently applying conversion factors that could alter borderline determinations.
