# ACE source dependencies

This directory contains the official ACE source files needed by the local corpus
experiments, plus the official README, extension instructions, license, example
adapters, dependency metadata, and paper PDF.

- Source: https://github.com/ace-agent/ace
- Commit: `82709de050e1db6e6ef2f07bcb0393560b94992a`
- Inventory and file hashes: [PROVENANCE.json](PROVENANCE.json)
- Execution guide: [ACE Local Reproduction Guide](../Storage/ace_reproduction_20260913/ACE_LOCAL_REPRODUCTION_GUIDE.md)

The corpus runners resolve `original_sources/ace` from the enclosing `ACL 2027`
project directory. They no longer require a sibling `ace_paper` directory.
Copied upstream files are unchanged. The AppWorld submodule and its environments
are not included because these four-corpus experiments do not use AppWorld.
This is a source export, not a Git checkout or a complete AppWorld installation.
The upstream finance example data are retained with the source export; they are
not inputs to the local four-corpus comparison.

The original external directory is preserved. The path migration and original
configurations are recorded in
`../Storage/ace_path_migration_20260913/`. Existing predictions, role caches,
reference annotations, model settings, and scientific protocol fields were not
changed by that migration.
