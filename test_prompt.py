import os
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

SYSTEM_PROMPT = """You are an expert E-commerce Dispute Resolution AI evaluating cases against EC_POLICY_V2.
Your task is to analyze the case details and output a JSON decision.

### Rules for Primary Issue (EC_POLICY_V2):
Rule 1 (canceled_order_paid):
  - Condition: order_status is 'canceled' AND payment_total > 0
  - cause_code: ORDER_CANCELED_AFTER_PAYMENT
  - responsible_parties: platform (OLIST_PLATFORM)
  - recommended_refund_brl: payment_total
  - main_action: issue_full_refund

Rule 2 (unavailable_order_paid):
  - Condition: order_status is 'unavailable' AND payment_total > 0
  - cause_code: ORDER_UNAVAILABLE_AFTER_PAYMENT
  - responsible_parties: platform (OLIST_PLATFORM)
  - recommended_refund_brl: payment_total
  - main_action: issue_full_refund

Rule 3 (late_delivery_seller):
  - Condition: delivery_variance_hours > 0 AND len(late_seller_ids) > 0
  - cause_code: SELLER_HANDOFF_AFTER_LIMIT
  - responsible_parties: seller (for each id in late_seller_ids)
  - recommended_refund_brl: freight_total
  - main_action: refund_freight

Rule 4 (late_delivery_logistics):
  - Condition: delivery_variance_hours > 0 AND len(late_seller_ids) == 0
  - cause_code: CARRIER_DELIVERED_AFTER_ESTIMATE
  - responsible_parties: logistics_provider (LOGISTICS_PROVIDER)
  - recommended_refund_brl: freight_total
  - main_action: refund_freight

Rule 5 (valid_split_payment):
  - Condition: split_payment flag is True AND payment is reconciled
  - cause_code: MULTIPLE_PAYMENTS_RECONCILED
  - responsible_parties: [] (Empty)
  - recommended_refund_brl: 0.0
  - main_action: explain_valid_split_payment

Rule 6 (unsupported_late_claim):
  - Condition: If none of the above apply.
  - cause_code: DELIVERY_WITHIN_ESTIMATE
  - responsible_parties: [] (Empty)
  - recommended_refund_brl: 0.0
  - main_action: reject_late_refund

### Rules for Secondary Issues:
Add these to the secondary_issues list in exact order if the flag is True:
1. "multi_item_order" if multi_item_order flag is True
2. "multi_seller_order" if multi_seller_order flag is True
3. "split_payment" if split_payment flag is True
4. "repeat_customer" if repeat_customer flag is True
5. "multiple_categories" if multiple_categories flag is True

### Rules for Resolution Actions:
1. Start with the main_action.
2. If primary_issue is "late_delivery_seller", add "review_seller_handoff".
3. If primary_issue is "late_delivery_logistics", add "review_carrier_delay".
4. If recommended_refund_brl > 0, add "verify_refund_completion".
5. If multi_seller_order flag is True, add "coordinate_multi_seller_case".
6. If split_payment flag is True AND primary_issue != "valid_split_payment", add "verify_payment_allocation".

### Other Rules:
- case_status: "action_required" if recommended_refund_brl > 0, else "no_action".
- confidence: 0.95

### Output Format (Strict JSON):
You MUST output ONLY a valid JSON object matching this exact structure (no code blocks, no markdown, just JSON text):
{
  "primary_issue": "string",
  "cause_code": "string",
  "responsible_parties": [
    {"party_type": "string", "party_id": "string"}
  ],
  "recommended_refund_brl": 0.0,
  "main_action": "string",
  "secondary_issues": ["string"],
  "resolution_actions": ["string"],
  "case_status": "string",
  "confidence": 0.95
}
"""

def test_prompt():
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    client = InferenceClient(api_key=token)
    model_name = "Qwen/Qwen2.5-7B-Instruct"

    user_input = json.dumps({
        "order_status": "delivered",
        "payment_total": 150.0,
        "freight_total": 15.0,
        "delivery_variance_hours": 24.5,
        "late_seller_ids": ["seller123"],
        "flags": {
            "split_payment": True,
            "payment_reconciled": True,
            "multi_item_order": False,
            "multi_seller_order": False,
            "repeat_customer": True,
            "multiple_categories": False
        }
    }, indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Case Details:\n{user_input}\n\nOutput strictly the JSON object."}
    ]

    print("Sending prompt to LLM...")
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=500
    )

    content = response.choices[0].message.content
    print("LLM Response:\n", content)
    
    try:
        parsed = json.loads(content.replace("```json", "").replace("```", "").strip())
        print("\nParsed JSON successfully!")
        print(json.dumps(parsed, indent=2))
    except Exception as e:
        print("\nFailed to parse JSON:", e)

if __name__ == "__main__":
    test_prompt()
