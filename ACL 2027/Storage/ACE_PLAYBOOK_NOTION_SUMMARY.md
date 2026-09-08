# ACE AppWorld Playbooks: Initial, Offline, and Online

ACE's AppWorld playbook is a reusable collection of instructions, workflows, API knowledge, and verification rules. The agent receives it as part of its prompt. Experience is retained by updating this text, rather than by updating the generator model's weights in the inspected adaptation code.

This note summarizes the three supplied AppWorld playbook artifacts and the accompanying local implementation. File statistics below were counted directly on September 8, 2026. They describe the supplied files, not benchmark scores.

## 1. The Three Artifacts

| Version | File | Rule entries | Words |
|---|---|---:|---:|
| Initial | appworld_initial_playbook.txt | 8 | 215 |
| Offline, no GT | appworld_offline_trained_no_gt_playbook.txt | 318 | 16,042 |
| Online | appworld_online_trained_playbook.txt | 359 | 17,808 |

An entry is a line beginning with an identifier such as `[shr-00005]`. Words are counted by whitespace splitting, including headings and identifiers. These are not tokenizer counts.

**Initial:** A small starting set of operational instructions. Several section headings exist before any rules have been added to them.

**Offline:** An expanded playbook associated with adaptation before evaluation. The local README describes adapting on the training split and subsequently evaluating with the resulting context on `test_normal`.

**Online:** An expanded playbook associated with adaptation during a sequence of tasks. The local online configuration starts from the initial playbook and runs adaptation on `test_normal`.

**Relationship:** Treat offline and online as separate adaptation conditions. The inspected online configuration does not initialize from the supplied offline file. The three files alone do not establish a single Initial -> Offline -> Online training history.

## 2. How the Playbook Is Used

1. **Generator:** Receives the task and current playbook, then produces code and API actions.
2. **Environment:** Executes actions and returns observations or errors.
3. **Reflector:** Inspects the trajectory and available feedback to identify reusable lessons.
4. **Curator:** Converts lessons into structured playbook operations.
5. **Later tasks:** Receive the updated playbook as context.

In the inspected `adaptation_react.py`, the playbook is supplied to the generator prompt template. Reflection uses conversation history, a test report when available, and ground-truth code when supplied. The curator response contains JSON operations; this implementation accepts ADD operations into named sections.

The learned artifact is therefore a collection of written procedures that future agent executions can consult. It is distinct from the task transcript, the evaluation answer, and a model checkpoint.

## 3. The Eight Sections

| Section | What it stores | Initial | Offline | Online |
|---|---|---:|---:|---:|
| Strategies and Hard Rules | General constraints and operating strategies | 3 | 96 | 159 |
| APIs to Use for Specific Information | Which API supplies a needed field or action | 1 | 57 | 58 |
| Useful Code Snippets and Templates | Reusable procedures and code patterns | 0 | 27 | 0 |
| Common Mistakes and Correct Strategies | Failure patterns and their corrections | 0 | 48 | 65 |
| Problem-Solving Heuristics and Workflows | General execution habits | 2 | 2 | 2 |
| Verification Checklist | How to check the resulting state | 0 | 86 | 71 |
| Troubleshooting and Pitfalls | Exceptional API behavior and recovery | 0 | 0 | 1 |
| Others | Additional task-completion conventions | 2 | 2 | 3 |
| **Total** | | **8** | **318** | **359** |

All three files use the same eight section headings. An empty section means that no entries appear under that heading in this artifact; it does not mean similar guidance is absent elsewhere.

## 4. What a Rule Looks Like

An entry consists of a section-specific prefix, a numeric identifier, and a natural-language instruction.

```text
[shr-00005] Always look at API specifications (using apis.api_docs.show_api_doc) before calling an API.
```

This initial rule remains present in both expanded files. Here, `shr` denotes the strategies-and-hard-rules section. The identifier addresses the rule; it is not a quality score.

The supplied files do not display per-rule helpful/harmful counters, confidence scores, or validation outcomes. The same identifier can refer to different content in different playbooks, so a citation should include both the filename and the entry ID.

## 5. Concrete Examples

The descriptions below are paraphrases of actual entries.

