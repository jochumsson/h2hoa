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






#########################################################################################################
######################################### Chat GPT Text #################################################
#########################################################################################################


Chat GPT Generate text after working on the flammability queries:
Ontology Schema Testing Pattern (TBox Structural Invariants)

This thesis introduces a SPARQL-based ontology testing strategy for validating
domain-level modeling commitments at the schema (TBox) level. The strategy is
motivated by the observation that many ontology modeling errors do not lead to
logical inconsistency under OWL’s open-world semantics and are therefore not
detected by standard OWL reasoners. Instead, such errors correspond to unintended
weakening, duplication, or drift of constraint axioms over time.

The core notion introduced is that of a TBox structural invariant. A TBox
structural invariant is a constraint on the form, multiplicity, and target of
OWL axioms that must hold for an ontology to be considered well-formed with
respect to its intended domain semantics. These invariants are independent of
instance data (ABox) and are validated directly against the ontology schema.

A recurring modeling pattern in the ontology is the restriction of hazard
classes to specific hazard source roles. Semantically, this is expressed using
the following Description Logic axiom schema:

  H ⊑ ∃ R.C ⊓ ∀ R.C

where H is a hazard class, R is a property (e.g., inheresIn), and C is the class
of permitted hazard sources. The existential restriction (∃ R.C) enforces that
every instance of H must inhere in at least one instance of C, while the
universal restriction (∀ R.C) ensures that no other fillers of R are permitted.

In addition to this semantic requirement, the ontology adopts a structural
discipline whereby exactly one existential and exactly one universal restriction
of this form must be present in the TBox. This avoids accidental duplication,
parallel constraint definitions, or silent weakening of constraints, none of
which are detected by OWL reasoners.

Structural invariants are validated using SPARQL queries formulated as violation
queries. Each query returns zero results if the invariant holds and one or more
results if it is violated. This enables integration of ontology validation into
automated testing pipelines, analogous to unit tests in software engineering.

In cases where the allowed source class C is itself defined as a union of more
specific classes, an additional refinement invariant is introduced. This
invariant validates that the union definition contains exactly the intended
member classes and no others, thereby preventing schema drift over time. This
refinement test is orthogonal to the hazard-to-source constraint and complements
it.

The proposed testing strategy operates exclusively at the TBox level and does
not validate individual instance data. Instance-level validation is delegated to
OWL reasoning and, where appropriate, dataset-specific validation mechanisms.
The approach therefore complements, rather than replaces, existing
reasoning-based validation techniques.

Overall, this work presents a lightweight but rigorous ontology schema testing
method that combines Description Logic semantics with explicit structural
validation, supporting regression testing and long-term maintainability of
safety-critical ontologies.


##################### Related Work #############################################
Related Work and Identified Research Gap

This work is situated at the intersection of ontology engineering, Description
Logic semantics, and ontology validation and testing. While each of these areas
is well studied individually, their integration into a systematic, executable
ontology schema testing methodology remains insufficiently addressed in the
literature.

Foundational work on Description Logics and OWL semantics, such as Baader et al.
(The Description Logic Handbook) and Horrocks et al. (From SHIQ and RDF to OWL),
establishes the formal meaning of existential (∃) and universal (∀) restrictions
under the open-world assumption. These works clarify that missing, duplicated,
or weakened axioms do not necessarily result in logical inconsistency and are
therefore not detected by standard OWL reasoners. However, they do not address
how intended modeling commitments should be verified or enforced during ontology
development.

Ontology evaluation has been discussed since early work by Gómez-Pérez, who
identified verification and validation as central quality concerns. Subsequent
approaches such as OntoClean (Guarino and Welty) introduced meta-level
constraints on ontological modeling decisions, demonstrating that many modeling
errors are not logical contradictions. Nevertheless, these approaches are
conceptual and methodological rather than operational, and they do not provide
executable tests that can be integrated into automated development pipelines.

Constraint languages such as SHACL and ShEx represent the current state of the
art in RDF validation. While powerful, these languages primarily target instance
data (ABox validation) and treat ontology axioms as data rather than as objects
of validation themselves. They do not natively support expressing or enforcing
schema-level invariants such as the requirement that exactly one existential and
one universal restriction of a given form must exist in the TBox.

Several authors have proposed using SPARQL for ontology debugging and quality
assessment, including Hogan et al., who employ SPARQL to detect schema anomalies
in linked data. However, such uses of SPARQL are typically ad hoc and lack a
formalized notion of reusable structural invariants or a principled testing
strategy.

More closely related to the present work is research on Ontology Test-Driven
Development (OTDD). Notably, Keet and colleagues propose adapting principles
from software Test-Driven Development to ontology engineering, emphasizing the
use of competency questions, test cases, and early validation to guide ontology
design. These approaches successfully demonstrate that ontologies benefit from
systematic testing practices and that tests can capture modeling intent beyond
logical consistency.

However, existing OTDD approaches primarily focus on:
- competency-question answering,
- reasoning outcomes,
- or expected inference results.

They do not explicitly address the validation of ontology schema structure
itself, such as enforcing the presence, uniqueness, and strength of constraint
axioms at the TBox level. As a result, ontologies may pass all reasoning-based
tests while still violating intended domain semantics due to silent schema drift
or constraint weakening.

The research gap addressed by this work can therefore be stated as follows:
Existing ontology engineering and testing approaches lack systematic, executable
mechanisms for validating TBox-level structural invariants that encode intended
modeling discipline. In particular, they do not detect missing, duplicated, or
weakened existential and universal restrictions that are critical in
safety-critical domains.

This thesis addresses this gap by introducing a SPARQL-based ontology schema
testing strategy grounded in Description Logic semantics. Intended domain
constraints are expressed as TBox structural invariants, validated using
parameterized violation queries that return results only when an invariant is
broken. The approach complements OWL reasoning and existing OTDD methodologies
by extending automated testing to the ontology schema itself, enabling
regression testing and long-term maintainability of evolving ontologies.

Key references:
- Baader et al., The Description Logic Handbook
- Horrocks et al., From SHIQ and RDF to OWL
- Gómez-Pérez, Ontology Evaluation
- Guarino and Welty, OntoClean
- Knublauch and Kontokostas, SHACL (W3C Recommendation)
- Hogan et al., Linked Data Conformance
- Keet et al., Ontology Test-Driven Development (OTDD)
