"""CustomerAgent: lookup customer facts + LLM evaluates customer risk."""
from src.schemas import CaseContext, CustomerContext
from src.data_loader import DataLoader
from src.llm_client import call_llm


class CustomerAgent:
    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        claimed_order_id = context.claimed_order_id
        customer_id = data_loader.get_customer_id_by_order(claimed_order_id)

        if not customer_id:
            context.customer_context = CustomerContext(
                customer_unique_id="",
                related_order_ids=[]
            )
            context.flags.repeat_customer = False
            return context

        customer_unique_id = data_loader.get_customer_unique_id(customer_id)
        history = data_loader.get_customer_history(
            customer_unique_id, exclude_order_id=claimed_order_id
        )

        context.flags.repeat_customer = len(history) > 0

        context.customer_context = CustomerContext(
            customer_unique_id=customer_unique_id,
            related_order_ids=history
        )

        # ------------------------------------------------------------------
        # LLM: Đánh giá mức độ rủi ro và ưu tiên điều tra
        # Python đã tính: repeat_customer, related_order_count
        # LLM quyết định: customer_risk_level, investigation_priority
        # ------------------------------------------------------------------
        prompt = f"""Bạn là một chuyên gia phân tích tranh chấp thương mại điện tử. Dựa trên các thông tin khách hàng sau,
hãy đánh giá mức độ rủi ro của khách hàng và mức độ ưu tiên điều tra.

Thông tin khách hàng (đã được hệ thống tính toán trước):
- customer_unique_id: {customer_unique_id}
- related_order_count: {len(history)}
- is_repeat_customer: {context.flags.repeat_customer}

Hãy quyết định:
- customer_risk_level: "low" (0-1 đơn hàng trước đó), "medium" (2-5 đơn hàng), hoặc "high" (6+ đơn hàng hoặc có dấu hiệu đáng ngờ)
- investigation_priority: "normal" (bình thường) hoặc "elevated" (ưu tiên cao nếu rủi ro cao hoặc có nhiều tranh chấp trước đó)"""

        schema = {
            "type": "object",
            "properties": {
                "customer_risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "investigation_priority": {"type": "string", "enum": ["normal", "elevated"]}
            },
            "required": ["customer_risk_level", "investigation_priority"],
            "additionalProperties": False
        }

        result = call_llm(prompt, schema=schema, max_tokens=1024)

        # Store LLM evaluation in context flags for downstream agents
        if result:
            context.flags.customer_risk_level = result.get("customer_risk_level", "low")
            context.flags.investigation_priority = result.get("investigation_priority", "normal")
        else:
            # Fallback: simple rule
            if len(history) >= 6:
                context.flags.customer_risk_level = "high"
                context.flags.investigation_priority = "elevated"
            elif len(history) >= 2:
                context.flags.customer_risk_level = "medium"
                context.flags.investigation_priority = "normal"
            else:
                context.flags.customer_risk_level = "low"
                context.flags.investigation_priority = "normal"

        return context
