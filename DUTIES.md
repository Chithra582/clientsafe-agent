# Segregation of Duties (SOD): ClinSafe Agent

Under FDA 21 CFR Part 11 and Good Clinical Practice (GCP) guidelines, no single autonomous process or agent may execute a clinical trial enrollment pipeline without separation of roles and independent verification.

## Role Definitions & Boundaries

```
[Ingestion Agent]       --> Role: Ingestion & Extraction (Maker)
        │
[PHI Scrubbing Agent]   --> Role: Privacy Gatekeeper (Validator)
        │
[Screening Agent]       --> Role: Deterministic Rule Evaluator (Executor)
        │
[Medical Safety Agent]  --> Role: Ontology Contraindication Checker (Inspector)
        │
[Confidence Scorer]     --> Role: Governance & HITL Threshold Arbiter (Governor)
        │
[Audit Agent]           --> Role: Regulatory Dossier & Provenance Recorder (Auditor)
```

### 1. Ingestion Agent (`maker`)
- **Responsibilities**: Ingests protocol PDFs and EHR patient documents into a sandboxed environment.
- **Permissions**: Read raw input files, extract text streams.
- **Restrictions**: Cannot evaluate criteria, cannot execute clinical decisions.

### 2. PHI Scrubbing Agent (`gatekeeper`)
- **Responsibilities**: Strips all 18 HIPAA identifiers using Microsoft Presidio and clinical regex; generates SHA-256 diff logs.
- **Permissions**: Redact PII/PHI, assign pseudonymized identifiers (`SUBJ-XXXX`).
- **Restrictions**: Must execute BEFORE any downstream agent or LLM call. Cannot modify clinical values (labs, diagnoses, dates of therapy).

### 3. Screening Agent (`executor`)
- **Responsibilities**: Evaluates patient values against protocol inclusion/exclusion criteria strictly via deterministic code.
- **Permissions**: Evaluate mathematical comparisons, mark status (`PASS`, `FAIL`, `UNKNOWN`).
- **Restrictions**: Cannot perform free-form generative LLM judgment on numbers.

### 4. Medical Safety Agent (`inspector`)
- **Responsibilities**: Independent cross-check against SNOMED-CT, ICD-10-CM, and LOINC lookup tables.
- **Permissions**: Flag contraindications, check reference ranges, detect ambiguities.
- **Restrictions**: Independent from Screening Agent. Cannot alter criteria rules.

### 5. Confidence Scorer (`governor`)
- **Responsibilities**: Evaluates multi-agent convergence, computes confidence deductions, and enforces HITL gating (< 90%).
- **Permissions**: Determine governed status, fire external webhooks.
- **Restrictions**: Cannot force enrollment when safety inspector flags contraindications.

### 6. Audit Agent (`auditor`)
- **Responsibilities**: Assembles immutable FDA 21 CFR Part 11 dossiers with digital signatures and protocol citations.
- **Permissions**: Compile PDF/JSON audit packages, sign electronic audit trails.
- **Restrictions**: Read-only access to prior agent results; cannot alter screening evaluations.
