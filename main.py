"""Main orchestration script for running 50 dispute cases in parallel using ThreadPoolExecutor."""

import glob
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from src.config import BASE_DIR, INPUT_DIR, OUTPUT_DIR
from src.data_loader import DataLoader
from src.agents.coordinator_agent import CoordinatorAgent


def process_file(filepath: str, coordinator: CoordinatorAgent):
    filename = os.path.basename(filepath)
    print(f"Processing {filename}...")
    return coordinator.run_case(filepath)


def main():
    expected_names = [f"EC_{i:03d}.json" for i in range(1, 51)]
    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "EC_*.json")))
    actual_input_names = [os.path.basename(path) for path in input_files]
    if actual_input_names != expected_names:
        missing = sorted(set(expected_names) - set(actual_input_names))
        extra = sorted(set(actual_input_names) - set(expected_names))
        raise RuntimeError(
            f"Input set must be exactly EC_001.json..EC_050.json; "
            f"missing={missing}, extra={extra}"
        )

    print(f"Found {len(input_files)} input cases. Loading Olist CSV data...")
    data_loader = DataLoader()
    coordinator = CoordinatorAgent(data_loader=data_loader, enable_llm=True)

    staging_root = Path(tempfile.mkdtemp(prefix="submission-", dir=BASE_DIR))
    staging_output = staging_root / "output"
    staging_trace = staging_root / "trace.jsonl"
    staging_output.mkdir()
    try:
        for filepath, expected_name in zip(input_files, expected_names):
            print(f"Processing {expected_name}...")
            with open(filepath, "r", encoding="utf-8") as handle:
                case_data = json.load(handle)
            if case_data.get("case_id") != expected_name.removesuffix(".json"):
                raise RuntimeError(f"case_id does not match filename: {filepath}")
            if case_data.get("policy_version") != "EC_POLICY_V2":
                raise RuntimeError(f"Invalid policy_version in {filepath}")
            coordinator.run_case(
                filepath,
                output_dir=str(staging_output),
                trace_file=str(staging_trace),
            )

        output_jsons = sorted(staging_output.glob("*.json"))
        if [path.name for path in output_jsons] != expected_names:
            raise RuntimeError("Generated output set is not exactly EC_001.json..EC_050.json")

        trace_lines = staging_trace.read_text(encoding="utf-8").splitlines()
        trace_ids = [json.loads(line)["case_id"] for line in trace_lines]
        if trace_ids != [name.removesuffix(".json") for name in expected_names]:
            raise RuntimeError("Trace must contain exactly one ordered entry per case")

        staging_zip = staging_root / "output.zip"
        expected_manifest = [f"output/{name}" for name in expected_names]
        with zipfile.ZipFile(staging_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for json_file in output_jsons:
                archive.write(json_file, arcname=f"output/{json_file.name}")
        with zipfile.ZipFile(staging_zip, "r") as archive:
            if archive.namelist() != expected_manifest:
                raise RuntimeError("ZIP manifest does not match the required output paths")
            if archive.testzip() is not None:
                raise RuntimeError("ZIP integrity check failed")
            for name in expected_manifest:
                json.loads(archive.read(name))

        output_path = Path(OUTPUT_DIR)
        if output_path.exists():
            shutil.rmtree(output_path)
        shutil.move(str(staging_output), str(output_path))
        os.replace(staging_trace, Path(BASE_DIR) / "trace.jsonl")
        os.replace(staging_zip, Path(BASE_DIR) / "output.zip")
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    print("Successfully created 50 outputs, a clean trace, and verified output.zip.")


if __name__ == "__main__":
    main()
