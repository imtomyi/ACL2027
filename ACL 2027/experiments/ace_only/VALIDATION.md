# Preparation validation

Validated on 13 September 2026 using the reference Python 3.13.2 environment.

- Created a temporary destination inside Storage with a different absolute path.
- Copied only the preparation helper, frozen selection/source manifests, and
  required Git-tracked inputs into the destination's inner `ACL 2027` directory.
- Omitted the Dreaddit working records and GoEmotions source files.
- Ran `prepare.py --download-missing` in that destination.
- Downloaded the recorded public sources with TLS verification and checked hashes.
- Rebuilt Dreaddit and obtained reference SHA-256
  `86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a`.
- Verified all four datasets' ordered 20 adaptation and 100 evaluation IDs, text
  hashes, unique IDs and adaptation/evaluation disjointness.
- The command returned `status: verified` with `inference_calls: 0`.
- Removed the temporary destination after checking it. No original dataset,
  active experiment, model configuration, or result was changed by the check.

The initial clean-destination test found an unconfigured default certificate
store in the macOS Python environment. The helper now uses the pinned certifi CA
bundle when available, with certificate verification enabled. The subsequent
complete download/rebuild check passed.

The pure Native and rubric helpers were extracted from the recorded local source.
Official ACE dependency files remain unchanged from their pinned export. The
execution agent must still implement and test the new ACE-only runner. No claim
of completed ACE evaluation, exact cross-hardware output identity, or tested
runner recovery is made by this preparation check.
