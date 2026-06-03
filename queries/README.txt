SPARQL queries supporting Section 6.2 (NYHKB querying) and IEC 61508-1 clause 7.4.2.

Run against merged H2HO + H2HOA + NYHKB (backup/h2ho.ttl + h2hoa.ttl + nyhkb.ttl), after
reasoning and inverse materialization (see run-validaton.py).

  listing-1-hazard-triggers.sparql          Paper Listing 1; IEC 61508-1 7.4.2.3 (triggers)
  iec61508-7.4.2.3-hazard-identification.sparql   7.4.2.3 hazards, events, situations
  iec61508-7.4.2.4-event-sequences.sparql         7.4.2.4 causal event sequences
  iec61508-7.4.2.6-harmful-events-harm.sparql     7.4.2.6 harmful events and harm
  iec61508-7.4.2.10-components-contributing.sparql  7.4.2.10 components / hazard sources
  iec61508-7.4.2.11-hazard-documentation.sparql   7.4.2.11 documented hazard knowledge
  iec61508-7.4.2.12-hazard-persistence.sparql     7.4.2.12 persisted RDF hazard assertions
  nyhkb-technical-room-hazards.sparql             Application query (technical room scope)

Equivalent copies for ROBOT verify live under validation/.

Empirical hazard narratives (Section 6.1 / Table 3 format): ../empirical-hazard-scenarios.txt
