#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from typing import List

from rdflib import Graph, URIRef


def run_capture(cmd: List[str], label: str) -> subprocess.CompletedProcess:
    print(f"\n--- {label} ---")
    print(" ".join(cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.stdout.strip():
        print(cp.stdout)
    if cp.stderr.strip():
        print(cp.stderr, file=sys.stderr)
    return cp


def run_or_die(cmd: List[str], label: str) -> subprocess.CompletedProcess:
    cp = run_capture(cmd, label)
    if cp.returncode != 0:
        sys.exit(cp.returncode)
    return cp


def require_file(path: str, label: str) -> None:
    if not os.path.exists(path):
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)


def materialize_inverse_properties(path_in: str, path_out: str) -> None:
    print("\n--- MATERIALIZE INVERSE PROPERTIES ---")
    print(f"Input:  {path_in}")
    print(f"Output: {path_out}")

    g = Graph()
    g.parse(path_in)

    HO = "https://w3id.org/jochumsson/ho61508#"
    H2HOA = "https://w3id.org/jochumsson/h2hoa#"

    inverse_pairs = [
        (URIRef(HO + "triggers"), URIRef(H2HOA + "triggeredBy")),
        (URIRef(HO + "inheresIn"), URIRef(HO + "inheres")),
        (URIRef(HO + "manifestsIn"), URIRef(HO + "manifestedBy")),
        (URIRef(HO + "causes"), URIRef(HO + "causedBy")),
        (URIRef(HO + "carriedBy"), URIRef(H2HOA + "carries")),
        (URIRef(HO + "affects"), URIRef(H2HOA + "affectedBy")),
    ]

    new_triples = set()

    for forward, inverse in inverse_pairs:
        for s, _, o in g.triples((None, forward, None)):
            new_triples.add((o, inverse, s))
        for s, _, o in g.triples((None, inverse, None)):
            new_triples.add((o, forward, s))

    added = 0
    for triple in new_triples:
        if triple not in g:
            g.add(triple)
            added += 1

    g.serialize(destination=path_out, format="turtle")
    print(f"Added {added} inverse property assertions.")


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Validate H2HO knowledge base: merge TBox + ABox, "
            "reason with ROBOT/HermiT, materialize inverse properties, "
            "and run a SPARQL query."
        )
    )

    p.add_argument("--robot", default="robot.jar", help="Path to robot.jar")
    p.add_argument("--reasoner", default="hermit", help="Reasoner to use")
    p.add_argument("--tbox", default="h2hoa.ttl", help="TBox ontology file")
    p.add_argument("--abox", default="nyhkb.ttl", help="ABox knowledge base file")
    p.add_argument("--query", required=True, help="SPARQL SELECT query file")

    p.add_argument("--merged-out", default="kb-merged.ttl", help="Merged ontology output")
    p.add_argument("--inferred-out", default="kb-inferred.ttl", help="Reasoned ontology output")
    p.add_argument("--materialized-out", default="kb-materialized.ttl", help="Inverse-materialized ontology output")
    p.add_argument("--query-out", default="query-results.csv", help="SPARQL query output file")
    p.add_argument("--explain-md", default="kb-inconsistency.md", help="Markdown inconsistency explanation")
    p.add_argument("--explain-owl", default="kb-inconsistency.ttl", help="OWL inconsistency explanation")
    p.add_argument("--unsat-out", default="kb-unsat-debug.owl", help="Unsatisfiable debug module output")

    p.add_argument("--skip-reasoning", action="store_true", help="Skip reasoning")
    p.add_argument("--skip-materialize-inverses", action="store_true", help="Skip inverse property materialization")

    args = p.parse_args()

    require_file(args.robot, "robot.jar")
    require_file(args.tbox, "TBox")
    require_file(args.abox, "ABox")
    require_file(args.query, "SPARQL query")

    merged_cmd = [
        "java", "-jar", args.robot,
        "merge",
        "--input", args.tbox,
        "--input", args.abox,
        "--output", args.merged_out,
    ]
    run_or_die(merged_cmd, "MERGE (TBOX + ABOX)")

    target = args.merged_out

    if not args.skip_reasoning:
        reason_cmd = [
            "java", "-jar", args.robot,
            "reason",
            "--input", args.merged_out,
            "--reasoner", args.reasoner,
            "--axiom-generators", "ClassAssertion PropertyAssertion",
            "-D", args.unsat_out,
            "-vvv",
            "--output", args.inferred_out,
        ]

        cp = run_capture(reason_cmd, f"REASON ({args.reasoner})")

        if cp.returncode != 0:
            stderr_lower = (cp.stderr or "").lower()
            stdout_lower = (cp.stdout or "").lower()

            if "inconsistent" in stderr_lower or "inconsistent" in stdout_lower:
                print("\nOntology inconsistent. Generating explanation...", file=sys.stderr)

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

            elif "unsatisfiable" in stderr_lower or "unsatisfiable" in stdout_lower:
                print(
                    f"\nOntology has unsatisfiable classes. "
                    f"Debug module written to: {args.unsat_out}",
                    file=sys.stderr,
                )

            sys.exit(cp.returncode)

        target = args.inferred_out
    else:
        print("\n--- SKIPPING REASONING ---")

    if not args.skip_materialize_inverses:
        materialize_inverse_properties(target, args.materialized_out)
        target = args.materialized_out
    else:
        print("\n--- SKIPPING INVERSE MATERIALIZATION ---")

    query_cmd = [
        "java", "-jar", args.robot,
        "query",
        "--input", target,
        "--query", args.query, args.query_out,
    ]

    cpq = run_capture(query_cmd, "QUERY")
    if cpq.returncode != 0:
        sys.exit(cpq.returncode)

    if os.path.exists(args.query_out):
        print("\n--- QUERY RESULTS ---")
        with open(args.query_out, "r", encoding="utf-8") as f:
            print(f.read())

    print("\n✅ VALIDATION COMPLETE")


if __name__ == "__main__":
    main()