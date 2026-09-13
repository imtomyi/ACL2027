# Saved experiment checkpoint

Dreaddit predictions and Conformability are paused by user request to prioritize offline adaptation on other datasets. DC GT yes has 97 committed predictions. An interrupted item's intermediate DC checkpoint is retained, allowing cached prediction reuse on resume. Existing completed rows and 588 Base quality judgments are preserved.

The run copy includes method state, memory, intermediate responses, optimizer artifacts, logs and frozen configuration. Source code and preparation manifests are copied separately. SHA256.json inventories copied files. This directory is a snapshot, not an active inference queue.

Resume using the original runtime313/bin/python and source supervise.py. Start conformability.py only after the prediction queue reports running so it waits without competing for inference. No resume was launched during this save.
