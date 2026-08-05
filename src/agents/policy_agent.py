import os
import json
from typing import List
from huggingface_hub import InferenceClient
import openai

from src.schemas import (
    CaseContext,
    CaseAssessment,
    RootCauseAnalysis,
    CauseCodeRank,
    PartyResponsible,
    FinancialResolution
)
from src.config import LLM_MODEL_NAME, NVIDIA_API_KEY

SYSTEM_PROMPT = """You are an expert E-commerce Dispute Resolution AI evaluating cases against EC_POLICY_V2.
Your task is to analyze the case details and output a JSON decision.

### Rules for Primary Issue (EC_POLICY_V2):
Rule 1:
  - primary_issue: canceled_order_paid
  - Condition: order_status is 'canceled' AND payment_total > 0
  - cause_code: ORDER_CANCELED_AFTER_PAYMENT
  - responsible_parties: platform (OLIST_PLATFORM)
  - recommended_refund_brl: payment_total
  - main_action: issue_full_refund

Rule 2:
  - primary_issue: unavailable_order_paid
  - Condition: order_status is 'unavailable' AND payment_total > 0
  - cause_code: ORDER_UNAVAILABLE_AFTER_PAYMENT
  - responsible_parties: platform (OLIST_PLATFORM)
  - recommended_refund_brl: payment_total
  - main_action: issue_full_refund

Rule 3:
  - primary_issue: late_delivery_seller
  - Condition: delivery_variance_hours > 0 AND len(late_seller_ids) > 0
  - cause_code: SELLER_HANDOFF_AFTER_LIMIT
  - responsible_parties: seller (for each id in late_seller_ids)
  - recommended_refund_brl: freight_total
  - main_action: refund_freight

Rule 4:
  - primary_issue: late_delivery_logistics
  - Condition: delivery_variance_hours > 0 AND len(late_seller_ids) == 0
  - cause_code: CARRIER_DELIVERED_AFTER_ESTIMATE
  - responsible_parties: logistics_provider (LOGISTICS_PROVIDER)
  - recommended_refund_brl: freight_total
  - main_action: refund_freight

Rule 5:
  - primary_issue: valid_split_payment
  - Condition: split_payment flag is True AND payment is reconciled
  - cause_code: MULTIPLE_PAYMENTS_RECONCILED
  - responsible_parties: [] (Empty)
  - recommended_refund_brl: 0.0
  - main_action: explain_valid_split_payment

Rule 6:
  - primary_issue: unsupported_late_claim
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

class PolicyAgent:
    """
    Policy & Reasoning Agent (EC_POLICY_V2 Engine) - LLM Powered
    Phụ trách: Bước 4 (Person 4)
    Nhiệm vụ: Sử dụng LLM để áp dụng chính sách EC_POLICY_V2 đưa ra đánh giá primary issue, 
             secondary issues, bên chịu trách nhiệm, bằng chứng evidence_ids, 
             khoản hoàn tiền và các hành động resolution_actions.
    """
    def __init__(self):
        self.hf_client = None
        self.nv_client = None
        if NVIDIA_API_KEY:
            self.nv_client = openai.OpenAI(
                api_key=NVIDIA_API_KEY,
                base_url="https://integrate.api.nvidia.com/v1"
            )
        else:
            token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
            if token:
                self.hf_client = InferenceClient(api_key=token)

    def process(self, context: CaseContext) -> CaseContext:
        payment_total = (
            context.payment_reconciliation.payment_total_brl
            if context.payment_reconciliation and context.payment_reconciliation.payment_total_brl is not None
            else 0.0
        )
        freight_total = (
            context.payment_reconciliation.freight_total_brl
            if context.payment_reconciliation and context.payment_reconciliation.freight_total_brl is not None
            else 0.0
        )
        delivery_variance = (
            context.delivery_analysis.delivery_variance_hours
            if context.delivery_analysis and context.delivery_analysis.delivery_variance_hours is not None
            else 0.0
        )
        late_seller_ids = (
            context.delivery_analysis.late_handoff_seller_ids
            if context.delivery_analysis
            else []
        )

        # -----------------------------------------------------------------------
        # STEP 1: Python tính toán (deterministic) - KHÔNG để LLM tính
        # -----------------------------------------------------------------------
        order_status = context.flags.order_status
        split_payment_flag = context.flags.split_payment
        payment_reconciled = (context.payment_reconciliation.reconciled is True) if context.payment_reconciliation else False
        multi_item = context.flags.multi_item_order
        multi_seller = context.flags.multi_seller_order
        repeat_customer = context.flags.repeat_customer
        multiple_categories = context.flags.multiple_categories

        # Python xác định primary_issue theo thứ tự ưu tiên đúng
        is_canceled = (order_status == "canceled") and (payment_total > 0)
        is_unavailable = (order_status == "unavailable") and (payment_total > 0)
        is_late = (delivery_variance is not None) and (delivery_variance > 0)
        has_late_sellers = len(late_seller_ids) > 0
        is_split_reconciled = split_payment_flag and payment_reconciled

        if is_canceled:
            python_primary = "canceled_order_paid"
            python_cause = "ORDER_CANCELED_AFTER_PAYMENT"
            python_responsible = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            python_refund = round(payment_total, 2)
            python_action = "issue_full_refund"
        elif is_unavailable:
            python_primary = "unavailable_order_paid"
            python_cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            python_responsible = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            python_refund = round(payment_total, 2)
            python_action = "issue_full_refund"
        elif is_late and has_late_sellers:
            python_primary = "late_delivery_seller"
            python_cause = "SELLER_HANDOFF_AFTER_LIMIT"
            python_responsible = [{"party_type": "seller", "party_id": sid} for sid in late_seller_ids]
            python_refund = round(freight_total, 2)
            python_action = "refund_freight"
        elif is_late and not has_late_sellers:
            python_primary = "late_delivery_logistics"
            python_cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            python_responsible = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            python_refund = round(freight_total, 2)
            python_action = "refund_freight"
        elif is_split_reconciled:
            python_primary = "valid_split_payment"
            python_cause = "MULTIPLE_PAYMENTS_RECONCILED"
            python_responsible = []
            python_refund = 0.0
            python_action = "explain_valid_split_payment"
        else:
            python_primary = "unsupported_late_claim"
            python_cause = "DELIVERY_WITHIN_ESTIMATE"
            python_responsible = []
            python_refund = 0.0
            python_action = "reject_late_refund"

        python_case_status = "action_required" if python_refund > 0 else "no_action"

        # -----------------------------------------------------------------------
        # STEP 2: Hỏi LLM để xác nhận và quyết định secondary_issues + actions
        # -----------------------------------------------------------------------
        llm_prompt = f"""Bạn là một AI Giải quyết Tranh chấp Thương mại Điện tử.
