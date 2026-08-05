# Báo cáo cá nhân — Multi-Agent E-commerce Dispute Resolution

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | **CẦN NGƯỜI NỘP ĐIỀN** |
| MSSV | 5 số cuối: `01230` |
| Khóa/Lớp | K4 / E403 |
| Vai trò chính | Tích hợp pipeline, verifier và kiểm soát artifact nộp bài |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách tích hợp chuỗi handoff `CustomerAgent → OrderProductAgent →
PaymentAgent → DeliveryAgent → PolicyAgent → VerifierAgent`, kiểm tra tính nhất
quán của `CaseContext`, tạo 50 output và đóng gói artifact nộp bài.

| Module/deliverable | Input | Output | Trạng thái |
|---|---|---|---|
| Coordinator/LangGraph | Input case và DataLoader | CaseContext hoàn chỉnh | Hoàn thành |
| Verifier | CaseContext sau policy | JSON và trace đã kiểm tra | Hoàn thành |
| Submission builder | 50 input JSON | 50 output, trace và output.zip | Hoàn thành |
| Audit | Output và CSV Olist | Báo cáo đối chiếu độc lập | Hoàn thành |

## 3. Kết quả bàn giao

- Pipeline xử lý đủ `EC_001` đến `EC_050`.
- ZIP chứa chính xác `output/EC_001.json` đến `output/EC_050.json` và không có file lạ.
- Trace có đúng một dòng theo thứ tự cho mỗi case.
- Đối chiếu độc lập 50 output với CSV không phát hiện sai lệch.
- Test các bước 1–5 đạt 23/23 trước lượt hoàn thiện submission.

## 4. Giải thích kỹ thuật

Mỗi agent chỉ sở hữu một domain dữ liệu và ghi kết quả vào `CaseContext`.
Customer Agent xác định khách hàng; Order/Product Agent lấy item, seller và product;
Payment Agent đối soát tổng thanh toán; Delivery Agent tính độ trễ và seller handoff;
Policy Agent áp dụng sáu rule theo thứ tự ưu tiên tuyệt đối; Verifier kiểm tra schema,
giới hạn, null handling, consistency và xuất artifact.

Policy được triển khai rule-based để kết quả có thể tái lập và truy nguyên trực tiếp
từ CSV. `meta-llama/Llama-3.1-8B-Instruct` (8B) chỉ là enrichment tùy chọn, không được dùng để quyết định primary
issue, responsible party hoặc refund trong đường submission.

### Contract

| Thành phần | Mô tả |
|---|---|
| Input | JSON case chứa `case_id`, `claimed_order_id`, scope và `EC_POLICY_V2` |
| Shared state | Pydantic `CaseContext` |
| Output | JSON theo schema README, trace JSONL và ZIP |
| Data source | 9 CSV Olist; pipeline truy vấn các bảng cần cho policy |
| Lỗi cần chặn | Thiếu case, sai policy, thiếu CSV, trace lặp, ZIP sai manifest |

### Cách xác minh

```bash
pytest -q
python main.py
python verify_submission.py
```

Kết quả mong đợi là toàn bộ test đạt, có đúng 50 output, 50 trace và ZIP vượt
kiểm tra manifest lẫn CRC.

## 5. Quyết định kỹ thuật quan trọng

Quyết định quan trọng nhất là tách LLM khỏi đường quyết định policy mặc định.
Phương án gọi LLM cho mọi case có ưu điểm tạo diễn giải tự nhiên nhưng phụ thuộc
mạng, quota và có thể không deterministic. Phương án rule-based bám chính xác
`EC_POLICY_V2`, nhanh và kiểm chứng được. Vì leaderboard chấm các trường dữ liệu
có ground truth, pipeline chọn rule-based làm nguồn quyết định; LLM chỉ bật khi
cần phần giải thích bổ sung.

## 6. Lỗi đã xử lý

Triệu chứng là hệ thống chấm báo ZIP không chứa đúng
`output/EC_001.json` đến `output/EC_050.json`. Nguyên nhân là quy trình đóng gói
không có quality gate đủ mạnh và có thể nộp nhầm artifact cũ. Submission builder
được đổi sang staging sạch, bắt buộc đúng bộ 50 tên file, kiểm tra trace, manifest,
CRC và parse từng JSON trong ZIP trước khi thay artifact chính.

Một lỗi khác là trace bị append thành 51 dòng với `EC_001` lặp. Test và full run
cần dùng trace riêng; full submission hiện tạo trace mới trong staging nên mỗi run
chỉ giữ lượt chạy mới nhất.

## 7. Hiểu biết luồng end-to-end

Input case cung cấp order ID. DataLoader dùng các index để join order với customer,
items, payments và products. Các extraction agent lần lượt bổ sung facts vào
`CaseContext`. Policy Agent đọc facts, áp dụng rule ưu tiên và tạo assessment,
root cause, refund, evidence cùng actions. Verifier kiểm tra consistency và giới
hạn trước khi ghi output. Main chỉ công bố artifact khi đủ 50 case và toàn bộ ZIP
đạt kiểm tra integrity.

## 8. Cam kết

- [x] Nội dung kỹ thuật phản ánh pipeline và kết quả kiểm chứng thực tế.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Các kết quả được gắn với lệnh hoặc artifact có thể tái hiện.
- [ ] Họ tên và MSSV đầy đủ đã được người nộp xác nhận (đã xác nhận 5 số cuối `01230`, lớp `E403`).

**Người nộp cần điền hai trường nhận dạng ở Mục 1 trước khi commit cuối.**
