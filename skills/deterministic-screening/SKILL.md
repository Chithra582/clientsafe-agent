---
name: deterministic-screening
description: Deterministically evaluate patient values against protocol criteria using pure code logic.
---

# Deterministic Screening Skill

## Overview
Evaluates structured, de-identified patient records against protocol inclusion/exclusion criteria rules strictly using deterministic Python code. Eliminates LLM numerical and threshold hallucinations.

## Operations
1. Resolves patient observed values for each required criterion field.
2. Applies deterministic comparison predicates (`obs >= target`, `obs <= target`, `obs == target`).
3. Handles missing/unrecorded lab biomarkers by assigning status `UNKNOWN` (preventing hallucinated guesses).
4. Generates traceable per-criterion pass/fail reasoning.
5. Produces screening outcome: `ELIGIBLE`, `INELIGIBLE`, or `REQUIRES_HUMAN_OVERVIEW`.
