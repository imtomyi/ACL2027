# AMI source and attribution

This internal experiment uses the AMI Meeting Corpus manual annotations,
official artifact `ami_public_manual_1.6.2.zip`, under the Creative Commons
Attribution 4.0 International license.

- AMI Corpus: <https://groups.inf.ed.ac.uk/ami/corpus/>
- Official download: <https://groups.inf.ed.ac.uk/ami/download/>
- License: <https://creativecommons.org/licenses/by/4.0/>
- Snapshot SHA-256:
  `b56e5babb2496b8795deeeda7e71178d7fbc9963f94276cf2a3f4b56ebbc9f9d`

The official filename labels the artifact version 1.6.2. Its embedded README
uses the label release 1.7. This experiment does not equate those labels and
identifies the source by URL, filename, byte length, and checksum.

Suggested scholarly citation:

Jean Carletta et al. (2006). “The AMI Meeting Corpus: A Pre-announcement.”
Machine Learning for Multimodal Interaction. DOI: 10.1007/11677482_3.

Modifications made here are limited to local transcript-token extraction,
role-preserving aggregation, TF-IDF transformation, and aggregate statistical
analysis. Raw identifiers are retained only transiently in memory for split
validation; no identifier or per-meeting record is exported. No endorsement by
the AMI Project is implied.
