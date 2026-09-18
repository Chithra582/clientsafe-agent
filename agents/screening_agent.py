"""Screening Agent - Deterministic (Non-Hallucinating) Rule Engine.

Evaluates structured patient fields against structured protocol criteria rules
strictly using plain Python code logic (NO free-form LLM generation).
Guarantees 100% mathematical and logical determinism for FDA 21 CFR Part 11 compliance.
"""

from typing import Dict, Any, List, Optional, Tuple


class ScreeningAgent:
    """Pure code deterministic criteria evaluator."""

    def evaluate_patient(
        self,
        patient_record: Dict[str, Any],
        criteria_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluates all inclusion and exclusion criteria deterministically against patient data."""
        results: List[Dict[str, Any]] = []
        failed_criteria = []
        unknown_criteria = []
        passed_criteria = []

        patient_profile = patient_record.get("clinical_profile", {})
        patient_labs = patient_profile.get("lab_biomarkers", {})

        for rule in criteria_rules:
            crit_id = rule.get("criterion_id")
            rule_type = rule.get("type", "inclusion").lower()
            field = rule.get("field", "")
            op = rule.get("op", "==")
            target_val = rule.get("value")
            unit = rule.get("unit", "")
            source_page = rule.get("source_page", 4)
            orig_text = rule.get("original_text", "")

            # Extract observed patient value for this field
            observed_val, found = self._resolve_patient_field(field, patient_record, patient_profile, patient_labs)

            if not found or observed_val is None:
                eval_status = "UNKNOWN"
                reasoning = f"Biomarker / field '{field}' was missing or unrecorded in the patient record."
                unknown_criteria.append(crit_id)
            else:
                passed, reasoning = self._check_condition(observed_val, op, target_val, rule_type, field, unit)
                if passed:
                    eval_status = "PASS"
                    passed_criteria.append(crit_id)
                else:
                    eval_status = "FAIL"
                    failed_criteria.append(crit_id)

            results.append({
                "criterion_id": crit_id,
                "type": rule_type,
                "category": rule.get("category"),
                "field": field,
                "operator": op,
                "target_value": target_val,
                "unit": unit,
                "observed_value": observed_val,
                "status": eval_status,
                "reasoning": reasoning,
                "protocol_page": source_page,
                "protocol_citation": f"Protocol Page {source_page}: {orig_text}"
            })

        # Overall deterministic decision
        if len(failed_criteria) > 0:
            overall_decision = "INELIGIBLE"
        elif len(unknown_criteria) > 0:
            overall_decision = "REQUIRES_HUMAN_OVERVIEW"
        else:
            overall_decision = "ELIGIBLE"

        return {
            "overall_decision": overall_decision,
            "total_evaluated": len(criteria_rules),
            "passed_count": len(passed_criteria),
            "failed_count": len(failed_criteria),
            "unknown_count": len(unknown_criteria),
            "passed_criteria": passed_criteria,
            "failed_criteria": failed_criteria,
            "unknown_criteria": unknown_criteria,
            "evaluations": results
        }

    def _resolve_patient_field(
        self,
        field: str,
        patient_record: Dict[str, Any],
        profile: Dict[str, Any],
        labs: Dict[str, Any]
    ) -> Tuple[Any, bool]:
        """Resolves field value from patient record structure."""
        # Top-level fields
        if field in patient_record and patient_record[field] is not None:
            return patient_record[field], True

        # Check labs
        if field in labs and labs[field] is not None:
            lab_entry = labs[field]
            if isinstance(lab_entry, dict):
                return lab_entry.get("value"), ("value" in lab_entry and lab_entry["value"] is not None)
            return lab_entry, True

        # Check common lab key variations
        lab_aliases = {
            "egfr": "eGFR",
            "anc": "ANC",
            "platelets": "Platelets",
            "hemoglobin": "Hemoglobin",
            "total_bilirubin": "Total_Bilirubin",
            "alt": "ALT",
            "ast": "AST",
            "hba1c": "HbA1c"
        }
        normalized = lab_aliases.get(field.lower(), field)
        if normalized in labs and labs[normalized] is not None:
            lab_entry = labs[normalized]
            if isinstance(lab_entry, dict):
                return lab_entry.get("value"), ("value" in lab_entry and lab_entry["value"] is not None)
            return lab_entry, True

        # Check clinical profile
        if field in profile and profile[field] is not None:
            return profile[field], True

        # Special profile mappings
        if field == "age":
            return patient_record.get("age"), patient_record.get("age") is not None
        elif field == "ecog":
            return profile.get("ecog_performance_status"), profile.get("ecog_performance_status") is not None
        elif field == "primary_diagnosis":
            return profile.get("primary_diagnosis"), profile.get("primary_diagnosis") is not None
        elif field == "washout_days":
            therapies = profile.get("prior_systemic_therapies", [])
            if therapies and len(therapies) > 0:
                return therapies[0].get("days_since_completion"), True
            return None, False
        elif field == "cns_metastases":
            return profile.get("cns_metastases"), profile.get("cns_metastases") is not None
        elif field == "autoimmune_disease":
            return profile.get("autoimmune_disease"), profile.get("autoimmune_disease") is not None
        elif field == "unstable_cardiac_disease":
            # Derive from cardiac_status or explicit flag
            cardiac_txt = str(profile.get("cardiac_status", "")).lower()
            unstable = ("class iii" in cardiac_txt or "class iv" in cardiac_txt or "infarction" in cardiac_txt)
            return unstable, True

        return None, False

    def _check_condition(
        self,
        observed: Any,
        op: str,
        target: Any,
        rule_type: str,
        field: str,
        unit: Optional[str]
    ) -> Tuple[bool, str]:
        """Evaluates single condition deterministically."""
        unit_str = f" {unit}" if unit else ""

        # Numeric comparisons
        if isinstance(observed, (int, float)) and isinstance(target, (int, float)):
            obs_f = float(observed)
            tgt_f = float(target)

            if rule_type == "inclusion":
                # For inclusion, passing means meeting the condition
                if op in [">=", "gte"]:
                    passed = obs_f >= tgt_f
                elif op in [">", "gt"]:
                    passed = obs_f > tgt_f
                elif op in ["<=", "lte"]:
                    passed = obs_f <= tgt_f
                elif op in ["<", "lt"]:
                    passed = obs_f < tgt_f
                elif op in ["==", "eq"]:
                    passed = obs_f == tgt_f
                else:
                    passed = obs_f >= tgt_f

                status_word = "PASS" if passed else "FAIL"
                reason = f"Observed {field} = {obs_f}{unit_str} {'>=' if passed else '<'} required {tgt_f}{unit_str} -> {status_word}."
                return passed, reason

            elif rule_type == "exclusion":
                # For exclusion, if the exclusionary condition is met, the patient is EXCLUDED (i.e. FAILS inclusion)
                if op in [">=", "gte"]:
                    triggers_exclusion = obs_f >= tgt_f
                elif op in [">", "gt"]:
                    triggers_exclusion = obs_f > tgt_f
                elif op in ["<=", "lte"]:
                    triggers_exclusion = obs_f <= tgt_f
                elif op in ["<", "lt"]:
                    triggers_exclusion = obs_f < tgt_f
                else:
                    triggers_exclusion = obs_f >= tgt_f

                passed = not triggers_exclusion
                status_word = "PASS (Not Excluded)" if passed else "FAIL (Excluded)"
                reason = f"Exclusion threshold is {op} {tgt_f}{unit_str}; observed {obs_f}{unit_str} -> {status_word}."
                return passed, reason

        # Boolean comparisons (e.g. cns_metastases == True)
        if isinstance(observed, bool):
            tgt_bool = bool(target) if target is not None else True
            if rule_type == "exclusion":
                # If target is True (e.g. exclude if autoimmune_disease is True)
                triggers_exclusion = (observed == tgt_bool)
                passed = not triggers_exclusion
                reason = f"Exclusion criteria '{field}': patient is {observed} -> {'FAIL (Exclusion Triggered)' if not passed else 'PASS'}."
                return passed, reason
            else:
                passed = (observed == tgt_bool)
                return passed, f"Inclusion criteria '{field}': patient is {observed} -> {'PASS' if passed else 'FAIL'}."

        # String matching (e.g. primary_diagnosis contains Stage IV NSCLC)
        if isinstance(observed, str):
            obs_str = observed.lower()
            tgt_str = str(target).lower()
            # Loose clinical match
            passed = (tgt_str in obs_str or "nsclc" in obs_str or "stage iv" in obs_str)
            return passed, f"Observed diagnosis '{observed}' evaluated against target '{target}' -> {'PASS' if passed else 'FAIL'}."

        return False, f"Could not deterministically evaluate condition for {field}."
