# Direction H real-data start here

The intended corpora are real Dreaddit and real `agyw_focus_groups`. Do not run
the earlier fictional/synthetic pilot or any item-data command.

## Safe first action

From the workspace root, run the governance-only readiness check. It reads no
corpus text:

```bash
python3 experiments/direction_h_human_in_loop/active_real_data/check_readiness.py \
  --as-of <current-UTC-timestamp-ending-in-Z>
```

At present it must report both corpora blocked at `0/10`. A blocked result is a
successful safety check, not permission to inspect a record.

## Charlie's first action

Charlie should do **nothing with item text yet**. First, the PI/institution and
coordinator must complete and independently verify the documentary gates listed
in [`active_real_data/README.md`](active_real_data/README.md). Charlie must not
be asked to browse raw/deidentified records, select examples, perform privacy
review on his own future rating items, or self-authorize the study.

Once the exact rater-exposure and consent controls are approved, Charlie's first
study action will be a real-data-specific tutorial and comprehension check using
material separately cleared for that purpose. That instrument does not exist
yet and must not be substituted with fictional examples without fresh explicit
permission.

## Stop conditions

Stop if any gate is pending, rejected, expired, version-stale, missing its
evidence reference, or outside the exact corpus/use. Also stop if a candidate
packet lacks two distinct privacy reviewers or permits model processing but not
rater display (or vice versa). Never infer approval from a public download,
CC BY license, source-study consent, a deidentified directory name, a checksum,
or a technically valid build.
