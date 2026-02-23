#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from typing import List


def run_capture(cmd: List[str], label: str) -> subprocess.CompletedProcess:
    print(f"\n--- {label} ---")
    print(" ".join(cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.stderr.strip():
        print(cp.stderr, file=sys.stderr)
    return cp


def run_or_die(cmd: List[str], label: str) -> subprocess.CompletedProcess:
    cp = run_capture(cmd, label)
    if cp.stdout.strip():
        print(cp.stdout)
    if cp.returncode != 0:
        sys.exit(cp.returncode)
    return cp


def require_file(path: str, label: str) -> None:
    if not os.path.exists(path):
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Validate H2HO knowledge base: merge TBox + ABox, "
            "reason with ROBOT/HermiT, and run a SPARQL query."
        )
    )

    # --- Stable defaults (your canonical setup) ---

    p.add_argument(
        "--robot",
        default="robot.jar",
        help="Path to robot.jar (default: robot.jar)",
    )
    p.add_argument(
        "--reasoner",
        default="hermit",
        help="Reasoner to use (default: hermit)",
    )
    p.add_argument(
        "--tbox",
        default="h2ho-a.ttl",
        help="TBox ontology file (default: h2ho-a.ttl)",
    )
    p.add_argument(
        "--abox",
        default="nyhkb.ttl",
        help="ABox knowledge base file (default: nyhkb.ttl)",
    )
    p.add_argument(
        "--query",
        required=True,
        help="SPARQL SELECT query file",
    )

    # --- Outputs ---

    p.add_argument(
        "--merged-out",
        default="kb-merged.ttl",
        help="Merged ontology output (default: kb-merged.ttl)",
    )
    p.add_argument(
        "--inferred-out",
        default="kb-inferred.ttl",
        help="Reasoned ontology output (default: kb-inferred.ttl)",
    )
    p.add_argument(
        "--explain-md",
        default="kb-inconsistency.md",
        help="Markdown inconsistency explanation (default: kb-inconsistency.md)",
    )
    p.add_argument(
        "--explain-owl",
        default="kb-inconsistency.ttl",
        help="OWL inconsistency explanation (default: kb-inconsistency.ttl)",
    )

    p.add_argument(
        "--skip-reasoning",
        action="store_true",
        help="Skip reasoning (query runs on merged graph)",
    )

    args = p.parse_args()

    # --- Sanity checks ---

    require_file(args.robot, "robot.jar")
    require_file(args.tbox, "TBox")
    require_file(args.abox, "ABox")
    require_file(args.query, "SPARQL query")

    # --- Merge TBox + ABox ---

    merged_cmd = [
        "java", "-jar", args.robot,
        "merge",
        "--input", args.tbox,
        "--input", args.abox,
        "--output", args.merged_out,
    ]
    run_or_die(merged_cmd, "MERGE (TBOX + ABOX)")

    target = args.merged_out

    # --- Reasoning (Protégé-equivalent materialization) ---

    if not args.skip_reasoning:
        reason_cmd = [
            "java", "-jar", args.robot,
            "reason",
            "--input", args.merged_out,
            "--reasoner", args.reasoner,
            "--axiom-generators",
            "ClassAssertion", "PropertyAssertion",
            "--output", args.inferred_out,
        ]

        cp = run_capture(reason_cmd, f"REASON ({args.reasoner})")

        if cp.returncode != 0:
            if "inconsistent" in (cp.stderr or "").lower():
                print("\nOntology inconsistent. Generating explanation…", file=sys.stderr)

                explain_cmd = [
                    "java", "-jar", args.robot,
                    "explain",
                    "--input", args.merged_out,
                    "--reasoner", args.reasoner,
                    "-M", "inconsistency",
                    "--explanation", args.explain_md,
                    "--output", args.explain_owl,
                ]
                run_capture(explain_cmd, "EXPLAIN (INCONSISTENCY)")

            sys.exit(cp.returncode)

        if cp.stdout.strip():
            print(cp.stdout)

        target = args.inferred_out
    else:
        print("\n--- SKIPPING REASONING ---")

    # --- Run SPARQL query ---

    query_cmd = [
        "java", "-jar", args.robot,
        "query",
        "--input", target,
        "--query", args.query,
    ]

    cpq = run_capture(query_cmd, "QUERY")
    if cpq.stdout.strip():
        print(cpq.stdout)
    if cpq.returncode != 0:
        sys.exit(cpq.returncode)

    print("\n✅ VALIDATION COMPLETE")


if __name__ == "__main__":
    main()