Hệ thống Python đã xác định phân loại chính dựa trên các tính toán số liệu chính xác:

Vấn đề chính (Primary Issue): {python_primary}
Mã nguyên nhân (Cause Code): {python_cause}
Số tiền hoàn lại (BRL): {python_refund}
Hành động chính (Main Action): {python_action}

Các cờ (flags) của vụ việc được hệ thống tính toán:
- multi_item_order: {multi_item}
- multi_seller_order: {multi_seller}
- split_payment: {split_payment_flag}
- repeat_customer: {repeat_customer}
- multiple_categories: {multiple_categories}

Nhiệm vụ của bạn CHỈ LÀ xác định:
1. secondary_issues: liệt kê theo ĐÚNG THỨ TỰ NÀY, chỉ đưa vào nếu cờ là True:
   - "multi_item_order" nếu multi_item_order là True
   - "multi_seller_order" nếu multi_seller_order là True
   - "split_payment" nếu split_payment là True
   - "repeat_customer" nếu repeat_customer là True
   - "multiple_categories" nếu multiple_categories là True

2. resolution_actions: liệt kê theo ĐÚNG THỨ TỰ NÀY:
   - Bắt đầu với: "{python_action}"
   - Nếu primary_issue là "late_delivery_seller", thêm "review_seller_handoff"
   - Nếu primary_issue là "late_delivery_logistics", thêm "review_carrier_delay"
   - Nếu số tiền hoàn lại > 0, thêm "verify_refund_completion"
   - Nếu multi_seller_order là True, thêm "coordinate_multi_seller_case"
   - Nếu split_payment là True VÀ primary_issue KHÔNG PHẢI "valid_split_payment", thêm "verify_payment_allocation"
