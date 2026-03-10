#!/bin/bash

# Input files
HO=../ho61508/ho61508.ttl
H2HO=../ho61508/h2ho.ttl
H2HOA=h2hoa.ttl

# Output
OUT=ho61508-h2ho-merged.ttl

echo "Merging ontologies..."

############################################################
# 1. Copy ho61508.ttl as-is
############################################################
cat "$HO" > "$OUT"
echo "" >> "$OUT"

############################################################
# 2. Ensure h2ho prefix is present
############################################################
if ! grep -q "^@prefix h2ho:" "$HO"; then
    echo "@prefix h2ho: <https://w3id.org/jochumsson/h2ho#> ." >> "$OUT"
    echo "" >> "$OUT"
fi

############################################################
# 3. Append h2ho.ttl WITHOUT HEADER
############################################################
# Remove everything until the FIRST line beginning with 'h2ho:'
sed -n '/^h2ho:/,$p' "$H2HO" >> "$OUT"
echo "" >> "$OUT"

############################################################
# 4. Ensure h2ho prefix is present
############################################################
if ! grep -q "^@prefix h2hoa:" "$HO"; then
    echo "@prefix h2hoa: <https://w3id.org/jochumsson/h2ho-a#> ." >> "$OUT"
    echo "" >> "$OUT"
fi

############################################################
# 5. Append restrictions WITHOUT HEADER
############################################################
# Same logic: remove everything before the first real triple
sed -n '/^# H2HO-A - start of the ontology/,$p' "$H2HOA" >> "$OUT"

echo ""
echo "Done. Output written to $OUT"

