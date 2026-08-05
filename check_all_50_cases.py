"""Detailed verification script for all 50 cases against README.md specifications."""

import os
import json
import glob

VALID_PRIMARY = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim"
}

VALID_STATUS = {"action_required", "no_action"}
VALID_RESP_TYPES = {"platform", "seller", "logistics_provider"}


def check_all_cases():
    json_files = sorted(glob.glob("output/*.json"))
    print(f"Checking {len(json_files)} output JSON files in output/...")
    assert len(json_files) == 50, f"Expected 50 output files, found {len(json_files)}"

    issues_count = {}
    errors = []

    for filepath in json_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        case_id = data.get("case_id")
        if not case_id:
            errors.append(f"{filename}: missing case_id")
            continue

        # Case Assessment
        ca = data.get("case_assessment", {})
        primary = ca.get("primary_issue")
        if primary not in VALID_PRIMARY:
            errors.append(f"{filename}: invalid primary_issue '{primary}'")
        issues_count[primary] = issues_count.get(primary, 0) + 1

        status = ca.get("case_status")
        if status not in VALID_STATUS:
            errors.append(f"{filename}: invalid case_status '{status}'")

        conf = ca.get("confidence")
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
            errors.append(f"{filename}: invalid confidence '{conf}'")

        # Affected Entities
        ae = data.get("affected_entities", {})
        if len(ae.get("order_ids", [])) > 5:
            errors.append(f"{filename}: order_ids > 5")
        if len(ae.get("item_ids", [])) > 5:
            errors.append(f"{filename}: item_ids > 5")
        if len(ae.get("seller_ids", [])) > 3:
            errors.append(f"{filename}: seller_ids > 3")
        if len(ae.get("payment_ids", [])) > 5:
            errors.append(f"{filename}: payment_ids > 5")

        # Customer & Product Context
        cc = data.get("customer_context", {})
        if len(cc.get("related_order_ids", [])) > 5:
            errors.append(f"{filename}: related_order_ids > 5")

        pc = data.get("product_context", {})
        if len(pc.get("product_ids", [])) > 5:
            errors.append(f"{filename}: product_ids > 5")
        if len(pc.get("category_names", [])) > 5:
            errors.append(f"{filename}: category_names > 5")

        # Delivery & Payment Reconciliation
        pr = data.get("payment_reconciliation", {})
        if pr.get("currency") != "BRL":
            errors.append(f"{filename}: payment_reconciliation currency != BRL")

        fr = data.get("financial_resolution", {})
        if fr.get("currency") != "BRL":
            errors.append(f"{filename}: financial_resolution currency != BRL")
        refund = fr.get("recommended_refund_brl")
        if not isinstance(refund, (int, float)):
            errors.append(f"{filename}: invalid recommended_refund_brl '{refund}'")

        # Check status alignment: action_required if refund > 0 else no_action
        if refund > 0 and status != "action_required":
            errors.append(f"{filename}: refund {refund} > 0 but status is {status}")
        if refund == 0 and status != "no_action":
            errors.append(f"{filename}: refund is 0 but status is {status}")

        # Root Cause Analysis
        rca = data.get("root_cause_analysis", {})
        for p in rca.get("responsible_parties", []):
            ptype = p.get("party_type")
            if ptype not in VALID_RESP_TYPES:
                errors.append(f"{filename}: invalid party_type '{ptype}'")

        # Evidence IDs
        ev_list = data.get("evidence_ids", [])
        if len(ev_list) > 20:
            errors.append(f"{filename}: evidence_ids > 20")
        for ev in ev_list:
            if not (ev.startswith("order:") or ev.startswith("item:") or ev.startswith("payment:") or ev.startswith("seller:") or ev.startswith("policy:")):
                errors.append(f"{filename}: invalid evidence ID format '{ev}'")

        # Resolution Actions
        actions = data.get("resolution_actions", [])
        if len(actions) > 5:
            errors.append(f"{filename}: resolution_actions > 5")

    print("\nPrimary Issue Distribution across 50 Cases:")
    for k, v in sorted(issues_count.items()):
        print(f"  - {k}: {v} cases")

    if errors:
        print(f"\nFOUND {len(errors)} SCHEMA ERRORS:")
        for err in errors:
            print(f"  [ERROR] {err}")
    else:
        print("\nALL 50 CASES PASSED 100% STRICT SCHEMA CHECKS WITH ZERO ERRORS!")


if __name__ == "__main__":
    check_all_cases()
