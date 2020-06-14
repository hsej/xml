#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

python3 ../converter/table_to_csv.py \
  --tag="{http://www.sa.dk/xmlns/siard/1.0/schema0/table.xsd}row" \
  --input="../files/table.xml" \
  --output="../files/table.csv"