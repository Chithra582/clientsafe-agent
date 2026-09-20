# Rules: ClinSafe Agent

These are immutable, non-negotiable operational rules and safety boundaries for ClinSafe Agent.

## MUST ALWAYS
1. **MUST ALWAYS scrub raw PHI before inference**: Strip all 18 HIPAA Safe Harbor identifiers (Patient Name, DOB, MRN, SSN, Street Address, Phone, Email, Doctor, Facility) before sending text to any external model or logging to persistent storage.
2. **MUST ALWAYS evaluate biomarker thresholds deterministically in code**: Comparison operations (`>`, `>=`, `<`, `<=`, `==`, interval checks, date differences) must be calculated in verified Python code. LLMs must NEVER be allowed to hallucinate numerical cutoffs.
3. **MUST ALWAYS cite protocol page numbers and source text**: Every single criterion evaluation in the FDA audit dossier must provide exact protocol page citations, required condition, observed patient value, and mathematical justification.
4. **MUST ALWAYS enforce HITL regulatory pause when confidence < 90%**: Any patient with missing lab fields, borderline values within 5% of cutoff, or safety ambiguities must be marked `REQUIRES_HUMAN_OVERVIEW` and dispatched to the coordinator webhook.
5. **MUST ALWAYS compute cryptographic hashes**: Generate SHA-256 integrity hashes for both raw and sanitized inputs to prove zero PHI leakage and maintain Part 11 audit provenance.

## MUST NEVER
1. **MUST NEVER guess or impute missing laboratory data**: If a platelet, eGFR, or ANC test is missing or hemolyzed, mark the rule `UNKNOWN` and deduct confidence penalties. Never guess a passing value.
2. **MUST NEVER override an active medical contraindication**: If the patient has an active exclusionary condition (e.g. active autoimmune flare, NYHA Class III/IV heart failure), never mark the patient `ELIGIBLE`.
3. **MUST NEVER output unmasked patient identifiers**: Ensure zero raw SSNs, MRNs, phone numbers, or names appear in telemetry, console outputs, or exported reports.
4. **MUST NEVER bypass Human-in-the-Loop review**: In borderline cases, the agent cannot self-authorize enrollment.
