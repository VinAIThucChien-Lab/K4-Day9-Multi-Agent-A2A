from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CaseAssessment(BaseModel):
    primary_issue: str
    secondary_issues: List[str] = Field(default_factory=list)
    case_status: str  # "action_required" | "no_action"
    confidence: float = 0.95

class AffectedEntities(BaseModel):
    order_ids: List[str] = Field(default_factory=list)
    item_ids: List[str] = Field(default_factory=list)
    seller_ids: List[str] = Field(default_factory=list)
    payment_ids: List[str] = Field(default_factory=list)

class CustomerContext(BaseModel):
    customer_unique_id: str
    related_order_ids: List[str] = Field(default_factory=list)

class ProductContext(BaseModel):
    product_ids: List[str] = Field(default_factory=list)
    category_names: List[str] = Field(default_factory=list)

class SellerHandoffAnalysis(BaseModel):
    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool = False

class DeliveryAnalysis(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: List[SellerHandoffAnalysis] = Field(default_factory=list)
    late_handoff_seller_ids: List[str] = Field(default_factory=list)

class PaymentReconciliation(BaseModel):
    currency: str = "BRL"
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: List[str] = Field(default_factory=list)

class CauseCodeRank(BaseModel):
    cause_code: str
    rank: int

class PartyResponsible(BaseModel):
    party_type: str  # "platform" | "seller" | "logistics_provider"
    party_id: str

class RootCauseAnalysis(BaseModel):
    ranked_causes: List[CauseCodeRank] = Field(default_factory=list)
    responsible_parties: List[PartyResponsible] = Field(default_factory=list)

class FinancialResolution(BaseModel):
    currency: str = "BRL"
    recommended_refund_brl: float = 0.0

class InternalFlags(BaseModel):
    has_items: bool = True
    order_status: str = ""
    multi_item_order: bool = False
    multi_seller_order: bool = False
    split_payment: bool = False
    repeat_customer: bool = False
    multiple_categories: bool = False

class CaseContext(BaseModel):
    case_id: str
    claimed_order_id: str
    customer_request: Dict[str, Any] = Field(default_factory=dict)
    investigation_scope: Dict[str, Any] = Field(default_factory=dict)
    policy_version: str = "EC_POLICY_V2"
    
    case_assessment: Optional[CaseAssessment] = None
    affected_entities: AffectedEntities = Field(default_factory=AffectedEntities)
    customer_context: Optional[CustomerContext] = None
    product_context: ProductContext = Field(default_factory=ProductContext)
    delivery_analysis: Optional[DeliveryAnalysis] = None
    payment_reconciliation: PaymentReconciliation = Field(default_factory=PaymentReconciliation)
    root_cause_analysis: RootCauseAnalysis = Field(default_factory=RootCauseAnalysis)
    evidence_ids: List[str] = Field(default_factory=list)
    financial_resolution: FinancialResolution = Field(default_factory=FinancialResolution)
    resolution_actions: List[str] = Field(default_factory=list)
    
    flags: InternalFlags = Field(default_factory=InternalFlags)