| Artifact / entry | Situation | Stored guidance |
|---|---|---|
| Initial / psw-00007 | An API returns paginated results | Iterate through pages instead of assuming the first response contains everything. |
| Offline / cms-00016 | A review already exists | Check existing reviews and update the existing record instead of creating a conflicting duplicate. |
| Offline / code-00010 | Find the most-liked song across playlists | Obtain credentials, collect playlists with pagination, deduplicate song IDs, retrieve like counts, and identify the maximum. |
| Online / cms-00010 | Match contacts across platforms | Collect both email and phone identifiers; email-only matching can miss valid matches. |
| Online / vc-00256 | Verify removal from a playlist or queue | Check that the targeted IDs are absent, rather than relying only on a changed total count. |

These examples show how a generic instruction can become a task-specific procedure with an explicit completion check. They are stored recommendations, not proof that every recommendation is correct or universally applicable.

## 6. What "No GT" Means Here

The inspected offline adaptation configuration sets `use_gt_code: false` and selects a no-GT reflector prompt. This supports describing that configuration as not supplying ground-truth solution code through that option.

It does not establish that the entire pipeline receives no feedback or no benchmark-derived information. The inspected reflection code can include test reports, and task initialization accesses required API metadata from the task's ground-truth object.

There is also a provenance distinction: the current offline configurations reference a filename ending in `_deepseek_3_1.txt`, whereas the supplied offline artifact has no such suffix. The configuration illustrates the workflow but does not, by itself, prove the exact model, epoch count, or execution history that produced the supplied offline file.

## 7. What the Comparison Shows

- The expanded artifacts contain much more procedural knowledge than the initial eight-rule seed.
- Offline includes 27 entries under code snippets/templates and 86 under verification.
- Online contains more hard-rule entries, but fewer verification entries and no entries under the code-template heading.
- Both expanded versions retain the eight original seed entries.
- More entries do not establish higher benchmark performance. These text files contain no task-success comparison.

The online artifact also contains repeated guidance. For example, `vc-00197`, `vc-00200`, and `vc-00201` repeat the same account-creation verification text. Consequently, entry count is not a count of distinct lessons. Retention, deduplication, and relevance matter when interpreting playbook growth.

## 8. Relevance to WarrantRoute

The transferable idea is to retain reusable, evidence-grounded review procedures across tasks. The AppWorld-specific API instructions would need to be replaced with procedures appropriate to qualitative review.

| AppWorld concept | Possible WarrantRoute counterpart |
|---|---|
| API documentation and field knowledge | Dataset characteristics and evidence-field definitions |
| Common API mistakes | Unsupported interpretation, omitted counterevidence, or lost context |
| Reusable task workflows | Review procedures for a specific flaw type |
| State verification | Checking that a proposed revision resolves the diagnosed issue against the cited evidence |
| Curated experience | Versioned review lessons with supporting development examples |

This is a proposed adaptation, not a description of a biomedical playbook supplied by ACE. These three artifacts concern AppWorld app/API tasks.

For an offline WarrantRoute comparison, develop the playbook using designated development data, freeze it, and evaluate it on separate test packets. If the playbook instead evolves during evaluation, report that condition as online adaptation and retain the task order and playbook version used for each prediction.

## Source Files

- [Initial playbook](../../ace_paper/original_sources/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt)
- [Offline no-GT playbook](../../ace_paper/original_sources/ace-appworld/experiments/playbooks/appworld_offline_trained_no_gt_playbook.txt)
- [Online playbook](../../ace_paper/original_sources/ace-appworld/experiments/playbooks/appworld_online_trained_playbook.txt)
- [AppWorld README](../../ace_paper/original_sources/ace-appworld/README.md)
- [Adaptation implementation](../../ace_paper/original_sources/ace-appworld/experiments/code/ace/adaptation_react.py)
- [Offline adaptation configuration](../../ace_paper/original_sources/ace-appworld/experiments/configs/ACE_offline_no_GT_adaptation.jsonnet)
- [Offline evaluation configuration](../../ace_paper/original_sources/ace-appworld/experiments/configs/ACE_offline_no_GT_evaluation.jsonnet)
- [Online adaptation configuration](../../ace_paper/original_sources/ace-appworld/experiments/configs/ACE_online_no_GT.jsonnet)

The links above resolve within this local repository. To preserve access from Notion, attach the three playbook files or replace local links with the corresponding repository URLs. No benchmark run was executed for this summary, and exact correspondence to a particular published result row has not been independently established here.
