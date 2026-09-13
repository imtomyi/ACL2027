# Twelve-Point TA Test: Inspection Notes

Post-run assistant inspection, separate from the frozen model artifacts and
generation manifest. This is not independent adjudication, a complete flaw
inventory, or a Credibility/Conformability score.

## Result

Local Gemma 3 4B processed all twelve previously exposed Dreaddit paragraphs in
their three original four-record packets. Each packet was generated once.
The three inference calls took 78.66 seconds in total, including their reported
request overhead. Software preparation and inspection time are not included.
No technical failures or paid calls occurred. The test-owned server was allowed
to shut down after completion.

| Packet Report | Source Paragraphs | Codes | Subthemes | Provisional Themes | Exact-Quote Flags |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Packet 1](ta_artifacts/TA_PKT_29de700981b105e4/codes_and_themes.md) | 4 | 5 | 0 | 1 | 2 |
| [Packet 2](ta_artifacts/TA_PKT_2cd6cab5f18bd96a/codes_and_themes.md) | 4 | 5 | 0 | 1 | 2 |
| [Packet 3](ta_artifacts/TA_PKT_35e4f9ef24450d68/codes_and_themes.md) | 4 | 5 | 0 | 1 | 0 |
| Total | 12 | 15 | 0 | 3 | 4 |

These are unit instances, not counts of independently validated or globally
deduplicated concepts. Code/theme IDs are local to each artifact. Five codes
and one theme per packet were the model's choices, not enforced quotas.

## Exact-Quote Findings

- Packet 1, C001 and T001: the same quotation changes the original spacing
  after "dog food,". Both occurrences fail strict exact-substring matching.
  This is two anchor flags for one repeated quotation change, not two
  independently established material flaws.
- Packet 2, C003: the quotation is attributed to record 02754, although the
  wording belongs to the neighboring record 02753, with a changed starting
  boundary. The supplied record does not contain the quote.
- Packet 2, C005: the quotation rewords the original sentence rather than
  preserving a verbatim substring.

The runner keeps these outputs instead of silently correcting them. Exact
offsets remain unresolved for these four occurrences. Mechanical validity alone
cannot decide the materiality of a whitespace change or the quality of a theme.

## Additional Interpretation Concerns

- Packet 1, T001: the claim generalizes to what stressed individuals "often"
  report. The evidence only supports a bounded interpretation of this packet.
  The source notes also attach some codes to records not supporting their
  recorded evidence, and exclude the job-move planning paragraph from coding.
  The relevance of that exclusion needs review against the research question.
- Packet 2, T001: a single account of sleep and time uncertainty becomes a
  general claim about intense stress affecting cognition. The source does not
  independently establish that causal interpretation. A single-source qualifier
  does not remove the broader wording in the analytic claim.
- Packet 3, C001: the author is recruiting participants as a filmmaker; the code
  definition/scope instead describe interest or intent to participate. This
  changes the author's role despite quoting the source exactly.
- Packet 3, T001: a theme about distressed individuals seeking community support
  is supported primarily by the filmmaker's project introduction, while linking
  all five codes. The declared multi-source support and inferential links need
  examination. Zero mechanical flags here does not mean correct TA.

These observations are inspection candidates, not a frozen answer key. No
precision, recall, accuracy, Credibility or Conformability percentage is inferred.

## What This Test Establishes

The local constructor can produce schema-valid, evidence-linked code/theme
artifacts and readable reports from the selected real source paragraphs.
It does not establish the semantic correctness of those artifacts. The source
links and documented defects make the outputs inspectable candidates for a
future authorized flaw-detection test.

There was no detector call, Playbook update, multi-epoch adaptation or quality
judge. The earlier paragraph experiment remains paused, and its five-rule
automatic and eight-rule manual Playbooks are unchanged. No Table 3 or manuscript
file was edited.

[Generation Summary](summary.md) | [Counts CSV](generation_summary.csv) |
[Frozen Inputs](inputs.private.json) | [Final Manifest](final_manifest.json)
