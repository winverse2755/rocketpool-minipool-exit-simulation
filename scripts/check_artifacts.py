"""Check published file hashes or the seven deterministic simulation CSVs."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_hashes(root: Path, expected: dict[str, str]) -> list[str]:
    failures = []
    for name, digest in expected.items():
        path = root / name
        if not path.is_file():
            failures.append(f"Missing: {name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append(f"Changed: {name}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rerun", action="store_true",
        help="compare regenerated CSVs with the published reproducibility record",
    )
    args = parser.parse_args()
    if args.rerun:
        record = json.loads((ROOT / "results/reproducibility.json").read_text())
        expected = record["rerun_csv_bytes_identical"]
    else:
        expected = json.loads((ROOT / "results/sha256_manifest.json").read_text())
    if not expected:
        raise SystemExit("No hashes found; verification cannot succeed.")
    failures = check_hashes(ROOT, expected)
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"PASS: {len(expected)} file hashes match.")


if __name__ == "__main__":
    main()
