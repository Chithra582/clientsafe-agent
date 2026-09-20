---
name: fda-dossier-generation
description: Compile FDA 21 CFR Part 11 compliant audit dossiers in PDF and JSON formats.
---

# FDA Dossier Generation Skill

## Overview
Assembles an immutable, cited, electronically signed regulatory audit package satisfying FDA 21 CFR Part 11 and HIPAA Safe Harbor requirements.

## Operations
1. Assembles subject provenance with pseudonymized subject ID and PHI redaction count.
2. Formats per-criterion traceability matrix: rule ID, source page citation, required threshold, observed patient value, and deterministic reasoning.
3. Incorporates medical ontology findings and multi-agent confidence score.
4. Generates publication-quality PDF audit dossier via ReportLab with running headers, metadata tables, and electronic signature block.
5. Emits machine-readable JSON dossier for regulatory system ingestion.
