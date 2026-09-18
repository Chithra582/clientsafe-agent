"""Medical Safety Agent.

Cross-checks patient conditions, comorbidities, and laboratory biomarkers
against local subsets of medical ontologies:
- ICD-10-CM (contraindications & exclusionary comorbidities)
- SNOMED-CT (clinical findings & disease concepts)
- LOINC (laboratory observation identifiers & standard units)
"""

import os
import csv
from typing import Dict, Any, List, Optional


class MedicalSafetyAgent:
    """Validates patient clinical safety against clinical ontologies."""

    def __init__(self, ontologies_dir: Optional[str] = None):
        self.ontologies_dir = ontologies_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ontologies"
        )
        self.icd10_table: Dict[str, Dict[str, str]] = {}
        self.snomed_table: Dict[str, Dict[str, str]] = {}
        self.loinc_table: Dict[str, Dict[str, str]] = {}
        self._load_ontologies()

    def _load_ontologies(self):
        """Loads CSV tables into memory for rapid deterministic cross-checks."""
        icd_path = os.path.join(self.ontologies_dir, "icd10_contraindications.csv")
        if os.path.exists(icd_path):
            with open(icd_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.icd10_table[row["code"].strip()] = row

        snomed_path = os.path.join(self.ontologies_dir, "snomed_terms.csv")
        if os.path.exists(snomed_path):
            with open(snomed_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.snomed_table[row["concept_id"].strip()] = row

        loinc_path = os.path.join(self.ontologies_dir, "loinc_biomarkers.csv")
        if os.path.exists(loinc_path):
            with open(loinc_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.loinc_table[row["loinc_num"].strip()] = row

    def perform_safety_audit(self, patient_record: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a comprehensive medical ontology safety cross-check."""
        flagged_contraindications = []
        ambiguous_terms = []
        validated_ontologies = []

        profile = patient_record.get("clinical_profile", {})
        labs = profile.get("lab_biomarkers", {})

        # 1. Cross-check ICD-10 codes
        icd_code = profile.get("icd10_code")
        if icd_code and icd_code in self.icd10_table:
            entry = self.icd10_table[icd_code]
            validated_ontologies.append({
                "ontology": "ICD-10-CM",
                "code": icd_code,
                "description": entry.get("description"),
                "risk_level": entry.get("risk_level"),
                "status": "VALIDATED"
            })

        # Check secondary conditions / autoimmune conditions for ICD-10
        autoimmune_list = profile.get("autoimmune_conditions", [])
        for item in autoimmune_list:
            cond_icd = item.get("icd10")
            cond_snomed = item.get("snomed")
            cond_name = item.get("condition", "Autoimmune condition")

            if cond_icd and cond_icd in self.icd10_table:
                entry = self.icd10_table[cond_icd]
                if entry.get("risk_level") in ["high", "critical"]:
                    flagged_contraindications.append({
                        "ontology": "ICD-10-CM",
                        "code": cond_icd,
                        "description": entry.get("description"),
                        "risk_level": entry.get("risk_level"),
                        "finding": f"High risk contraindication: {cond_name}",
                        "action_required": entry.get("action_required")
                    })
            if cond_snomed and cond_snomed in self.snomed_table:
                entry = self.snomed_table[cond_snomed]
                if str(entry.get("contraindication_flag")) == "1":
                    flagged_contraindications.append({
                        "ontology": "SNOMED-CT",
                        "code": cond_snomed,
                        "description": entry.get("term"),
                        "risk_level": "high",
                        "finding": f"SNOMED exclusionary concept: {entry.get('notes')}",
                        "action_required": "exclude_patient"
                    })

        # 2. Cross-check Primary SNOMED
        snomed_id = profile.get("snomed_concept_id")
        if snomed_id and snomed_id in self.snomed_table:
            entry = self.snomed_table[snomed_id]
            validated_ontologies.append({
                "ontology": "SNOMED-CT",
                "code": snomed_id,
                "description": entry.get("term"),
                "status": "VALIDATED_TARGET_INDICATION"
            })

        # 3. Cross-check LOINC Biomarkers and Units
        for lab_name, lab_info in labs.items():
            if isinstance(lab_info, dict):
                loinc_code = lab_info.get("loinc")
                lab_val = lab_info.get("value")
                lab_unit = lab_info.get("unit")

                if loinc_code and loinc_code in self.loinc_table:
                    loinc_meta = self.loinc_table[loinc_code]
                    std_unit = loinc_meta.get("standard_unit")
                    validated_ontologies.append({
                        "ontology": "LOINC",
                        "code": loinc_code,
                        "component": loinc_meta.get("component"),
                        "standard_unit": std_unit,
                        "observed_unit": lab_unit,
                        "clinical_significance": loinc_meta.get("clinical_significance")
                    })

                    # Borderline ambiguity check (e.g. eGFR within 3 units of cutoff 50)
                    if loinc_meta.get("component") == "eGFR" and lab_val is not None:
                        if 48.0 <= float(lab_val) <= 53.0:
                            ambiguous_terms.append({
                                "field": "eGFR",
                                "code": loinc_code,
                                "observed_value": lab_val,
                                "issue": f"eGFR {lab_val} mL/min is within tight ±3 mL/min boundary of protocol cutoff (50 mL/min). Requires nephrology review."
                            })

        # 4. Check prior therapy washout ambiguities
        therapies = profile.get("prior_systemic_therapies", [])
        for t in therapies:
            days = t.get("days_since_completion")
            if days is not None and 20 <= days < 28:
                ambiguous_terms.append({
                    "field": "washout_window",
                    "observed_value": f"{days} days",
                    "issue": f"Prior regimen '{t.get('regimen')}' completed {days} days ago. Marginally short of 28-day window."
                })

        # Safety decision determination
        if len(flagged_contraindications) > 0:
            safety_decision = "CONTRAINDICATION_FLAGGED"
            safety_score = 0.40
        elif len(ambiguous_terms) > 0:
            safety_decision = "AMBIGUOUS_SAFETY_RISK"
            safety_score = 0.75
        else:
            safety_decision = "SAFE"
            safety_score = 1.0

        return {
            "safety_decision": safety_decision,
            "safety_score": safety_score,
            "contraindications_count": len(flagged_contraindications),
            "ambiguous_count": len(ambiguous_terms),
            "flagged_contraindications": flagged_contraindications,
            "ambiguous_safety_risks": ambiguous_terms,
            "validated_ontologies": validated_ontologies
        }
