#!/usr/bin/env python3
"""Verify fixed-seed generation in isolated temporary directories."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_generation(scale: str, seed: int, output_dir: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_data.py"),
            "--scale",
            scale,
            "--seed",
            str(seed),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode:
        raise RuntimeError(f"Data generation failed:\n{result.stdout}\n{result.stderr}")
    manifest_path = output_dir / "manifests" / "manifest.json"
    with open(manifest_path, encoding="utf-8") as source:
        return json.load(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="student-risk-repro-") as temp:
        root = Path(temp)
        first = run_generation(args.scale, args.seed, root / "run-1")
        second = run_generation(args.scale, args.seed, root / "run-2")

    first_checksums = first["file_checksums"]
    second_checksums = second["file_checksums"]
    mismatches = {
        filename: (first_checksums.get(filename), second_checksums.get(filename))
        for filename in first_checksums.keys() | second_checksums.keys()
        if first_checksums.get(filename) != second_checksums.get(filename)
    }
    if mismatches or first["entity_counts"] != second["entity_counts"]:
        print(f"REPRODUCIBILITY FAILED: {len(mismatches)} file checksum mismatch(es)")
        for filename, (first_hash, second_hash) in sorted(mismatches.items()):
            print(f"  {filename}: {first_hash} != {second_hash}")
        if first["entity_counts"] != second["entity_counts"]:
            print("  Generated entity counts differ between runs")
        return 1

    print(
        f"REPRODUCIBILITY VERIFIED: scale={args.scale}, seed={args.seed}, "
        f"{len(first_checksums)} exported files identical"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
