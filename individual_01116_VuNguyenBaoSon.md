# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                                           |
| --------------- | -------------------------------------------------------------------------------------------------- |
| Họ và tên       | Vũ Nguyễn Bảo Sơn                                                                                  |
| MSSV            | 01116                                                                                              |
| Khóa/Lớp        | K4                                                                                                 |
| Vai trò chính   | Person 2 — Domain Extraction Agents Part 1 (Customer Agent, Order-Product Agent & Data Engine Foundation) |
| Ngày hoàn thành | 2026-08-05                                                                                         |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Config & Data Engine** | [`src/config.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/config.py), [`src/data_loader.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/data_loader.py) | `.env`, các tệp Olist CSV trong `data/` | Class `DataLoader` với hệ thống Index Map tra cứu $O(1)$ | Hoàn thành |
| **Data Contract Schemas** | [`src/schemas.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/schemas.py) | Cấu trúc dữ liệu theo spec `AGENTS.md` | Đối tượng `CaseContext` và các sub-models Pydantic | Hoàn thành |
| **Customer Agent** | [`src/agents/customer_agent.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/agents/customer_agent.py) | `CaseContext`, `DataLoader` | `context.customer_context`, `flags.repeat_customer` | Hoàn thành |
| **Order & Product Agent** | [`src/agents/order_product_agent.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/agents/order_product_agent.py) | `CaseContext`, `DataLoader` | `affected_entities`, `product_context`, `payment_reconciliation` (expected_total_brl), `flags` | Hoàn thành |
| **Step 2 Unit Verification** | [`test_step2.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/test_step2.py) | Tệp mẫu `EC_001.json` | Log xác minh dữ liệu trích xuất và cờ logic | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| Handoff Contract Standards | Person 3 (Payment & Delivery Agent), Person 4 (Policy Agent) | Đảm bảo tính nhất quán thuộc tính trong `CaseContext` và `expected_total_brl` giúp Person 3 thực hiện Reconciliation chính xác. |
| Môi trường & Dependency Setup | Toàn đội ngũ | Khởi tạo file `.env`, cập nhật `.gitignore`, tạo môi trường ảo Python `venv` và cài đặt các thư viện `pydantic`, `pandas`, `python-dotenv`. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Trích xuất thông tin khách hàng | `CustomerAgent.process()` | `CustomerContext` chứa `customer_unique_id`, tối đa 5 `related_order_ids`, cờ `repeat_customer` | Exec `.\venv\Scripts\python test_step2.py` |
| Phân tích đơn hàng & sản phẩm | `OrderProductAgent.process()` | `item_ids`, `seller_ids`, `product_ids`, `category_names`, tính toán tài chính (`expected_total_brl`), các cờ `multi_item_order`, `multi_seller_order`, `multiple_categories` | Exec `.\venv\Scripts\python test_step2.py` |
| Quản lý nạp dữ liệu Olist | `DataLoader._load_data()` | Nạp 9 CSV và xây dựng HashMap tra cứu $O(1)$ | Đã chạy thử nghiệm đạt tốc độ tra cứu tức thì |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng lớp trích xuất tri thức đầu tiên (Domain Extraction Part 1) từ các tệp dữ liệu CSV gốc của sàn thương mại điện tử Olist thành một đối tượng hợp đồng dữ liệu chuẩn hóa (`CaseContext`).

### Cách triển khai
1. **`DataLoader`**: Đọc toàn bộ các CSV khi khởi tạo và gom nhóm theo Dictionary Index (`orders_by_id`, `customers_by_id`, `customer_orders_map`, `items_by_order`, `products_by_id`, `category_translation`).
2. **`CustomerAgent`**:
   - Lấy `customer_id` từ `claimed_order_id`.
   - Lấy `customer_unique_id` và truy xuất danh sách các order trong quá khứ (loại trừ `claimed_order_id`), giới hạn tối đa 5 order.
   - Bật cờ `context.flags.repeat_customer = len(related_order_ids) > 0`.
3. **`OrderProductAgent`**:
   - Đọc danh sách mặt hàng (`items`) thuộc `claimed_order_id`.
   - Nếu không có items: bật `has_items = False`, gán các danh sách thực thể rỗng và tiền tệ thành `None`.
   - Nếu có items: bật `has_items = True`, trích xuất `item_ids` (tối đa 5), `seller_ids` duy nhất (tối đa 3), `product_ids` (tối đa 5), dịch `category_names` sang tiếng Anh (tối đa 5).
   - Tính toán tiền tệ: `item_total_brl`, `freight_total_brl`, và `expected_total_brl = round(item_total_brl + freight_total_brl, 2)`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | `CaseContext` chứa `case_id`, `customer_request`, `claimed_order_id` |
