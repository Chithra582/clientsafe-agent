---
name: phi-scrubbing
description: Redact all 18 HIPAA Safe Harbor identifiers from patient records before inference.
---

# PHI Scrubbing Skill

## Overview
This skill executes automated redaction of Protected Health Information (PHI) and Personally Identifiable Information (PII) from clinical trial patient records (JSON, structured fields, or raw clinical progress notes).

## Inputs
- `patient_text` or `patient_json`: Raw patient document with potentially identifying information.

## Operations
1. Scans text with Microsoft Presidio NER and high-precision clinical regex recognizers.
2. Identifies: Patient Names, Medical Record Numbers (MRN), Social Security Numbers (SSN), Dates of Birth (DOB), Phone Numbers, Email Addresses, Street Addresses, Physician Names, and Healthcare Institutions.
3. Replaces each with standardized redacted tokens (e.g. `[PATIENT_NAME_REDACTED]`, `[MRN_REDACTED]`, `[SSN_REDACTED]`).
4. Generates a subject pseudonym (`SUBJ-XXXX`) and an immutable before/after diff table with SHA-256 provenance hashes.
5. Performs post-redaction scan to certify zero raw PHI leakage.
