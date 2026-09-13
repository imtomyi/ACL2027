# Initial and After Playbook Comparison

Run: `dreaddit_paragraph4_playbook_smoke_20260910T042347Z`.
Local Gemma 3 4B, four original Dreaddit paragraphs, three epochs, 12 completed
query exposures. These are separate post-run snapshots, not new inference
outputs. The original artifacts and frozen manifests are unchanged.

## Files

- [playbook_initial.txt](playbook_initial.txt): exact initial TXT content from
  `../playbooks/dreaddit/history/revision-00000.txt`.
- [playbook_after.txt](playbook_after.txt): exact final TXT content from
  `../playbooks/dreaddit/current.txt`, after all 12 exposures.

## Differences

**The two files are byte-for-byte identical.** No accepted content update occurred.

| **Property** | **Initial** | **After** |
| --- | --- | --- |
| Completed query exposures | 0 | 12 |
| Content revision | 0 | 0 |
| Total rules | 2 | 2 |
| Learned rules | 0 | 0 |
| Rule IDs | shr-00001, shr-00002 | shr-00001, shr-00002 |

Added rules: 0. Modified rules: 0. Removed rules: 0.

Both TXT snapshots and their source TXT files have SHA-256:

```text
0d60429c84549ce05d5cc4c59c411f663375f979abe98ba0de17b2dfff216cff
```

The experiment attempted learning after each query. All 18 proposed refinements
were withheld: 12 for targeting immutable seed rules, and six for missing a
required countercondition (reported as `rule_text_budget` before the seed check).
The latter six also targeted seeds. Three exposures proposed no delta.

Existing Playbook TXT delivery was verified in all 12 detector requests, but
learning or improved detection was not demonstrated. There is no adjudicated
flaw inventory for these inputs, so correctness and Credibility/Conformability
are not assessed. See [the diagnostic report](../post_run_analysis.md) and
[per-query outcomes](../query_progress.csv).
