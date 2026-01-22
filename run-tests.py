import argparse
import glob
import os
import subprocess
import sys
from typing import List

ONTOLOGY = "ho61508-h2ho-merged.ttl"
INFERRED = "ho61508-h2ho-inferred.ttl"
TEST_DIR = "tests"
TEST_PATTERN = "*test.sparql"


def run(cmd, label: str) -> None:
    print(f"\n--- {label} ---")
    print(cmd if isinstance(cmd, str) else " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str),
    )
    if result.stdout.strip():
        print(result.stdout)
    if result.stderr.strip():
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)


def discover_all_tests() -> List[str]:
    return sorted(glob.glob(os.path.join(TEST_DIR, TEST_PATTERN)))


def normalize_and_validate_tests(tests: List[str]) -> List[str]:
    normalized: List[str] = []
    for t in tests:
        # Keep user-provided path as-is, but normalize for filesystem checks
        t_norm = os.path.normpath(t)
        if not os.path.exists(t_norm):
            print(f"ERROR: Test file not found: {t}", file=sys.stderr)
            sys.exit(1)
        normalized.append(t_norm)
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ontology reasoning and tests")
    parser.add_argument(
        "--skip-reasoning",
        action="store_true",
        help="Skip the reasoning step and use existing inferred ontology",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Run all tests matching {TEST_PATTERN} in {TEST_DIR}/",
    )
    parser.add_argument(
        "tests",
        nargs="*",
        help="Specific test .sparql files to run (e.g., tests/my-test.sparql). "
             "If omitted, all tests are run (same as --all).",
    )
    args = parser.parse_args()

    print("Running ontology tests...\n")

    # 1) Merge + Reason (optional)
    if not args.skip_reasoning:
        run("merge-ontologies.sh", "MERGING ONTOLOGIES")
        run(
            [
                "java", "-jar", "robot.jar",
                "reason",
                "--input", ONTOLOGY,
                "--reasoner", "hermit",
                "--output", INFERRED,
            ],
            "REASONING",
        )
    else:
        if not os.path.exists(INFERRED):
            print(f"ERROR: {INFERRED} does not exist, cannot skip reasoning.", file=sys.stderr)
            sys.exit(1)
        print(f"\n--- SKIPPING REASONING (using {INFERRED}) ---")

    # 2) Decide which tests to run
    if args.tests and args.all:
        print("ERROR: Provide specific test files OR use --all, not both.", file=sys.stderr)
        sys.exit(1)

    if args.tests:
        test_files = normalize_and_validate_tests(args.tests)
    else:
        # No explicit tests -> run all (also covers --all)
        test_files = discover_all_tests()
        if not test_files:
            print(f"ERROR: No test files matching {TEST_PATTERN} found in {TEST_DIR}/", file=sys.stderr)
            sys.exit(1)

    print(f"\nSelected {len(test_files)} test(s):")
    for t in test_files:
        print(f"  - {t}")

    # 3) Run tests
    for test in test_files:
        run(
            [
                "java", "-jar", "robot.jar",
                "verify",
                "--input", INFERRED,
                "--queries", test,
            ],
            f"TEST: {test}",
        )

    print("\n✅ ALL TESTS PASSED")


if __name__ == "__main__":
    main()
