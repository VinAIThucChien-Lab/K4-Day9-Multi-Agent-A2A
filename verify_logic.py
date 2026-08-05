import json
import os

input_dir = "input/input"
output_dir = "output"
cases = ["EC_001.json", "EC_002.json", "EC_003.json", "EC_004.json", "EC_005.json"]

print("="*60)
print("KIỂM TRA CHÉO 5 CASE ĐẦU TIÊN GIỮA INPUT VÀ OUTPUT")
print("="*60)

for case in cases:
    inp_path = os.path.join(input_dir, case)
    out_path = os.path.join(output_dir, case)
    
    with open(inp_path, 'r', encoding='utf-8') as f:
        inp = json.load(f)
        
    with open(out_path, 'r', encoding='utf-8') as f:
        out = json.load(f)
        
    print(f"\nCASE ID: {inp['case_id']}")
    print(f"1. Khách hàng khiếu nại (INPUT): {inp.get('customer_request', {}).get('message')}")
    print(f"2. Primary Issue LLM xác định (OUTPUT): {out.get('case_assessment', {}).get('primary_issue')}")
    print(f"3. Root Cause Code LLM đưa ra (OUTPUT): {out.get('root_cause_analysis', {}).get('ranked_causes', [{}])[0].get('cause_code')}")
    print(f"4. Đề xuất hoàn tiền (OUTPUT): {out.get('financial_resolution', {}).get('recommended_refund_brl')} BRL")
    print(f"5. Hành động LLM đề xuất (OUTPUT): {', '.join(out.get('resolution_actions', []))}")
    print("-"*60)