| Output | `CaseContext` đã điền đầy đủ `customer_context`, `product_context`, `affected_entities`, `expected_total_brl`, và các cờ trong `flags` |
| Module phụ thuộc | `src/config.py`, `src/schemas.py`, `src/data_loader.py` |
| Module sử dụng output | `PaymentAgent` (Bước 3), `DeliveryAgent` (Bước 3), `PolicyAgent` (Bước 4) |

### Cách xác minh

```bash
.\venv\Scripts\python test_step2.py
```

- **Kết quả mong đợi:** Mã thoát code 0. `CaseContext` được điền đầy đủ thông tin khách hàng, chi tiết đơn hàng, tổng tiền kỳ vọng và các cờ phân loại chính xác.
- **Kết quả thực tế:**
  ```text
  Case ID: EC_001, Claimed Order ID: 9b75cdaf2d85857ef023980e15d01546
  Customer Context: customer_unique_id='bbf65e7823171a84e70a495dd6c34ceb' related_order_ids=['65bbd0719855fe808bb19f62dfa9f42c']
  Repeat Customer Flag: True
  Order Status: delivered | Has Items: True
  Affected Order IDs: ['9b75cdaf2d85857ef023980e15d01546']
  Affected Item IDs: ['9b75cdaf2d85857ef023980e15d01546:1', '9b75cdaf2d85857ef023980e15d01546:2']
  Item Total BRL: 220.64 | Freight Total BRL: 16.7 | Expected Total BRL: 237.34
  ```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tra cứu dữ liệu khách hàng và sản phẩm từ các tệp CSV dung lượng lớn cho 50 case điều tra mà vẫn đảm bảo hiệu năng và thời gian phản hồi nhanh.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Mỗi lần một Agent chạy lại thực hiện `pandas.read_csv()` để tìm kiếm dòng dữ liệu tương ứng.
  2. *Phương án B*: Khởi tạo class `DataLoader` duy nhất, nạp dữ liệu một lần vào bộ nhớ và tạo sẵn các chỉ mục dạng Hash Table / Dictionary (`dict`).
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Giảm thời gian tra cứu từ $O(N)$ xuống $O(1)$, tránh việc đọc/ghi đĩa I/O lặp lại nhiều lần, giúp toàn bộ pipeline chạy 50 cases chỉ trong vài giây.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  pydantic_core._pydantic_core.ValidationError: 1 validation error for CaseContext
  claimed_order_id
    Field required [type=missing, input_value={'case_id': 'EC_001', 'customer_request': {...}}, input_type=dict]
  ```
- **Lệnh tái hiện:** `.\venv\Scripts\python test_step2.py`
- **Nguyên nhân gốc:** Tệp JSON đầu vào (`EC_001.json`) đặt trường `claimed_order_id` bên trong dictionary `customer_request` chứ không nằm trực tiếp ở cấp cao nhất của object JSON.
- **Cách xử lý:** Đặt giá trị mặc định `claimed_order_id: str = ""` và thêm `@model_validator(mode='after')` vào `CaseContext` trong [`src/schemas.py`](file:///c:/Users/LENOVO/K4-Day9-Multi-Agent-A2A/src/schemas.py) để tự động trích xuất `claimed_order_id` từ `customer_request["claimed_order_id"]` nếu trường này chưa được khởi tạo.
- **Cách xác minh sau khi sửa:** Chạy lại `test_step2.py` thành công với exit code 0.

---

## 7. Hiểu biết về luồng end-to-end

1. **Luồng dữ liệu trong hệ thống**: Dữ liệu khiếu nại (Case JSON) từ thư mục `input/` được nạp vào hệ thống $\rightarrow$ `CoordinatorAgent` khởi tạo `CaseContext` $\rightarrow$ `CustomerAgent` trích xuất thông tin khách hàng $\rightarrow$ `OrderProductAgent` phân tích sản phẩm và tính `expected_total_brl` $\rightarrow$ `PaymentAgent` & `DeliveryAgent` làm rõ đối soát và thời gian bàn giao $\rightarrow$ `PolicyAgent` quyết định quy tắc hoàn tiền & bên chịu trách nhiệm $\rightarrow$ `VerifierAgent` định dạng và xuất JSON ra thư mục `output/`.
2. **Vai trò của Data Contract**: `CaseContext` là bản giao ước chung (Handoff Schema). Người làm sau phụ thuộc hoàn toàn vào dữ liệu do người làm trước điền vào `CaseContext`.
3. **Mục đích của việc kiểm thử từng bước (Unit Verification)**: Đảm bảo từng Agent thực hiện đúng nhiệm vụ trích xuất dữ liệu của mình trước khi lắp ghép vào pipeline tổng, giúp khoanh vùng lỗi nhanh chóng.

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Nguyễn Bảo Sơn  
**MSSV (5 số cuối):** 01116  
**Ngày xác nhận:** 2026-08-05
