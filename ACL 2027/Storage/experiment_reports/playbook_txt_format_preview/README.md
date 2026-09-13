# TXT Playbook Format Preview

This is an offline rendering of the two existing initial seed rules for each
dataset, not a running experiment and not newly learned Playbook content.
The user-provided API/code rules were format examples and are not included.

Open `playbooks/dreaddit/current.txt`, `playbooks/goemotions/current.txt`,
`playbooks/cache/current.txt`, or `playbooks/parlamint-gb/current.txt`.
The four seed files initially have identical wording. In a future authorized
run, each corpus keeps its own independently updated memory and history.

The runtime now publishes this format after each committed query, following
approved add/refine/reinforce decisions. Stable numbered IDs survive refinement.
No-change and rejected proposals do not force growth. JSON remains the validated
state, and the model receives the same TXT projection of its retrieved rules.
Manual changes to a generated TXT are not imported into the experiment.

Offline verification: 168 tests passed, including TXT prompt equivalence,
stable IDs, revision history, next-query use and recovery without model redraw.
No live inference was performed to create this preview. Previous frozen runs
remain unchanged and the previous experiment remains paused.
