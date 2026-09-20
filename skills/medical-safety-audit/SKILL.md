---
name: medical-safety-audit
description: Cross-check comorbidities and medications against SNOMED-CT, ICD-10-CM, and LOINC ontologies.
---

# Medical Safety Audit Skill

## Overview
Cross-references patient diagnoses, comorbidities, prior therapies, and biomarker reference ranges against medical ontologies to catch clinical contraindications and safety ambiguities.

## Operations
1. Cross-checks ICD-10 codes against exclusionary diagnoses table (e.g. `K50.90` Crohn's/colitis, `I50.9` heart failure, `N18.4` severe renal disease).
2. Validates primary and secondary SNOMED-CT concept IDs for active disease flags.
3. Normalizes LOINC lab biomarker codes and verifies standard reference units.
4. Detects borderline safety boundaries (eGFR within $\pm 3$ units of threshold, or prior therapy washout within 3 days of cutoff).
5. Outputs `safety_decision`: `SAFE`, `CONTRAINDICATION_FLAGGED`, or `AMBIGUOUS_SAFETY_RISK`.
