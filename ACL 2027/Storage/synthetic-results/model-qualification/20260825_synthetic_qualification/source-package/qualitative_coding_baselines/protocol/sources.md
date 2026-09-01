# Process and model-source record

Sources were checked on 2026-08-25. This file records the methodological basis
for the protocol; it does not turn any metric into a validity guarantee.

## Method and evaluation

- Braun and Clarke on quality and methodological congruence in thematic analysis:
  https://doi.org/10.1080/14780887.2020.1769238
- Jacobs and Wallach on separating constructs from operationalizations:
  https://doi.org/10.1145/3442188.3445901
- Chen et al. on plurality-aware open-code diagnostics and repeated runs:
  https://aclanthology.org/2026.findings-acl.2073/
- HICode on many-to-many alignment and divergence between embedding and human
  evaluation: https://aclanthology.org/2025.emnlp-main.1580/
- CentaurTA on explicit expert-calibrated qualitative evaluation:
  https://aclanthology.org/2026.findings-acl.778/
- Jowsey et al. on quotation fidelity and corpus-position failure:
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0330217
- Dörfel and Ammoneit on the distinction between stability and human alignment:
  https://doi.org/10.3390/educsci16081314
- Liu et al. on source-symmetric blinded comparison and Bradley–Terry ranking
  (2026 preprint; not treated as settled validation):
  https://arxiv.org/abs/2607.28890
- Full-provenance architecture (2026 preprint):
  https://arxiv.org/abs/2603.08989

## Current OpenAI model guidance

- Official model-family guide (fetched 2026-08-25):
  https://developers.openai.com/api/docs/guides/latest-model
- GPT-5.6 Sol: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- GPT-5.6 Terra: https://developers.openai.com/api/docs/models/gpt-5.6-terra
- GPT-5.6 Luna: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- GPT-5.5: https://developers.openai.com/api/docs/models/gpt-5.5
- GPT-5.4: https://developers.openai.com/api/docs/models/gpt-5.4

The official guide describes Sol as the frontier-capability option, Terra as a
quality/cost balance, and Luna as the efficient high-volume option. The Codex
runtime comparison records exact runtime model labels, but it does not expose
provider request IDs, token use, latency, or dated GPT-5.6 snapshots. Those
limitations are retained in the run manifest and prevent a publication-grade
cost or API-reproducibility claim from this qualification.

## Governance sources in this workspace

- `dataset/PROCESSING.md`
- `dataset/KODIS_PROCESSING.md`
- `dataset/CANDOR_PROCESSING.md`
- `overleaf/DATASET_PLAN.md`
- `review/_workspace/research/evaluation_methodology.md`

These local records require institutional/platform/model-processing clearance
before real Dreaddit or AGYW inference and document that no KODIS/CANDOR data
is authorized for this baseline, even though a separate private KODIS workbook
is present. They therefore control the scope of the current run.
