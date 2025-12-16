import subprocess
import sys
import os
import argparse
import glob

ONTOLOGY = "ho61508-h2ho-merged.ttl"
INFERRED = "ho61508-h2ho-inferred.ttl"
TEST_DIR = "tests"
TEST_PATTERN = "*test.sparql"


def run(cmd, label):
    print(f"\n--- {label} ---")
    print(cmd if isinstance(cmd, str) else " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str)
    )
    print(result.stdout)
    if result.stderr.strip():
        print(result.stderr)
    if result.returncode != 0:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run ontology reasoning and tests")
    parser.add_argument(
        "--skip-reasoning",
        action="store_true",
        help="Skip the reasoning step and use existing inferred ontology"
    )
    args = parser.parse_args()

    print("Running ontology tests...\n")

    # 1. Merge + Reason (optional)
    if not args.skip_reasoning:
        run("merge-ontologies.sh", "MERGING ONTOLOGIES")
        run(
            [
                "java", "-jar", "robot.jar",
                "reason",
                "--input", ONTOLOGY,
                "--reasoner", "hermit",
                "--output", INFERRED
            ],
            "REASONING"
        )
    else:
        if not os.path.exists(INFERRED):
            print(f"ERROR: {INFERRED} does not exist, cannot skip reasoning.")
            sys.exit(1)
        print(f"\n--- SKIPPING REASONING (using {INFERRED}) ---")

    # 2. Discover tests
    test_files = sorted(
        glob.glob(os.path.join(TEST_DIR, TEST_PATTERN))
    )

    if not test_files:
        print(f"ERROR: No test files matching {TEST_PATTERN} found in {TEST_DIR}/")
        sys.exit(1)

    print(f"\nDiscovered {len(test_files)} test(s):")
    for t in test_files:
        print(f"  - {t}")

    # 3. Run tests
    for test in test_files:
        run(
            [
                "java", "-jar", "robot.jar",
                "verify",
                "--input", INFERRED,
                "--queries", test
            ],
            f"TEST: {test}"
        )

    print("\n✅ ALL TESTS PASSED")


if __name__ == "__main__":
    main()

