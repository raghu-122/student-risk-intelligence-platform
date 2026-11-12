#!/usr/bin/env python3
"""
Reproducibility verification: runs generate_data.py twice with the same seed
and verifies that file checksums are identical.
"""
import subprocess, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

def run_gen(seed):
    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "generate_data.py"), "--scale", "starter", "--seed", str(seed)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr); sys.exit(1)
    man_path = ROOT / "data" / "manifests" / "manifest.json"
    with open(man_path) as f:
        return json.load(f)

print("Run 1...")
m1 = run_gen(20261022)
print("Run 2...")
m2 = run_gen(20261022)

mismatches = []
for fname, chk1 in m1["file_checksums"].items():
    chk2 = m2["file_checksums"].get(fname)
    if chk1 != chk2:
        mismatches.append({"file": fname, "run1": chk1, "run2": chk2})

if mismatches:
    print(f"\n❌ REPRODUCIBILITY FAILED — {len(mismatches)} file(s) differ:")
    for m in mismatches:
        print(f"   {m['file']}: {m['run1']} != {m['run2']}")
    sys.exit(1)
else:
    print(f"\n✅ REPRODUCIBILITY VERIFIED — all {len(m1['file_checksums'])} files are identical across both runs")
    print(f"   Seed: {m1['seed']}, Scale: {m1['scale']}, Files checked: {len(m1['file_checksums'])}")

