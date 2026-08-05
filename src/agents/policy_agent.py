from typing import List
from src.schemas import (
    CaseContext,
    CaseAssessment,
    RootCauseAnalysis,
    CauseCodeRank,
    PartyResponsible,
    FinancialResolution
)

class PolicyAgent:
    """
    Policy & Reasoning Agent (EC_POLICY_V2 Engine)
    Phụ trách: Bước 4 (Person 4)
    Nhiệm vụ: Áp dụng chính sách EC_POLICY_V2 để đưa ra đánh giá primary issue, 
             secondary issues, bên chịu trách nhiệm, bằng chứng evidence_ids, 
             khoản hoàn tiền và các hành động resolution_actions.
    """

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

        # ---------------------------------------------------------------------
        # 4.1 Áp dụng Quy Tắc Primary Issue (Thứ tự ưu tiên tuyệt đối 1 -> 6)
        # ---------------------------------------------------------------------
        primary_issue = ""
        cause_code = ""
        responsible_parties: List[PartyResponsible] = []
        recommended_refund_brl = 0.0
        main_action = ""

        # Rule 1: canceled_order_paid
        if context.flags.order_status == "canceled" and payment_total > 0:
            primary_issue = "canceled_order_paid"
            cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
            responsible_parties = [
                PartyResponsible(party_type="platform", party_id="OLIST_PLATFORM")
            ]
            recommended_refund_brl = round(payment_total, 2)
            main_action = "issue_full_refund"

        # Rule 2: unavailable_order_paid
        elif context.flags.order_status == "unavailable" and payment_total > 0:
            primary_issue = "unavailable_order_paid"
            cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            responsible_parties = [
                PartyResponsible(party_type="platform", party_id="OLIST_PLATFORM")
            ]
            recommended_refund_brl = round(payment_total, 2)
            main_action = "issue_full_refund"

        # Rule 3: late_delivery_seller
        elif delivery_variance > 0 and len(late_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
            responsible_parties = [
                PartyResponsible(party_type="seller", party_id=sid)
                for sid in late_seller_ids
            ]
            recommended_refund_brl = round(freight_total, 2)
            main_action = "refund_freight"

        # Rule 4: late_delivery_logistics
        elif delivery_variance > 0 and len(late_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            responsible_parties = [
                PartyResponsible(party_type="logistics_provider", party_id="LOGISTICS_PROVIDER")
            ]
            recommended_refund_brl = round(freight_total, 2)
            main_action = "refund_freight"

        # Rule 5: valid_split_payment
        elif context.flags.split_payment and context.payment_reconciliation.reconciled is True:
            primary_issue = "valid_split_payment"
            cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
            responsible_parties = []
            recommended_refund_brl = 0.0
            main_action = "explain_valid_split_payment"

        # Rule 6: unsupported_late_claim
        else:
            primary_issue = "unsupported_late_claim"
            cause_code = "DELIVERY_WITHIN_ESTIMATE"
            responsible_parties = []
            recommended_refund_brl = 0.0
            main_action = "reject_late_refund"

        # ---------------------------------------------------------------------
        # 4.2 Xác Định Secondary Issues (Thêm lần lượt theo đúng thứ tự)
        # ---------------------------------------------------------------------
        secondary_issues: List[str] = []
        if context.flags.multi_item_order:
            secondary_issues.append("multi_item_order")
        if context.flags.multi_seller_order:
            secondary_issues.append("multi_seller_order")
        if context.flags.split_payment:
            secondary_issues.append("split_payment")
        if context.flags.repeat_customer:
            secondary_issues.append("repeat_customer")
        if context.flags.multiple_categories:
            secondary_issues.append("multiple_categories")

        # ---------------------------------------------------------------------
        # 4.3 Xây Dựng Evidence IDs (Thứ tự định sẵn)
        # ---------------------------------------------------------------------
        evidence_ids: List[str] = []
        
        # 1. Order evidence
        evidence_ids.append(f"order:{context.claimed_order_id}")
        
        # 2. Item evidence
        if context.affected_entities and context.affected_entities.item_ids:
            for item_id in context.affected_entities.item_ids:
                if item_id.startswith("item:"):
                    evidence_ids.append(item_id)
                elif ":" in item_id:
                    evidence_ids.append(f"item:{item_id}")
                else:
                    evidence_ids.append(f"item:{context.claimed_order_id}:{item_id}")

        # 3. Payment evidence
        if context.affected_entities and context.affected_entities.payment_ids:
            for pay_id in context.affected_entities.payment_ids:
                if pay_id.startswith("payment:"):
                    evidence_ids.append(pay_id)
                elif ":" in pay_id:
                    evidence_ids.append(f"payment:{pay_id}")
                else:
                    evidence_ids.append(f"payment:{context.claimed_order_id}:{pay_id}")

        # 4. Seller evidence (cho từng seller chịu trách nhiệm nếu có)
        for party in responsible_parties:
            if party.party_type == "seller":
                evidence_ids.append(f"seller:{party.party_id}")

        # 5. Policy evidence
        evidence_ids.append(f"policy:{cause_code}")

        # ---------------------------------------------------------------------
        # 4.4 Xây Dựng Resolution Actions Bổ Sung
        # ---------------------------------------------------------------------
        resolution_actions: List[str] = [main_action]

        if primary_issue == "late_delivery_seller":
            resolution_actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            resolution_actions.append("review_carrier_delay")

        if recommended_refund_brl > 0:
            resolution_actions.append("verify_refund_completion")

        if context.flags.multi_seller_order:
            resolution_actions.append("coordinate_multi_seller_case")

        if context.flags.split_payment and primary_issue != "valid_split_payment":
            resolution_actions.append("verify_payment_allocation")

        # ---------------------------------------------------------------------
        # 4.5 Set Status & Confidence
        # ---------------------------------------------------------------------
        case_status = "action_required" if recommended_refund_brl > 0 else "no_action"
        confidence = 0.95

        # Cập nhật kết quả vào CaseContext
        context.case_assessment = CaseAssessment(
            primary_issue=primary_issue,
            secondary_issues=secondary_issues,
            case_status=case_status,
            confidence=confidence
        )

        context.root_cause_analysis = RootCauseAnalysis(
            ranked_causes=[CauseCodeRank(cause_code=cause_code, rank=1)],
            responsible_parties=responsible_parties
        )

        context.evidence_ids = evidence_ids

        context.financial_resolution = FinancialResolution(
            currency="BRL",
            recommended_refund_brl=recommended_refund_brl
        )

        context.resolution_actions = resolution_actions

        return context
