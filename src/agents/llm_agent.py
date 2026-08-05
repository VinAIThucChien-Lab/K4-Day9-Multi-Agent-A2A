"""LLM reasoning through OpenRouter with a deterministic local fallback."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

from src.config import LLM_MODEL_NAME
from src.schemas import CaseContext

logger = logging.getLogger(__name__)

class LLMReasoningAgent:
    """
    Gọi Qwen2.5 7B Instruct qua OpenRouter để tạo diễn giải bổ trợ. Quyết định policy vẫn do
    PolicyAgent thực hiện trên dữ liệu có thể kiểm chứng.
    """

    def __init__(self, token: Optional[str] = None, model_name: Optional[str] = None):
        load_dotenv()
        self.token = token or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name or LLM_MODEL_NAME
        self.provider = "openrouter"
        self.timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "20"))
        self.client = None
        self.api_disabled = False

        if self.token and not self.token.startswith("sk-or-your"):
            try:
                self.client = OpenAI(
                    api_key=self.token,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=self.timeout_seconds,
                )
            except Exception as e:
                logger.warning(f"Could not initialize OpenRouter client: {e}")

    def process(self, context: CaseContext) -> CaseContext:
        """
        Gửi thông tin context thu thập được sang LLM để nhận phân tích suy luận bổ trợ.
        """
        order_id = context.claimed_order_id
        order_status = context.flags.order_status
        payment_total = context.payment_reconciliation.payment_total_brl if context.payment_reconciliation else 0.0
        delivery_variance = context.delivery_analysis.delivery_variance_hours if context.delivery_analysis else 0.0
        late_sellers = context.delivery_analysis.late_handoff_seller_ids if context.delivery_analysis else []

        if self.client and not self.api_disabled:
            try:
                prompt = (
                    f"Case ID: {context.case_id}\n"
                    f"Claimed Order ID: {order_id}\n"
                    f"Order Status: {order_status}\n"
                    f"Payment Total (BRL): {payment_total}\n"
                    f"Delivery Variance (Hours): {delivery_variance}\n"
                    f"Late Handoff Sellers: {late_sellers}\n"
                    "Hãy tóm tắt vấn đề chính và bên chịu trách nhiệm bằng đúng 2 câu tiếng Việt. "
                    "Không dịch tên danh mục hoặc mã định danh sang tiếng Anh."
                )
                messages = [
                    {"role": "system", "content": "Bạn là chuyên gia xử lý tranh chấp thương mại điện tử. Chỉ trả lời bằng tiếng Việt."},
                    {"role": "user", "content": prompt}
                ]
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=100
                )
                content = response.choices[0].message.content
                if content:
                    context.investigation_scope["llm_reasoning"] = content.strip()
                    context.investigation_scope["llm_status"] = "api_success"
                    context.investigation_scope["llm_model"] = self.model_name
                    context.investigation_scope["llm_provider"] = self.provider
                    print(
                        f"[API_SUCCESS] {context.case_id} | "
                        f"model={self.model_name} | provider={self.provider}"
                    )
                    logger.info(f"LLM reasoning generated via OpenRouter for {context.case_id}")
                    return context
            except Exception as e:
                err_msg = str(e)
                if "402" in err_msg or "Payment Required" in err_msg or "depleted" in err_msg:
                    print("\n[INFO] OpenRouter quota không khả dụng; chuyển sang suy luận local cho các case còn lại.")
                    self.api_disabled = True
                else:
                    logger.warning(f"OpenRouter API call for case {context.case_id} failed: {e}. Falling back gracefully.")

        # 2. Fallback: Local Structured Reasoning Engine (Đảm bảo luôn điền llm_reasoning sạch sẽ)
        reasoning_summary = self._generate_local_reasoning(context)
        context.investigation_scope["llm_reasoning"] = reasoning_summary
        context.investigation_scope["llm_status"] = "local_fallback"
        context.investigation_scope["llm_model"] = self.model_name
        context.investigation_scope["llm_provider"] = self.provider
        print(
            f"[LOCAL_FALLBACK] {context.case_id} | "
            f"model={self.model_name} | provider={self.provider}"
        )
        return context

    def _generate_local_reasoning(self, context: CaseContext) -> str:
        """Tạo bản tóm tắt suy luận đa đại lý chuẩn xác khi API bên ngoài bị giới hạn."""
        status = context.flags.order_status
        dev_var = context.delivery_analysis.delivery_variance_hours if context.delivery_analysis else 0.0
        late_sellers = context.delivery_analysis.late_handoff_seller_ids if context.delivery_analysis else []

        if status == "canceled":
            return f"Đơn {context.claimed_order_id} đã bị hủy sau khi thanh toán. Nền tảng chịu trách nhiệm hoàn toàn bộ tiền."
        elif status == "unavailable":
            return f"Đơn {context.claimed_order_id} không còn khả dụng sau khi thanh toán. Nền tảng chịu trách nhiệm hoàn toàn bộ tiền."
        elif dev_var and dev_var > 0:
            if late_sellers:
                return f"Đơn {context.claimed_order_id} giao muộn {dev_var} giờ do seller bàn giao trễ ({late_sellers}). Seller chịu trách nhiệm hoàn phí vận chuyển."
            else:
                return f"Đơn {context.claimed_order_id} giao muộn {dev_var} giờ trong khâu vận chuyển. Đơn vị logistics chịu trách nhiệm hoàn phí vận chuyển."
        elif context.flags.split_payment and context.payment_reconciliation.reconciled:
            return f"Đơn {context.claimed_order_id} có nhiều khoản thanh toán và đã đối soát khớp. Không cần hoàn tiền."
        else:
            return f"Đơn {context.claimed_order_id} được giao trong thời hạn và thanh toán khớp tổng dự kiến. Khiếu nại hoàn tiền bị từ chối."
