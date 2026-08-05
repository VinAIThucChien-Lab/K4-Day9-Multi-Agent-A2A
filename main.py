"""Main orchestration script for running 50 dispute cases and archiving outputs."""

import os
import glob
import zipfile
from src.config import INPUT_DIR, OUTPUT_DIR
from src.data_loader import DataLoader
from src.agents.coordinator_agent import CoordinatorAgent


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    trace_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace.jsonl")
    if os.path.exists(trace_path):
        os.remove(trace_path)

    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "EC_*.json")))
    
    if not input_files:
        print(f"No input files found in {INPUT_DIR}")
        return

    print(f"Found {len(input_files)} input cases. Loading Olist CSV data...")
    data_loader = DataLoader()
    coordinator = CoordinatorAgent(data_loader=data_loader)

    for filepath in input_files:
        filename = os.path.basename(filepath)
        print(f"Processing {filename}...")
        coordinator.run_case(filepath)

    # Archive output directory into output.zip using shutil for proper directory entries
    import shutil
    zip_path = "output.zip"
    output_jsons = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
    
    # make_archive creates output.zip from the OUTPUT_DIR, but we want the zip to contain the folder "output/" itself.
    # To do this, we can zip the current directory but only include the "output" folder.
    # A robust way is to create a temporary folder structure or just use zipfile but explicitly add the directory.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Explicitly add the directory entry first
        zf.writestr(zipfile.ZipInfo("output/"), "")
        for json_file in output_jsons:
            arcname = f"output/{os.path.basename(json_file)}"
            zf.write(json_file, arcname=arcname)

    print(f"Successfully processed {len(output_jsons)} cases into {OUTPUT_DIR}/ and created {zip_path}.")


if __name__ == "__main__":
    main()
