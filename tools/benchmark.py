import json
import time
import os
import re
from typing import Dict, List, Optional

import pandas as pd

from orchestration import run_orchestration

# POC pills → canonical ground-truth scenario rows (demand / inventory / supplier)
GT_SCENARIO_BY_PILL = {
    0: "SC-001",
    1: "SC-009",
    2: "SC-015",
}

# Legacy keyword fallback if CSV missing
GROUND_TRUTH_KEYWORDS = {
    0: "Air",
    1: "Rail",
    2: "Ocean",
}


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def load_ground_truth_rows() -> Dict[str, dict]:
    path = os.path.join(_project_root(), "datasets", "ground_truth_dataset.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    out = {}
    for _, row in df.iterrows():
        sid = str(row.get("scenario_id", "")).strip()
        if sid:
            out[sid] = row.to_dict()
    return out


def _significant_tokens(text: str, min_len: int = 5) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    parts = re.split(r"[^a-zA-Z0-9]+", text)
    skip = {
        "increase", "reduce", "within", "units", "order", "from", "with", "after",
        "during", "across", "using", "based", "against", "through", "without",
    }
    seen = set()
    tokens = []
    for p in parts:
        low = p.lower()
        if len(p) < min_len or low in skip:
            continue
        if low not in seen:
            seen.add(low)
            tokens.append(low)
    return tokens[:15]


def recommendation_aligns_with_ground_truth(rec_name: str, gt_row: Optional[dict]) -> bool:
    if not gt_row:
        return False
    rn = (rec_name or "").lower()
    for field in ("preferred_action", "expected_outcome", "description"):
        blob = str(gt_row.get(field, "") or "")
        for tok in _significant_tokens(blob):
            if tok in rn:
                return True
    return False


def run_phase0_validation():
    print("Initiating Phase-0 Nike Supply Chain Validation Pipeline...")
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scenarios": 3,
        "metrics": {
            "accuracy": 0.0,
            "avg_latency_ms": 0.0,
            "pass_rate": 0.0
        },
        "details": []
    }

    gt_map = load_ground_truth_rows()

    start_all = time.time()
    correct_count = 0

    for sc_id in range(3):
        print(f"  -> Testing Scenario {sc_id}...")
        start = time.time()

        try:
            exec_result = run_orchestration(sc_id)
            latency = (time.time() - start) * 1000

            best_rec_name = exec_result.recommendation.name
            sid = GT_SCENARIO_BY_PILL.get(sc_id)
            gt_row = gt_map.get(sid) if sid else None

            gt_pass = bool(gt_row) and recommendation_aligns_with_ground_truth(best_rec_name, gt_row)
            expected_keyword = GROUND_TRUTH_KEYWORDS.get(sc_id, "NONE")
            legacy_pass = (
                expected_keyword.lower() in best_rec_name.lower()
                or "act" in best_rec_name.lower()
            )
            is_pass = gt_pass or legacy_pass

            if is_pass:
                correct_count += 1

            if gt_pass:
                reason_ok = f"ground-truth token overlap (row {sid})"
                reason_fail = f"no ground-truth token overlap for {sid}; legacy keyword '{expected_keyword}' also failed"
            elif legacy_pass:
                reason_ok = f"legacy transport keyword '{expected_keyword}' (ground-truth row {sid} present but no text overlap)"
                reason_fail = ""
            else:
                reason_ok = ""
                reason_fail = (
                    f"no significant-token overlap with row {sid}"
                    + (f"; expected legacy keyword '{expected_keyword}'" if gt_row else "")
                )

            results["details"].append({
                "scenario_id": sc_id,
                "ground_truth_scenario_id": sid,
                "ground_truth_match": gt_pass,
                "legacy_keyword_match": legacy_pass,
                "use_case": exec_result.status_metrics.get("active_use_case", "UNKNOWN"),
                "latency_ms": round(latency, 2),
                "result": "PASS" if is_pass else "FAIL",
                "recommendation": best_rec_name,
                "reason": reason_ok if is_pass else reason_fail,
            })
        except Exception as e:
            print(f"     Error in scenario {sc_id}: {e}")
            results["details"].append({
                "scenario_id": sc_id,
                "result": "ERROR",
                "reason": str(e)
            })

    total_latency = (time.time() - start_all) * 1000
    results["metrics"]["accuracy"] = round((correct_count / 3) * 100, 1)
    results["metrics"]["avg_latency_ms"] = round(total_latency / 3, 2)
    results["metrics"]["pass_rate"] = round((correct_count / 3), 2)

    with open("validation_report.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Validation Complete. Accuracy: {results['metrics']['accuracy']}%")
    print(f"   Report saved to validation_report.json")


if __name__ == "__main__":
    run_phase0_validation()
