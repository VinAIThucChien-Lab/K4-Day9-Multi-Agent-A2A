"""Deep audit script checking logic & data of all 50 cases against Olist dataset."""

import json
import os
import glob
from src.data_loader import DataLoader

def deep_audit():
    dl = DataLoader()
    output_files = sorted(glob.glob("output/*.json"))
    print(f"Deep auditing {len(output_files)} cases...")

    for filepath in output_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            out = json.load(f)

        case_id = out["case_id"]
        # Find input case
        input_path = os.path.join("input", "input", f"{case_id}.json")
        if not os.path.exists(input_path):
            input_path = os.path.join("input", f"{case_id}.json")

        with open(input_path, "r", encoding="utf-8") as f:
            inp = json.load(f)

        claimed_order_id = inp["customer_request"]["claimed_order_id"]
        order = dl.get_order(claimed_order_id)
        items = dl.get_order_items(claimed_order_id)
        payments = dl.get_order_payments(claimed_order_id)

        # 1. Check order status
        order_status = order.get("order_status")
        payment_total = round(sum(float(p["payment_value"]) for p in payments), 2)
        item_total = round(sum(float(i["price"]) for i in items), 2) if items else 0.0
        freight_total = round(sum(float(i["freight_value"]) for i in items), 2) if items else 0.0
        expected_total = round(item_total + freight_total, 2) if items else None

        primary = out["case_assessment"]["primary_issue"]
        refund = out["financial_resolution"]["recommended_refund_brl"]

        # Audit Primary Rules
        if order_status == "canceled" and payment_total > 0:
            if primary != "canceled_order_paid" or refund != payment_total:
                print(f"[ERR] {case_id}: Order status canceled, expected canceled_order_paid with refund {payment_total}, got {primary} with refund {refund}")
        elif order_status == "unavailable" and payment_total > 0:
            if primary != "unavailable_order_paid" or refund != payment_total:
                print(f"[ERR] {case_id}: Order status unavailable, expected unavailable_order_paid with refund {payment_total}, got {primary} with refund {refund}")

        # Audit Evidence IDs
        evidence_ids = out.get("evidence_ids", [])
        expected_order_ev = f"order:{claimed_order_id}"
        if expected_order_ev not in evidence_ids:
            print(f"[ERR] {case_id}: Missing {expected_order_ev} in evidence_ids")

        for item in items[:5]:
            expected_item_ev = f"item:{claimed_order_id}:{item['order_item_id']}"
            if expected_item_ev not in evidence_ids:
                print(f"[ERR] {case_id}: Missing {expected_item_ev} in evidence_ids")

        for pay in payments[:5]:
            expected_pay_ev = f"payment:{claimed_order_id}:{pay['payment_sequential']}"
            if expected_pay_ev not in evidence_ids:
                print(f"[ERR] {case_id}: Missing {expected_pay_ev} in evidence_ids")

    print("Deep audit completed!")

if __name__ == "__main__":
    deep_audit()
