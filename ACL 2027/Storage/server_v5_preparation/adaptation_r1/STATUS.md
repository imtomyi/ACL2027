# Historical ACE/DC r1 execution status

**Stopped for the separately versioned r2 format repair. The text below records the original r1 launch, not the current execution state. Do not resume r1 automatically.**

ACE/DC production started: 33 seed runs admitted, 21 withheld after development failures. Latest mirrored snapshot 2026-09-14T04:43:56.109504+00:00: 24 valid evaluation predictions, 18 updates; 8 active, 25 queued.

[RESULTS.md](RESULTS.md) · [METRICS.md](METRICS.md). The admitted prediction target is 3,300; the full planned ACE/DC stage remains 5,400 across 54 seed runs. Withheld conditions are not completed or failed test runs: they never started evaluation.

Eleven of eighteen corpus/phase/method/GT development cases passed, using the shortest and longest real development sources. The eleven passing conditions each run seeds 42/43/44. All seven software behavior tests passed locally and on server.

Pending fixes: GoEmotions ACE offline/online GT yes/no (12 seed runs), CaChe ACE offline GT no (3), and Dreaddit DC online GT yes/no (6). Preserve the failed probes and sealed production artifacts; fixes require a separate declared stage. MIPROv2/GEPA and judging are separate pending work.

Pipeline PID 2358664/start identity 58516651. Server stage: `/home/sy23985/Storage/acl2027_server_v5_20260914/stages/adaptation_r1`. Seal: `6f2c9c9c4cb050413aa8eaf215b1ea250bf3593eac1832564f00188e8aad3906`.

The first archive extraction attempt used the old system Python; switching setup to the pinned Python 3.13 runtime fixed it before inference. No inference was discarded by that repair.
