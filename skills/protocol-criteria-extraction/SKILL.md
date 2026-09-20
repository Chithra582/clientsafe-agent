---
name: protocol-criteria-extraction
description: Extract structured inclusion and exclusion rules from clinical trial protocol PDFs.
---

# Protocol Criteria Extraction Skill

## Overview
Parses multi-page clinical trial protocol documents (PDF or text) and extracts inclusion and exclusion criteria into structured JSON condition rules.

## Operations
1. Ingests PDF bytes via `pdfplumber` / `pypdf` with page-by-page text extraction.
2. Identifies Section 4.1 (Inclusion Criteria) and Section 4.2 (Exclusion Criteria).
3. Normalizes each rule into a strict schema:
   - `criterion_id`: e.g. `INC-1`, `EXC-2`
   - `category`: `biomarker`, `demographic`, `condition`, `medication_washout`, `functional_status`
   - `field`: normalized clinical target (e.g. `eGFR`, `ANC`, `Platelets`, `ecog`, `washout_days`)
   - `op`: comparison operator (`>=`, `<=`, `>`, `<`, `==`)
   - `value`: numeric cutoff or condition state
   - `unit`: standard measurement unit
   - `source_page`: integer protocol page citation
   - `original_text`: exact verbatim snippet from protocol