"""

        policy_schema = {
            "type": "object",
            "properties": {
                "secondary_issues": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["multi_item_order", "multi_seller_order", "split_payment", "repeat_customer", "multiple_categories"]}
                },
                "resolution_actions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["secondary_issues", "resolution_actions"],
            "additionalProperties": False
        }

        from src.llm_client import call_llm
        llm_result = call_llm(llm_prompt, schema=policy_schema, max_tokens=1024)

        # Fallback: Python tự tính secondary_issues và actions nếu LLM lỗi
        if not llm_result:
            secondary_issues = []
            if multi_item: secondary_issues.append("multi_item_order")
            if multi_seller: secondary_issues.append("multi_seller_order")
            if split_payment_flag: secondary_issues.append("split_payment")
            if repeat_customer: secondary_issues.append("repeat_customer")
            if multiple_categories: secondary_issues.append("multiple_categories")

            resolution_actions = [python_action]
            if python_primary == "late_delivery_seller": resolution_actions.append("review_seller_handoff")
            elif python_primary == "late_delivery_logistics": resolution_actions.append("review_carrier_delay")
            if python_refund > 0: resolution_actions.append("verify_refund_completion")
            if multi_seller: resolution_actions.append("coordinate_multi_seller_case")
            if split_payment_flag and python_primary != "valid_split_payment": resolution_actions.append("verify_payment_allocation")
            llm_result = {"secondary_issues": secondary_issues, "resolution_actions": resolution_actions}

        # Assemble final result using Python-computed primary fields + LLM secondary/actions
        parsed = {
            "primary_issue": python_primary,
            "cause_code": python_cause,
            "responsible_parties": python_responsible,
            "recommended_refund_brl": python_refund,
            "main_action": python_action,
            "secondary_issues": llm_result.get("secondary_issues", []),
            "resolution_actions": llm_result.get("resolution_actions", []),
            "case_status": python_case_status,
            "confidence": 0.95
        }


        # ---------------------------------------------------------------------
        # Cập nhật kết quả vào CaseContext
        # ---------------------------------------------------------------------
        context.case_assessment = CaseAssessment(
            primary_issue=parsed.get("primary_issue", ""),
            secondary_issues=parsed.get("secondary_issues", []),
            case_status=parsed.get("case_status", "no_action"),
            confidence=float(parsed.get("confidence", 0.95))
        )

        responsible_parties = []
        for rp in parsed.get("responsible_parties", []):
            responsible_parties.append(PartyResponsible(party_type=rp.get("party_type", ""), party_id=rp.get("party_id", "")))

        context.root_cause_analysis = RootCauseAnalysis(
            ranked_causes=[CauseCodeRank(cause_code=parsed.get("cause_code", ""), rank=1)],
            responsible_parties=responsible_parties
        )

        context.financial_resolution = FinancialResolution(
            currency="BRL",
            recommended_refund_brl=float(parsed.get("recommended_refund_brl", 0.0))
        )

        context.resolution_actions = parsed.get("resolution_actions", [])

        # ---------------------------------------------------------------------
        # Xây Dựng Evidence IDs (Thứ tự định sẵn)
        # ---------------------------------------------------------------------
        evidence_ids: List[str] = []
        evidence_ids.append(f"order:{context.claimed_order_id}")
        
        if context.affected_entities and context.affected_entities.item_ids:
            for item_id in context.affected_entities.item_ids:
                if item_id.startswith("item:"):
                    evidence_ids.append(item_id)
                elif ":" in item_id:
                    evidence_ids.append(f"item:{item_id}")
                else:
                    evidence_ids.append(f"item:{context.claimed_order_id}:{item_id}")

        if context.affected_entities and context.affected_entities.payment_ids:
            for pay_id in context.affected_entities.payment_ids:
                if pay_id.startswith("payment:"):
                    evidence_ids.append(pay_id)
                elif ":" in pay_id:
                    evidence_ids.append(f"payment:{pay_id}")
                else:
                    evidence_ids.append(f"payment:{context.claimed_order_id}:{pay_id}")

        for party in responsible_parties:
            if party.party_type == "seller":
                evidence_ids.append(f"seller:{party.party_id}")

        if parsed.get("cause_code"):
            evidence_ids.append(f"policy:{parsed.get('cause_code')}")

        context.evidence_ids = evidence_ids

        return context

    def _fallback_logic(self, context, payment_total, freight_total, delivery_variance, late_seller_ids):
        # ... logic if LLM fails ...
        primary_issue = ""
        cause_code = ""
        responsible_parties = []
        recommended_refund_brl = 0.0
        main_action = ""

        if context.flags.order_status == "canceled" and payment_total > 0:
            primary_issue = "canceled_order_paid"
            cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = round(payment_total, 2)
            main_action = "issue_full_refund"
        elif context.flags.order_status == "unavailable" and payment_total > 0:
            primary_issue = "unavailable_order_paid"
            cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = round(payment_total, 2)
            main_action = "issue_full_refund"
        elif delivery_variance > 0 and len(late_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
            responsible_parties = [{"party_type": "seller", "party_id": sid} for sid in late_seller_ids]
            recommended_refund_brl = round(freight_total, 2)
            main_action = "refund_freight"
        elif delivery_variance > 0 and len(late_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund_brl = round(freight_total, 2)
            main_action = "refund_freight"
        elif context.flags.split_payment and context.payment_reconciliation.reconciled is True:
            primary_issue = "valid_split_payment"
            cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
            responsible_parties = []
            recommended_refund_brl = 0.0
            main_action = "explain_valid_split_payment"
        else:
            primary_issue = "unsupported_late_claim"
            cause_code = "DELIVERY_WITHIN_ESTIMATE"
            responsible_parties = []
            recommended_refund_brl = 0.0
            main_action = "reject_late_refund"

        secondary_issues = []
        if context.flags.multi_item_order: secondary_issues.append("multi_item_order")
        if context.flags.multi_seller_order: secondary_issues.append("multi_seller_order")
        if context.flags.split_payment: secondary_issues.append("split_payment")
        if context.flags.repeat_customer: secondary_issues.append("repeat_customer")
        if context.flags.multiple_categories: secondary_issues.append("multiple_categories")

        resolution_actions = [main_action]
        if primary_issue == "late_delivery_seller": resolution_actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics": resolution_actions.append("review_carrier_delay")
        if recommended_refund_brl > 0: resolution_actions.append("verify_refund_completion")
        if context.flags.multi_seller_order: resolution_actions.append("coordinate_multi_seller_case")
        if context.flags.split_payment and primary_issue != "valid_split_payment": resolution_actions.append("verify_payment_allocation")

        case_status = "action_required" if recommended_refund_brl > 0 else "no_action"

        return {
            "primary_issue": primary_issue,
            "cause_code": cause_code,
            "responsible_parties": responsible_parties,
            "recommended_refund_brl": recommended_refund_brl,
            "main_action": main_action,
            "secondary_issues": secondary_issues,
            "resolution_actions": resolution_actions,
            "case_status": case_status,
            "confidence": 0.95
        }
