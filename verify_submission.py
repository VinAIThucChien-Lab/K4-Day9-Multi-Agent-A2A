"""Comprehensive verification script to validate all README.md requirements."""

import os
import json
import zipfile

VALID_PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim"
}

VALID_CASE_STATUSES = {"action_required", "no_action"}
VALID_EVIDENCE_PREFIXES = ("order:", "item:", "payment:", "seller:", "policy:")


def verify_submission():
    print("==================================================")
    print("VERIFYING SUBMISSION ACCORDING TO README.MD")
    print("==================================================")

    # 1. Verify output.zip
    zip_path = "output.zip"
    assert os.path.exists(zip_path), "output.zip does not exist!"
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        expected_names = [f"output/EC_{i:03d}.json" for i in range(1, 51)]
        print(f"[Check Zip] Total entries in output.zip: {len(namelist)}")
        assert namelist == expected_names, (
            "ZIP must contain exactly output/EC_001.json..output/EC_050.json "
            "in order, with no extra entries"
        )
        assert zf.testzip() is None, "ZIP integrity check failed"
        for name in expected_names:
            json.loads(zf.read(name))
        print("--> output.zip content check PASSED (contains exactly output/EC_001.json - output/EC_050.json).")

    # 2. Verify Output Schemas & Array Limits for 50 JSONs
    output_dir = "output"
    for i in range(1, 51):
        filename = f"EC_{i:03d}.json"
        filepath = os.path.join(output_dir, filename)
        assert os.path.exists(filepath), f"File missing: {filepath}"

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("case_id") == f"EC_{i:03d}"
        
        assessment = data.get("case_assessment", {})
        assert assessment.get("primary_issue") in VALID_PRIMARY_ISSUES, f"Invalid primary_issue in {filename}"
        assert assessment.get("case_status") in VALID_CASE_STATUSES, f"Invalid case_status in {filename}"
        assert 0.0 <= assessment.get("confidence", -1) <= 1.0, f"Invalid confidence in {filename}"

        entities = data.get("affected_entities", {})
        assert len(entities.get("order_ids", [])) <= 5, f"order_ids limit exceeded in {filename}"
        assert len(entities.get("item_ids", [])) <= 5, f"item_ids limit exceeded in {filename}"
        assert len(entities.get("seller_ids", [])) <= 3, f"seller_ids limit exceeded in {filename}"
        assert len(entities.get("payment_ids", [])) <= 5, f"payment_ids limit exceeded in {filename}"

        cust = data.get("customer_context", {})
        assert len(cust.get("related_order_ids", [])) <= 5, f"related_order_ids limit exceeded in {filename}"

        prod = data.get("product_context", {})
        assert len(prod.get("product_ids", [])) <= 5, f"product_ids limit exceeded in {filename}"
        assert len(prod.get("category_names", [])) <= 5, f"category_names limit exceeded in {filename}"

        rca = data.get("root_cause_analysis", {})
        assert len(rca.get("ranked_causes", [])) <= 3, f"ranked_causes limit exceeded in {filename}"
        assert len(rca.get("responsible_parties", [])) <= 3, f"responsible_parties limit exceeded in {filename}"

        evidence = data.get("evidence_ids", [])
        assert len(evidence) <= 20, f"evidence_ids limit exceeded in {filename}"
        for evi in evidence:
            assert evi.startswith(VALID_EVIDENCE_PREFIXES), f"Invalid evidence ID format in {filename}: {evi}"

        actions = data.get("resolution_actions", [])
        assert len(actions) <= 5, f"resolution_actions limit exceeded in {filename}"

    print("--> 50 Output JSON files schema & array limits check PASSED.")

    # 3. Verify Required Audit Artifacts in Repo Root (README Section 8)
    artifacts = [
        "architecture.md",
        "individual_5SoCuoiMHV_HoVaTen.md",
        "trace.jsonl",
        "metadata.json"
    ]
    for art in artifacts:
        assert os.path.exists(art), f"Required audit artifact missing: {art}"
        assert os.path.getsize(art) > 0, f"Audit artifact is empty: {art}"
        print(f"--> [Artifact Check] {art} verified (exists & non-empty).")

    with open("trace.jsonl", "r", encoding="utf-8") as f:
        trace_lines = f.readlines()
    assert len(trace_lines) == 50, f"Expected 50 trace lines in trace.jsonl, found {len(trace_lines)}"
    trace_rows = [json.loads(line) for line in trace_lines]
    expected_case_ids = [f"EC_{i:03d}" for i in range(1, 51)]
    assert [row.get("case_id") for row in trace_rows] == expected_case_ids, (
        "trace.jsonl must contain exactly one ordered entry for every case"
    )
    print("--> trace.jsonl contains 50 execution trace entries.")

    print("\n==================================================")
    print("ALL SUBMISSION REQUIREMENTS PASSED 100%!")
    print("==================================================")


if __name__ == "__main__":
    verify_submission()
