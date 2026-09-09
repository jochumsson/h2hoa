#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
from typing import List, Optional, Sequence

from rdflib import Graph, URIRef
from rdflib.namespace import OWL


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


def write_ontology_without_imports(
    path_in: str, path_out: str, drop_import_iris: Sequence[str]
) -> int:
    """Copy an ontology file, removing selected owl:imports.

    ROBOT merge follows owl:imports by default. NYHKB imports published H2HOA and
    H2HOA imports published H2HO; when those are also passed as local --input files,
    the remote copies can reintroduce outdated axioms and make the merge inconsistent.
    Keep remote imports that are not supplied locally (e.g. HO61508).
    """
    g = Graph()
    g.parse(path_in)
    removed = 0
    for iri in drop_import_iris:
        triple = (None, OWL.imports, URIRef(iri))
        before = len(list(g.triples(triple)))
        g.remove(triple)
        removed += before
    g.serialize(destination=path_out, format="turtle")
    return removed


def materialize_inverse_properties(
    path_in: str, path_out: str, subclass_source: Optional[str] = None
) -> None:
    print("\n--- MATERIALIZE INVERSE PROPERTIES ---")
    print(f"Input:  {path_in}")
    print(f"Output: {path_out}")

    g = Graph()
    g.parse(path_in)

    RDFS = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    if subclass_source:
        tbox = Graph()
        tbox.parse(subclass_source)
        subclass_added = 0
        for s, _, o in tbox.triples((None, RDFS, None)):
            if (s, RDFS, o) not in g:
                g.add((s, RDFS, o))
                subclass_added += 1
        print(
            f"Restored {subclass_added} rdfs:subClassOf axioms from {subclass_source} "
            "(for SPARQL type paths; reasoner may omit these)."
        )

    HO = "https://w3id.org/jochumsson/ho61508#"
    H2HOA = "https://w3id.org/jochumsson/h2hoa#"

    inverse_pairs = [
        (URIRef(HO + "triggers"), URIRef(H2HOA + "triggeredBy")),
        (URIRef(HO + "inheresIn"), URIRef(HO + "inheres")),
        (URIRef(HO + "manifestsIn"), URIRef(H2HOA + "manifestedBy")),
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
    p.add_argument("--h2ho", default="backup/h2ho.ttl", help="H2HO core ontology (event/hazard types)")
    p.add_argument("--tbox", default="h2hoa.ttl", help="Application TBox (H2HOA)")
    p.add_argument("--abox", default="nyhkb.ttl", help="ABox knowledge base (NYHKB)")
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
    p.add_argument(
        "--follow-published-imports",
        action="store_true",
        help=(
            "Do not strip redundant owl:imports of local H2HO/H2HOA. "
            "Default strips them so unpublished local ontology edits are used."
        ),
    )

    args = p.parse_args()

    require_file(args.robot, "robot.jar")
    require_file(args.h2ho, "H2HO")
    require_file(args.tbox, "TBox")
    require_file(args.abox, "ABox")
    require_file(args.query, "SPARQL query")

    h2ho_iri = "https://w3id.org/jochumsson/h2ho"
    h2hoa_iri = "https://w3id.org/jochumsson/h2hoa"
    merge_h2ho = args.h2ho
    merge_tbox = args.tbox
    merge_abox = args.abox
    tmp_paths: List[str] = []

    try:
        if not args.follow_published_imports:
            tmp_dir = tempfile.mkdtemp(prefix="h2hoa-validate-")
            merge_tbox = os.path.join(tmp_dir, "h2hoa-no-h2ho-import.ttl")
            merge_abox = os.path.join(tmp_dir, "nyhkb-no-h2hoa-import.ttl")
            tmp_paths.extend([merge_tbox, merge_abox])

            removed_tbox = write_ontology_without_imports(
                args.tbox, merge_tbox, [h2ho_iri]
            )
            removed_abox = write_ontology_without_imports(
                args.abox, merge_abox, [h2hoa_iri]
            )
            print(
                "\n--- PREPARE LOCAL MERGE INPUTS ---"
                f"\nRemoved {removed_tbox} owl:imports of {h2ho_iri} from TBox copy"
                f"\nRemoved {removed_abox} owl:imports of {h2hoa_iri} from ABox copy"
                "\nLocal --h2ho/--tbox/--abox files are authoritative; HO61508 import retained."
            )

        merged_cmd = [
            "java", "-jar", args.robot,
            "merge",
            "--input", merge_h2ho,
            "--input", merge_tbox,
            "--input", merge_abox,
            "--output", args.merged_out,
        ]
        run_or_die(merged_cmd, "MERGE (H2HO + H2HOA + NYHKB)")

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
                        "--reasoner", "elk",
                        "-M", "inconsistency",
                        "--explanation", args.explain_md,
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
            subclass_source = args.merged_out if not args.skip_reasoning else None
            materialize_inverse_properties(
                target, args.materialized_out, subclass_source=subclass_source
            )
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

        print("\nVALIDATION COMPLETE")
    finally:
        for path in tmp_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        if tmp_paths:
            try:
                os.rmdir(os.path.dirname(tmp_paths[0]))
            except OSError:
                pass


if __name__ == "__main__":
    main()