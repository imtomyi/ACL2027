# v5 merge decisions

This is a specification merge. Historical source files and stopped experiments are preserved. The guideline version is independent of historical ACE Original/V2/V3/V4 recovery labels; none is renamed to ACE V5.

| **Topic** | **Inputs that differ** | **v5 decision** | **Reason / consequence** |
| --- | --- | --- | --- |
| Dataset size | Local design 100/100/100; MIATA offline test 24/128/8 | Keep train/adaptation 100, development 100, evaluation 100 per corpus | Latest explicit uniform-data design; real disjoint records still need preparation |
| Test selection | Existing local and MIATA test manifests | Compare exact IDs, source groups and content hashes; no equality assumed | Preserve the selected evaluation panel only if compatible; otherwise identify a new panel |
| Historical test exposure | Prior outputs already inspected | Disclose prior panel use; tune on development only | Reusing a known panel is not a newly untouched confirmatory evaluation |
| Method panel | Local 24; MIATA original 30; previous new design 28 | Keep 28 per model | Add supervised offline ACE; omit GT-reference coding conditions unsupported by real GT |
| CaChe / ParlaMint references | MIATA unverified model-reference banks versus GT-free design | Preserve banks as historical evidence; no new-profile Acc/F1 or reference feedback | Model-reference agreement is not human-label accuracy |
| Repetitions | Existing seed 42, unlaunched 42/43 ACE draft | Keep seeds 42/43/44 for all new conditions | Same item set, paired per-seed order; 84 condition-runs per model |
| Runtime limit | Historical two-hour cap and later unlimited runtime | No wall-clock cutoff; finite documented optimizer budgets remain | Unlimited duration does not define a reproducible search budget |
| Backbone | Historical Qwen3-8B; discussed Qwen/Gemma/Mistral candidates | Remains unselected for v5 | A discussion or saved checkpoint is not model selection |
| Inference settings | Several historical generator/curator caps | Keep the new shared role-cap design and fresh manifest | No mixing historical outputs from different caps into new results |
| DC length failures | Larger curator cap still failed in MIATA | Bounded retries only; preserve failure evidence, no guaranteed repair claim | Nonterminating generation can persist at larger caps |
| Retaining memory | Paused local budget rejection and MIATA unfinished retained-failure draft | Valid oversized candidate can retain prior memory as specified; exhausted generation still fails the condition | Do not import unfinished failure-retention semantics or mark truncated content accepted |
| Grounding | Legacy 384-token same-family judge versus expanded v2 | Keep expanded v2, separate judge selection/calibration and audit status | Old Conformability is not interchangeable with new rubric scores |
| Metrics | Historical Acc/agreement/F1/grounding versus broad new register | Keep 85 entries/families with 340 dataset-condition records | Applicability and required inputs travel with every exported value |
| Hardware | One-A6000 reference design versus historical eight-service orchestration | One GPU/concurrency 1 for reference timing; separate named profile for verified allocated parallel resources | Saved service count does not prove current GPU availability or equal timing conditions |
| Queue order | Historical feedback barriers versus generic new serial panel | Preserve sequential items per cell; schedule GT✓ before GT✗ for labeled adaptation conditions; coding corpora remain GT✗ only | Scheduling is recorded; no model-reference feedback is introduced into GT-free corpora |
| Cross-cell state | Recovery drafts import prefixes and endpoint histories | Fresh new-protocol adaptation/optimizer state; no old prediction or playbook imports | Historical continuation is a different scientific scope |
| Reuse | MIATA runtime/model/corpus/vendor sources | Reuse validated assets, never old launch leases or unverified API compatibility | Linux and macOS environments are distinct; pin actual selected model runtime |
| Monitoring | Paused local 5-minute and MIATA 30-minute monitors | Keep both stopped now; new 5-minute English monitor only when execution resumes | Latest user pause remains in force |
| Manuscript / Notion | Historical diagnostic reports and desired final tables | Preserve all provenance and metric labels; publish only authorized verified results | This merge creates no new measured evidence or final manuscript result |

The scheduling row is an implementation convention to be made explicit in the future execution manifest, not an instruction to reactivate an old scheduler. Corpus display order and scientific item order remain those of the guideline.

## Sources preserved in full

- [Previous design snapshot](sources/previous_design/Storage/EXPERIMENT_GUIDELINES.md), including metric register, applicability matrix, table schemas and the previous handoff review.
- [MIATA handoff](sources/miata_handoff/README.md), including all 868 manifest-listed files and its manifest receipts.
- [Historical decision record](sources/miata_handoff/DECISIONS.md), [file map](sources/miata_handoff/FILE_MAP.md), [relocation notes](sources/miata_handoff/LOCAL_MATERIALS_AND_RELOCATION.md), and [extra-artifact review](sources/miata_handoff/EXTRA_ARTIFACTS_REVIEW.md).

Source path and byte hashes are recorded in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). Absolute paths embedded in preserved originals are historical provenance, not current local path guesses or instructions to access another account.
