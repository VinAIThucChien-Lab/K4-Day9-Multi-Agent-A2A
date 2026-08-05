"""Verify data/ and input/ are correctly loaded."""
import json, glob, os, csv

print("=" * 60)
print("DATA DIRECTORY CHECK")
print("=" * 60)
data_dir = "data"
data_files = sorted(os.listdir(data_dir))
for fn in data_files:
    fp = os.path.join(data_dir, fn)
    size = os.path.getsize(fp)
    # Count rows if CSV
    if fn.endswith(".csv"):
        with open(fp, encoding="utf-8-sig") as f:
            rows = sum(1 for _ in f) - 1  # minus header
        print(f"  {fn}: {rows:,} rows ({size:,} bytes)")
    else:
        print(f"  {fn}: {size:,} bytes")

print()
print("=" * 60)
print("INPUT DIRECTORY CHECK")
print("=" * 60)
input_files = sorted(glob.glob(os.path.join("input", "input", "EC_*.json")))
print(f"  Files found: {len(input_files)}")
for fp in input_files[:3]:
    with open(fp, encoding="utf-8") as f:
        d = json.load(f)
    oid = d["customer_request"]["claimed_order_id"]
    print(f"  {os.path.basename(fp)}: order_id = {oid}")
print(f"  ...")

print()
print("=" * 60)
print("OUTPUT vs INPUT ORDER ID MATCH")
print("=" * 60)
mismatch = 0
missing_output = 0
for fp in input_files:
    case = os.path.basename(fp).replace(".json", "")
    out_fp = os.path.join("output", f"{case}.json")
    if not os.path.exists(out_fp):
        print(f"  {case}: OUTPUT MISSING")
        missing_output += 1
        continue
    with open(fp, encoding="utf-8") as f:
        inp = json.load(f)
    with open(out_fp, encoding="utf-8") as f:
        out = json.load(f)
    claimed = inp["customer_request"]["claimed_order_id"]
    actual = out["affected_entities"]["order_ids"][0] if out["affected_entities"]["order_ids"] else None
    if claimed != actual:
        print(f"  {case}: MISMATCH! input={claimed}, output={actual}")
        mismatch += 1

print(f"  Missing outputs: {missing_output}")
print(f"  Mismatched order IDs: {mismatch}")
if mismatch == 0 and missing_output == 0:
    print("  All 50 output order_ids match inputs CORRECTLY!")

print()
print("=" * 60)
print("OUTPUT PRIMARY ISSUE DISTRIBUTION")
print("=" * 60)
from collections import Counter
issues = Counter()
for i in range(1, 51):
    fp = os.path.join("output", f"EC_{i:03d}.json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        pi = d["case_assessment"]["primary_issue"]
        dv = d["delivery_analysis"]["delivery_variance_hours"]
        issues[pi] += 1

for issue, count in issues.most_common():
    print(f"  {issue}: {count} cases")

print()
print("=" * 60)
print("SPOT CHECK: Cases with negative delivery_variance but non-no_action")
print("=" * 60)
bugs = 0
for i in range(1, 51):
    fp = os.path.join("output", f"EC_{i:03d}.json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        da = d.get("delivery_analysis", {})
        dv = da.get("delivery_variance_hours", 0)
        pi = d["case_assessment"]["primary_issue"]
        order_status = None
        # Get order status from data
        inp_fp = os.path.join("input", "input", f"EC_{i:03d}.json")
        if os.path.exists(inp_fp):
            with open(inp_fp, encoding="utf-8") as f:
                inp = json.load(f)
            oid = inp["customer_request"]["claimed_order_id"]
        
        if dv is not None and dv <= 0 and pi in ("late_delivery_seller", "late_delivery_logistics"):
            print(f"  EC_{i:03d}: variance={dv}, but primary_issue={pi} -> BUG!")
            bugs += 1

if bugs == 0:
    print("  No bugs found in delivery logic.")
else:
    print(f"  Total bugs: {bugs}")
