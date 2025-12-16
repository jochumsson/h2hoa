Ontology Structural Unit Testing with ROBOT and SPARQL
=====================================================

1. Goal and scope
----------------

The goal of this testing setup is to automatically verify structural axioms of an OWL ontology, in particular:

- restrictions between Hazard classes and HazardSource classes
- allowed and forbidden class memberships
- correct use of existential (∃) restrictions over inheresIn and carriedBy

The focus is TBox-level testing, not ABox instantiation.

This approach is suitable for:
- regression testing during ontology evolution
- verifying modeling assumptions before publication
- documenting intended DL axioms in executable form


2. Core idea
------------

Each DL axiom of interest is translated into:

- a negative SPARQL test that returns violations
- executed using `robot verify`
- passing if and only if the query returns zero results

If the query returns any result, the ontology violates the axiom.

This mirrors unit testing in software: returned bindings correspond to failing test cases.


3. Tooling overview
-------------------

3.1 ROBOT

ROBOT is a command-line ontology tool built on the OWL API and Apache Jena.

In this setup it is used for:
- reasoning (robot reason)
- test execution (robot verify)

3.2 merge-ontologies.sh

This script is responsible for producing a single merged ontology prior to reasoning.

Typical responsibilities:
- merging ho61508, h2ho, and mapping ontologies
- resolving imports explicitly
- producing ho61508-h2ho-merged.ttl

Merging is intentionally separated from reasoning to keep responsibilities clear and reproducible.


4. Installation
---------------

Requirements:

- Java 11 or newer
- Python 3.9 or newer
- A Unix-like shell (Git Bash on Windows is sufficient)

ROBOT installation:

Download the latest ROBOT release:

https://github.com/ontodev/robot/releases/latest/download/robot.jar

Place robot.jar in the project root directory.

Verify installation:

java -jar robot.jar --version

Python dependencies:

No third-party Python libraries are required.
Only the Python standard library is used.

Shell scripts:

If using Windows:
- run scripts from Git Bash
- ensure merge-ontologies.sh has Unix line endings (LF)


5. Reasoning pipeline
---------------------

The pipeline consists of three conceptual stages:

1. Merge
2. Reason
3. Verify

Only inferred axioms are tested.

Reasoning command:

java -jar robot.jar reason
  --input ho61508-h2ho-merged.ttl
  --reasoner hermit
  --output ho61508-h2ho-inferred.ttl

Reasoning is required because:
- existential restrictions and subclass entailments must be materialized
- SPARQL tests operate over inferred TBox axioms


6. Test structure
-----------------

6.1 Directory layout

Project structure:

.
├── robot.jar
├── merge-ontologies.sh
├── run-tests.py
├── ho61508-h2ho-merged.ttl
├── ho61508-h2ho-inferred.ttl
└── tests/
    ├── flammability-source.test.sparql
    ├── oxygen-deficiency.test.sparql
    ├── pressure-hazard.test.sparql
    └── ...

Naming convention:

- every test file ends with *test.sparql
- each file contains exactly one SPARQL query

This is required by robot verify.


6.2 Test semantics
------------------

Each test file follows the same structure:

1. Document the DL axiom under test in comments
2. Select violations using SPARQL
3. Expect zero results

Example:

Rule: FlammabilityHazardSource must be one of the allowed hazard source types
DL axiom under test:
FlammabilityHazardSource ⊑ StorageVesselHazardSource ⊔
                            ProcessEquipmentHazardSource ⊔
                            PipingHazardSource

The SPARQL query selects any subclass of FlammabilityHazardSource that is not one of the allowed types.

If the query returns no rows, the axiom holds.


7. Executing tests with ROBOT
-----------------------------

To run a single test:

java -jar robot.jar verify
  --input ho61508-h2ho-inferred.ttl
  --queries tests/flammability-source.test.sparql

ROBOT behavior:

- PASS indicates zero violations
- FAIL lists violating classes


8. Automation with run-tests.py
-------------------------------

Purpose:

run-tests.py automates the entire workflow:
- optional ontology merge
- optional reasoning
- automatic discovery of test files
- execution of each test independently

Key features:

- executes all tests matching tests/*test.sparql
- fails fast on the first violation
- supports --skip-reasoning for faster iteration

Typical usage:

python run-tests.py

Skip reasoning when inferred ontology already exists:

python run-tests.py --skip-reasoning

Python is used instead of shell scripting to ensure portability across Windows and Unix environments and to allow structured error handling.


9. Why SPARQL and not DL query syntax
------------------------------------

Protégé DL queries are interactive and not automatable.

ROBOT does not support DL syntax for verification.

SPARQL is the only supported executable query language for robot verify.

Trade-off:
- DL queries are more concise and readable
- SPARQL is more verbose but executable and automatable

In this setup:
- DL axioms are documented
- SPARQL is used as an executable encoding of those axioms


10. Limitations
---------------

This approach intentionally does not:
- test individuals (ABox)
- prove global ontology consistency
- replace formal DL reasoning

It does:
- verify specific structural modeling constraints
- detect unintended ontology drift
- provide executable documentation of modeling decisions


11. Summary
-----------

This unit testing approach treats ontology axioms as executable constraints.

Using ROBOT and SPARQL, it enables:
- regression testing
- automated structural validation
- reproducible modeling decisions

It is particularly suitable for abstract research ontologies where:
- structure matters more than data
- modeling assumptions must be explicit and defensible

