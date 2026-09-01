#!/bin/sh
set -eu

workspace_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dir="$workspace_root/overleaf"
output_dir="$workspace_root/output/pdf"
output_stem="warrant-route-acl2027-current-manuscript"
output_pdf="$output_dir/$output_stem.pdf"

mkdir -p "$output_dir"

python3 "$workspace_root/governance/scripts/check_required_manuscript_citations.py"
python3 "$workspace_root/governance/scripts/check_manuscript_data_policy.py"

cd "$source_dir"
latexmk -norc -pdf -interaction=nonstopmode -halt-on-error \
  -jobname="$output_stem" \
  -outdir="$output_dir" \
  main.tex
latexmk -norc -c \
  -jobname="$output_stem" \
  -outdir="$output_dir" \
  main.tex
rm -f "$output_dir/$output_stem.bbl"

test -f "$output_pdf"
python3 "$workspace_root/governance/scripts/check_manuscript_data_policy.py"
