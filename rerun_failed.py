"""Re-run only cases where LLM failed (confidence < 0.95 in output), sequentially."""
import os
import json
import glob
import zipfile
import time
from src.config import INPUT_DIR, OUTPUT_DIR
from src.data_loader import DataLoader
from src.agents.coordinator_agent import CoordinatorAgent


def find_failed_cases(output_dir: str) -> list[str]:
    """Find cases where confidence < 0.95 (LLM fallback was used)."""
    failed = []
    for json_file in sorted(glob.glob(os.path.join(output_dir, "EC_*.json"))):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            confidence = data.get("case_assessment", {}).get("confidence", 0.95)
            if confidence < 0.95:
                case_id = os.path.basename(json_file).replace(".json", "")
                failed.append(case_id)
                print(f"  Found failed case: {case_id} (confidence={confidence})")
        except Exception as e:
            print(f"  Error reading {json_file}: {e}")
    return failed


def main():
    print("=== Scanning for failed cases (confidence < 0.95) ===")
    failed_cases = find_failed_cases(OUTPUT_DIR)
    
    if not failed_cases:
        print("No failed cases found! All outputs have confidence >= 0.95.")
        return
    
    print(f"\nFound {len(failed_cases)} cases to re-run: {failed_cases}")
    print("Loading Olist CSV data...")
    data_loader = DataLoader()
    coordinator = CoordinatorAgent(data_loader=data_loader)

    print("\n=== Re-running failed cases sequentially ===")
    for case_id in failed_cases:
        input_path = os.path.join(INPUT_DIR, f"{case_id}.json")
        if not os.path.exists(input_path):
            print(f"  Input not found: {input_path}")
            continue
        print(f"  Re-processing {case_id}.json...")
        coordinator.run_case(input_path)
        time.sleep(0.5)  # Small delay between sequential calls

    # Re-create output.zip with updated files
    print("\n=== Recreating output.zip ===")
    zip_path = "output.zip"
    output_jsons = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for json_file in output_jsons:
            arcname = f"output/{os.path.basename(json_file)}"
            zf.write(json_file, arcname=arcname)
    
    print(f"Done! output.zip recreated with {len(output_jsons)} cases.")


if __name__ == "__main__":
    main()
