# AGENTS.md — Quy Trình Phân Công & Checklist Multi-Agent (5 Bước / 5 Developers)

Tài liệu này định nghĩa chi tiết phân công công việc, giao thức kết nối (Handoff Schemas), thuật toán xử lý và checklist cụ thể cho 5 lập trình viên cùng phát triển hệ thống Multi-Agent E-commerce Dispute Resolution (`EC_POLICY_V2`). 

Mục tiêu: **Không bị trùng lặp hay xung đột code (conflict)**, người làm sau kết nối mượt mà với output của người làm trước nhờ **Contract Dữ Liệu (`CaseContext`)** cố định.

---

## 📐 Handoff Contract & Quy Tắc Chung (Cả 5 Người Cần Tuân Thủ)

> [!IMPORTANT]
> **BẮT BUỘC ĐỌC KĨ**: Trước khi thực hiện bất kỳ công việc nào, tất cả 5 lập trình viên **BẮT BUỘC** phải đọc kỹ file [implementation_plan.md](file:///home/myvh07/VinLab/K4-Day9-Multi-Agent-A2A/implementation_plan.md) để nắm rõ kiến trúc tổng thể, luồng Handoff Agent-to-Agent (A2A) và kế hoạch triển khai chi tiết.

1. **Shared State / Context Model**: Tất cả các Agent đọc và ghi vào một đối tượng duy nhất `CaseContext` (được định nghĩa chi tiết ở Bước 1 trong `src/schemas.py`).
2. **Không tự ý đổi tên trường trong `CaseContext`**: Người làm sau dựa vào các thuộc tính của `CaseContext`. Nếu cần thêm thuộc tính phụ, hãy thêm vào `flags: InternalFlags`.
3. **Môi trường & Git**:
   - API Key đặt tại `.env` (`HF_TOKEN`, `HUGGINGFACEHUB_API_TOKEN`, etc.).
   - Model name cố định trong code và `metadata.json` (Model $\le 10\text{B}$ parameters, e.g. `Qwen/Qwen3-VL-8B-Instruct`).
   - Mỗi người làm trên file/module được phân công, không sửa file của người khác.

---

## 🏛️ Giao Thức Dữ Liệu Chuẩn (`src/schemas.py`)

Person 1 triển khai toàn bộ các class Pydantic này để Person 2, 3, 4, 5 import sử dụng:

```python
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
```

---

## 📍 Bước 1: Person 1 — Core Data Engine, Configuration & Shared Data Models (Foundation)

> **Mục tiêu**: Xây dựng bộ nạp dữ liệu Olist CSV, đọc file cấu hình và xuất bản Data Contract (`CaseContext`).

### 📁 Tệp tin phụ trách:
- `src/config.py`
- `src/schemas.py`
- `src/data_loader.py`

### 📋 Checklist chi tiết:
- [ ] **1.1 Config (`src/config.py`)**:
  - Đọc file `.env` bằng `python-dotenv`.
  - Khai báo các hằng số đường dẫn: `DATA_DIR`, `INPUT_DIR`, `OUTPUT_DIR`, `LOGGING_DIR`.
  - Khai báo hằng số Model: `LLM_MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"`.
- [ ] **1.2 Schemas (`src/schemas.py`)**:
  - Tạo đầy đủ các Pydantic model như phần **Giao Thức Dữ Liệu Chuẩn** ở trên.
- [ ] **1.3 Data Loader (`src/data_loader.py`)**:
  - Tải 9 file CSV trong `data/` vào bộ nhớ khi khởi tạo class `DataLoader`.
  - Xây dựng Index dạng `dict` tra cứu $O(1)$:
    - `orders_by_id`: `order_id -> row_dict`
    - `orders_by_customer`: `customer_id -> order_id`
    - `customers_by_id`: `customer_id -> customer_unique_id`
    - `customer_orders_map`: `customer_unique_id -> list[order_id]`
    - `items_by_order`: `order_id -> list[item_row_dict]`
    - `payments_by_order`: `order_id -> list[payment_row_dict]`
    - `products_by_id`: `product_id -> product_row_dict`
    - `category_translation`: `product_category_name -> product_category_name_english`
  - Cung cấp các hàm helper công khai:
    - `get_order(order_id: str) -> dict`
    - `get_customer_id_by_order(order_id: str) -> str`
    - `get_customer_unique_id(customer_id: str) -> str`
    - `get_customer_history(customer_unique_id: str, exclude_order_id: str) -> list[str]`
    - `get_order_items(order_id: str) -> list[dict]`
    - `get_order_payments(order_id: str) -> list[dict]`
    - `get_product(product_id: str) -> dict`
    - `translate_category(category_pt: str) -> str`
- [ ] **1.4 Verification**:
  - Chạy `python -c "from src.data_loader import DataLoader; dl = DataLoader(); print(dl.get_order('e4834301c8177937d5085580f7454200'))"` để kiểm tra tính đúng đắn.

---

## 📍 Bước 2: Person 2 — Domain Extraction Agents Part 1: Customer Agent & Order-Product Agent

> **Mục tiêu**: Xây dựng 2 Agent phân tích thông tin Khách hàng và Chi tiết Đơn hàng / Sản phẩm / Seller.

### 📁 Tệp tin phụ trách:
- `src/agents/customer_agent.py`
- `src/agents/order_product_agent.py`

### 🔗 Input Handoff từ Person 1:
- Class `CaseContext` và class `DataLoader`.

### 📋 Checklist chi tiết:
- [ ] **2.1 Customer Agent (`src/agents/customer_agent.py`)**:
  - Class `CustomerAgent`: Hàm `process(context: CaseContext, data_loader: DataLoader) -> CaseContext`.
  - Tra cứu `customer_id` từ `claimed_order_id`.
  - Tra cứu `customer_unique_id` từ `customer_id`.
  - Lấy tất cả các order của `customer_unique_id`, **loại trừ** `claimed_order_id` để đưa vào `related_order_ids` (tối đa 5 order).
  - Điền `context.customer_context = CustomerContext(customer_unique_id=..., related_order_ids=...)`.
  - Cập nhật cờ: `context.flags.repeat_customer = len(related_order_ids) > 0`.
- [ ] **2.2 Order & Product Agent (`src/agents/order_product_agent.py`)**:
  - Class `OrderProductAgent`: Hàm `process(context: CaseContext, data_loader: DataLoader) -> CaseContext`.
  - Lấy thông tin order từ `data_loader.get_order(claimed_order_id)`. Điền `context.flags.order_status = order["order_status"]`.
  - Điền `affected_entities.order_ids = [claimed_order_id]`.
  - Lấy danh sách item từ `data_loader.get_order_items(claimed_order_id)`.
  - **Trường hợp Đơn không có Items (No Items)**:
    - Set `context.flags.has_items = False`.
    - `affected_entities.item_ids = []`
    - `affected_entities.seller_ids = []`
    - `product_context.product_ids = []`
    - `product_context.category_names = []`
    - `payment_reconciliation.item_total_brl = None`
    - `payment_reconciliation.freight_total_brl = None`
    - `payment_reconciliation.expected_total_brl = None`
  - **Trường hợp Đơn có Items**:
    - Set `context.flags.has_items = True`.
    - `item_ids`: `[f"{claimed_order_id}:{item['order_item_id']}" for item in items]` (tối đa 5).
    - `seller_ids`: Danh sách seller_id duy nhất (tối đa 3).
    - `product_ids`: Danh sách product_id duy nhất (tối đa 5).
    - `category_names`: Dịch `product_category_name` sang tiếng Anh qua `data_loader.translate_category` (duy nhất, tối đa 5).
    - Tính toán tài chính (làm tròn 2 chữ số):
      - `item_total_brl = round(sum(float(item['price']) for item in items), 2)`
      - `freight_total_brl = round(sum(float(item['freight_value']) for item in items), 2)`
      - `expected_total_brl = round(item_total_brl + freight_total_brl, 2)`
    - Cập nhật cờ:
      - `context.flags.multi_item_order = len(items) >= 2`
      - `context.flags.multi_seller_order = len(seller_ids) >= 2`
      - `context.flags.multiple_categories = len(category_names) >= 2`
- [ ] **2.3 Verification**:
  - Viết test thử chạy `CustomerAgent` và `OrderProductAgent` trên 1 case mẫu, kiểm tra `context.flags` và `context.payment_reconciliation.expected_total_brl`.

---

## 📍 Bước 3: Person 3 — Domain Extraction Agents Part 2: Payment Agent & Delivery Agent

> **Mục tiêu**: Xây dựng 2 Agent phân tích Thanh toán (Reconciliation) và Thời gian vận chuyển/bàn giao (Delivery & Seller Handoff).

### 📁 Tệp tin phụ trách:
- `src/agents/payment_agent.py`
- `src/agents/delivery_agent.py`

### 🔗 Input Handoff từ Person 1 & 2:
- Nhận `CaseContext` đã được Person 2 điền đầy đủ `expected_total_brl` và trạng thái `has_items`.

### 📋 Checklist chi tiết:
- [ ] **3.1 Payment Agent (`src/agents/payment_agent.py`)**:
  - Class `PaymentAgent`: Hàm `process(context: CaseContext, data_loader: DataLoader) -> CaseContext`.
  - Lấy danh sách payment rows từ `data_loader.get_order_payments(claimed_order_id)`.
  - `payment_ids`: `[f"{claimed_order_id}:{row['payment_sequential']}" for row in payments]` (tối đa 5).
  - `payment_types`: Danh sách các `payment_type` duy nhất trong order.
  - `payment_total_brl = round(sum(float(row['payment_value']) for row in payments), 2)`.
  - `affected_entities.payment_ids = payment_ids`.
  - **Đối soát dữ liệu (Reconciliation)**:
    - Nếu `context.flags.has_items` là `False`:
      - `payment_reconciliation.difference_brl = None`
      - `payment_reconciliation.reconciled = None`
    - Nếu `context.flags.has_items` là `True`:
      - `difference_brl = round(payment_total_brl - context.payment_reconciliation.expected_total_brl, 2)`
      - `reconciled = abs(difference_brl) <= 0.10`
  - Cập nhật cờ: `context.flags.split_payment = len(payments) >= 2`.
- [ ] **3.2 Delivery Agent (`src/agents/delivery_agent.py`)**:
  - Class `DeliveryAgent`: Hàm `process(context: CaseContext, data_loader: DataLoader) -> CaseContext`.
  - Trích xuất timestamp từ order:
    - `delivered_at`: `order_delivered_customer_date` (chuỗi `YYYY-MM-DD HH:MM:SS` hoặc `None`).
    - `estimated_delivery_at`: `order_estimated_delivery_date`.
    - `carrier_handoff_at`: `order_delivered_carrier_date`.
  - **Tính độ lệch thời gian giao hàng (`delivery_variance_hours`)**:
    - Nếu có đủ `delivered_at` và `estimated_delivery_at`:
      - `diff_seconds = (delivered_at_dt - estimated_delivery_at_dt).total_seconds()`
      - `delivery_variance_hours = round(diff_seconds / 3600.0, 2)`
  - **Phân tích bàn giao theo Seller (`seller_handoff_analysis`)**:
    - Lấy items của order từ `data_loader.get_order_items(claimed_order_id)`.
    - Tạo dictionary gom `shipping_limit_date` sớm nhất theo từng `seller_id`:
      `seller_limits[seller_id] = min(shipping_limit_dates)`.
    - Với mỗi `seller_id`:
      - Nếu có `carrier_handoff_at` và `shipping_limit_at`:
        - `h_diff_seconds = (carrier_handoff_at_dt - shipping_limit_at_dt).total_seconds()`
        - `handoff_variance_hours = round(h_diff_seconds / 3600.0, 2)`
        - `late_handoff = handoff_variance_hours > 0`
      - Thêm vào `seller_handoff_analysis` object.
      - Nếu `late_handoff == True`, thêm `seller_id` vào `late_handoff_seller_ids`.
- [ ] **3.3 Verification**:
  - Chạy test độc lập `PaymentAgent` và `DeliveryAgent` để kiểm tra độ chính xác của các số float làm tròn 2 chữ số và cờ `late_handoff`.

---

## 📍 Bước 4: Person 4 — Policy & Reasoning Agent (EC_POLICY_V2 Engine)

> **Mục tiêu**: Xây dựng bộ não đưa ra quyết định chính sách `EC_POLICY_V2`, phân định nguyên nhân gốc, bên chịu trách nhiệm, khoản refund và quy trình action.

### 📁 Tệp tin phụ trách:
- `src/agents/policy_agent.py`

### 🔗 Input Handoff từ Person 2 & 3:
- Nhận `CaseContext` chứa đầy đủ thông tin domain từ Customer, Order, Payment và Delivery Agent.

### 📋 Checklist chi tiết:
- [x] **4.1 Áp dụng Quy Tắc Primary Issue (Thứ tự ưu tiên tuyệt đối 1 -> 6)**:
  - **Rule 1 (`canceled_order_paid`)**:
    - *Điều kiện*: `context.flags.order_status == "canceled"` VÀ `payment_total_brl > 0`.
    - *Primary Issue*: `canceled_order_paid`
    - *Cause Code*: `ORDER_CANCELED_AFTER_PAYMENT`
    - *Responsible Party*: `party_type="platform"`, `party_id="OLIST_PLATFORM"`
    - *Refund*: `payment_total_brl`
    - *Main Action*: `issue_full_refund`
  - **Rule 2 (`unavailable_order_paid`)**:
    - *Điều kiện*: `context.flags.order_status == "unavailable"` VÀ `payment_total_brl > 0`.
    - *Primary Issue*: `unavailable_order_paid`
    - *Cause Code*: `ORDER_UNAVAILABLE_AFTER_PAYMENT`
    - *Responsible Party*: `party_type="platform"`, `party_id="OLIST_PLATFORM"`
    - *Refund*: `payment_total_brl`
    - *Main Action*: `issue_full_refund`
  - **Rule 3 (`late_delivery_seller`)**:
    - *Điều kiện*: Giao muộn (`delivery_variance_hours > 0`) VÀ `len(late_handoff_seller_ids) > 0`.
    - *Primary Issue*: `late_delivery_seller`
    - *Cause Code*: `SELLER_HANDOFF_AFTER_LIMIT`
    - *Responsible Party*: `party_type="seller"`, `party_id=sid` cho từng seller trong `late_handoff_seller_ids`.
    - *Refund*: `freight_total_brl`
    - *Main Action*: `refund_freight`
  - **Rule 4 (`late_delivery_logistics`)**:
    - *Điều kiện*: Giao muộn (`delivery_variance_hours > 0`) VÀ `len(late_handoff_seller_ids) == 0`.
    - *Primary Issue*: `late_delivery_logistics`
    - *Cause Code*: `CARRIER_DELIVERED_AFTER_ESTIMATE`
    - *Responsible Party*: `party_type="logistics_provider"`, `party_id="LOGISTICS_PROVIDER"`
    - *Refund*: `freight_total_brl`
    - *Main Action*: `refund_freight`
  - **Rule 5 (`valid_split_payment`)**:
    - *Điều kiện*: `context.flags.split_payment == True` VÀ `payment_reconciliation.reconciled == True` (VÀ không bị trúng Rule 1-4).
    - *Primary Issue*: `valid_split_payment`
    - *Cause Code*: `MULTIPLE_PAYMENTS_RECONCILED`
    - *Responsible Party*: Không có (`responsible_parties = []`)
    - *Refund*: `0.0`
    - *Main Action*: `explain_valid_split_payment`
  - **Rule 6 (`unsupported_late_claim`)**:
    - *Điều kiện*: Không thuộc các trường hợp trên (Giao đúng hạn/sớm hạn và payment khớp).
    - *Primary Issue*: `unsupported_late_claim`
    - *Cause Code*: `DELIVERY_WITHIN_ESTIMATE`
    - *Responsible Party*: Không có (`responsible_parties = []`)
    - *Refund*: `0.0`
    - *Main Action*: `reject_late_refund`
- [x] **4.2 Xác Định Secondary Issues (Thêm lần lượt theo đúng thứ tự)**:
  Khởi tạo `secondary_issues = []`. Check theo thứ tự:
  1. `multi_item_order`: nếu `context.flags.multi_item_order == True`
  2. `multi_seller_order`: nếu `context.flags.multi_seller_order == True`
  3. `split_payment`: nếu `context.flags.split_payment == True`
  4. `repeat_customer`: nếu `context.flags.repeat_customer == True`
  5. `multiple_categories`: nếu `context.flags.multiple_categories == True`
- [x] **4.3 Xây Dựng Evidence IDs (Thứ tự định sẵn)**:
  Tạo danh sách `evidence_ids`:
  1. `f"order:{claimed_order_id}"`
  2. Từng item: `f"item:{claimed_order_id}:{item_seq}"`
  3. Từng payment: `f"payment:{claimed_order_id}:{payment_seq}"`
  4. Từng seller chịu trách nhiệm (nếu có): `f"seller:{seller_id}"`
  5. Policy: `f"policy:{cause_code}"`
- [x] **4.4 Xây Dựng Resolution Actions Bổ Sung**:
  - Bắt đầu bằng `Main Action`.
  - Nếu primary issue thuộc seller late delivery: thêm `"review_seller_handoff"`.
  - Nếu primary issue thuộc carrier late delivery: thêm `"review_carrier_delay"`.
  - Nếu `recommended_refund_brl > 0`: thêm `"verify_refund_completion"`.
  - Nếu `context.flags.multi_seller_order == True`: thêm `"coordinate_multi_seller_case"`.
  - Nếu `context.flags.split_payment == True` VÀ `primary_issue != "valid_split_payment"`: thêm `"verify_payment_allocation"`.
- [x] **4.5 Set Status & Confidence**:
  - `case_status`: `"action_required"` nếu `recommended_refund_brl > 0`, ngược lại `"no_action"`.
  - `confidence`: `0.95`.
- [x] **4.6 Verification**:
  - Test `PolicyAgent` trên 6 kịch bản ứng với 6 primary issues để đảm bảo kết quả chính xác 100%.

---

## 📍 Bước 5: Person 5 — Coordinator, Verifier Agent, Orchestrator & Audit Artifacts

> **Mục tiêu**: Lắp ghép Pipeline (Coordinator), Kiểm soát giới hạn & Schema (Verifier), thực thi 50 cases (`main.py`) và tạo các tệp tin báo cáo/metadata.

### 📁 Tệp tin phụ trách:
- `src/agents/coordinator_agent.py`
- `src/agents/verifier_agent.py`
- `main.py`
- `architecture.md`
- `metadata.json`
- `individual_5SoCuoiMHV_HoVaTen.md`

### 🔗 Input Handoff từ Person 4:
- Nhận `CaseContext` hoàn chỉnh từ `PolicyAgent`.

### 📋 Checklist chi tiết:
- [ ] **5.1 Verifier Agent (`src/agents/verifier_agent.py`)**:
  - Class `VerifierAgent`: Hàm `verify_and_export(context: CaseContext, output_dir: str, trace_file: str)`.
  - **Cắt lát giới hạn mảng (Max Limits Slicing)**:
    - `order_ids`: max 5
    - `item_ids`: max 5
    - `seller_ids`: max 3
    - `payment_ids`: max 5
    - `related_order_ids`: max 5
    - `product_ids`: max 5
    - `category_names`: max 5
    - `ranked_causes`: max 3
    - `responsible_parties`: max 3
    - `evidence_ids`: max 20
    - `resolution_actions`: max 5
  - **Kiểm tra Null Handling**:
    - Nếu `context.flags.has_items == False`: đảm bảo `item_total_brl`, `freight_total_brl`, `expected_total_brl`, `difference_brl`, `reconciled` đều là `None` (JSON xuất ra `null`).
  - **Làm tròn chữ số thập phân**: Ép kiểu `round(val, 2)` cho toàn bộ các thuộc tính tiền tệ và thời gian.
  - **Ghi log trace**: Append 1 dòng JSON vào `trace.jsonl` chứa `case_id`, `primary_issue`, `refund`, `timestamp`.
  - **Xuất JSON**: Ghi `output/{case_id}.json` đúng định dạng Output Schema.
- [ ] **5.2 Coordinator Agent (`src/agents/coordinator_agent.py`)**:
  - Class `CoordinatorAgent`: Hàm `run_case(input_case_path: str) -> dict`.
  - Đọc file JSON trong `input/`.
  - Khởi tạo `CaseContext`.
  - Thực thi chuỗi Handoff lần lượt:
    `CustomerAgent` $\rightarrow$ `OrderProductAgent` $\rightarrow$ `PaymentAgent` $\rightarrow$ `DeliveryAgent` $\rightarrow$ `PolicyAgent` $\rightarrow$ `VerifierAgent`.
- [ ] **5.3 Main Script (`main.py`)**:
  - Quét 50 file `EC_001.json` đến `EC_050.json` trong `input/`.
  - Gọi `CoordinatorAgent` xử lý từng file.
  - Tự động nén thư mục `output/` thành `output.zip` chứa đúng 50 file JSON.
- [ ] **5.4 Documentation & Artifacts**:
  - **`architecture.md`**: Viết sơ đồ Mermaid, liệt kê 7 Agent, quyền truy cập dữ liệu và cơ chế Handoff.
  - **`metadata.json`**: Khai báo đúng định dạng:
    ```json
    {
      "model_name": "Qwen/Qwen3-VL-8B-Instruct",
      "parameter_size": "8B",
      "framework": "Python 3.10+, Pydantic v2, Pandas",
      "runtime": "Linux / CUDA"
    }
    ```
  - **`individual_5SoCuoiMHV_HoVaTen.md`**: Viết báo cáo cá nhân tổng kết quá trình xây dựng hệ thống.
- [ ] **5.5 Final Check**: Run `python main.py`, kiểm tra `output.zip` giải nén ra đúng 50 file JSON, không thiếu trường nào.
