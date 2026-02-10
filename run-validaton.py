#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def run_capture(cmd, label: str) -> subprocess.CompletedProcess:
    print(f"\n--- {label} ---")
    print(" ".join(cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.stderr.strip():
        print(cp.stderr, file=sys.stderr)
    return cp


def run(cmd, label: str) -> None:
    cp = run_capture(cmd, label)
    if cp.stdout.strip():
        print(cp.stdout)
    if cp.returncode != 0:
        sys.exit(cp.returncode)


def require_file(path: str, label: str) -> None:
    if not os.path.exists(path):
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Merge TBox + ABox, reason with ROBOT/HermiT, "
            "and run a SPARQL report query (results printed to stdout)."
        )
    )

    p.add_argument(
        "--robot",
        default="robot.jar",
        help="Path to robot.jar (default: robot.jar)",
    )
    p.add_argument(
        "--reasoner",
        default="hermit",
        help="Reasoner to use with ROBOT (default: hermit)",
    )
    p.add_argument(
        "--tbox",
        default="ho61508-h2ho-inferred.ttl",
        help="TBox ontology file (default: ho61508-h2ho-inferred.ttl)",
    )
    p.add_argument(
        "--abox",
        default="nyhkb.ttl",
        help="ABox knowledge base file (default: nyhkb.ttl)",
    )
    p.add_argument(
        "--query",
        required=True,
        help="SPARQL query file (SELECT query recommended)",
    )
    p.add_argument(
        "--workdir",
        default=".",
        help="Directory for intermediate outputs (default: .)",
    )
    p.add_argument(
        "--merged-out",
        default="kb-merged.ttl",
        help="Merged TBox+ABox output file (default: kb-merged.ttl)",
    )
    p.add_argument(
        "--inferred-out",
        default="kb-inferred.ttl",
        help="Reasoned output file (default: kb-inferred.ttl)",
    )
    p.add_argument(
        "--skip-reasoning",
        action="store_true",
        help="Skip reasoning step (query runs on merged graph)",
    )

    args = p.parse_args()

    require_file(args.robot, "robot.jar")
    require_file(args.tbox, "TBox file")
    require_file(args.abox, "ABox file")
    require_file(args.query, "SPARQL query file")

    merged_path = os.path.join(args.workdir, args.merged_out)
    inferred_path = os.path.join(args.workdir, args.inferred_out)

    # 1) Merge TBox + ABox
    run(
        [
            "java", "-jar", args.robot,
            "merge",
            "--input", args.tbox,
            "--input", args.abox,
            "--output", merged_path,
        ],
        "MERGE (TBOX + ABOX)",
    )

    # 2) Reason (materialise inferred types)
    target = merged_path
    if not args.skip_reasoning:
        run(
            [
                "java", "-jar", args.robot,
                "reason",
                "--input", merged_path,
                "--reasoner", args.reasoner,
                "--output", inferred_path,
            ],
            f"REASON ({args.reasoner})",
        )
        target = inferred_path
    else:
        print("\n--- SKIPPING REASONING (query runs on merged graph) ---")

    # 3) Run SPARQL report query (print results to stdout)
    cp = run_capture(
        [
            "java", "-jar", args.robot,
            "query",
            "--input", target,
            "--query", args.query,
        ],
        f"QUERY (REPORT): {os.path.basename(args.query)}",
    )

    if cp.stdout.strip():
        print(cp.stdout)

    if cp.returncode != 0:
        sys.exit(cp.returncode)

    print("\n✅ QUERY EXECUTED")


if __name__ == "__main__":
    main()
