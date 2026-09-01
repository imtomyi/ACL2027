# Five-corpus dataset index

This directory is the single entry point for the five obtained study corpora.
The corpus folders here are compatibility links to their existing restricted
locations; no source or processed data are duplicated.

| Corpus | Entry point | Source status | Processed status |
|---|---|---|---|
| DREDDIT | `dreaddit/` | Obtained; official train/test archive preserved | Existing restricted derivative available under `../deidentified/dreaddit/` |
| AGYW focus groups | `agyw_focus_groups/` | Obtained; 11 transcript files preserved | Existing restricted derivative available under `../deidentified/agyw_focus_groups/` |
| KODIS | `kodis/` | Obtained; workbook and provider README preserved | Private exploratory human–human turn bundle under `../deidentified/kodis_exploratory_private/`; one unsplit role |
| CaSiNo | `casino/` | Obtained; pinned repository archive and extraction preserved | Not yet processed |
| AMI scenario meetings | `ami_scenario_meetings/` | Obtained; official annotation archive and selective extraction preserved | Not yet processed |

## Handling rules

- Treat every linked corpus as restricted, including publicly downloadable
  source material.
- Do not edit files under a corpus `raw/` area or the AGYW/DREDDIT source
  locations in place.
- Write derived records only through the documented processing pipelines.
- Do not place experimental results in this directory; use the project
  experiment or storage areas.
- `processed/` being empty means preprocessing has not begun or has not been
  approved. It does not mean that acquisition is incomplete.
- KODIS exploratory output is deliberately separate from the governed KODIS
  pipeline and is not sampling eligible for a manuscript experiment.

The compatibility links preserve paths used by existing scripts. See
`../README.md` for governance and processing documentation.
