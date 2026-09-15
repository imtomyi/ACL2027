# Terminal progress viewer

In the existing server SSH terminal, run:

```sh
~/acl-progress
```

Refreshes every five seconds. Ctrl+C exits only the viewer; experiments continue independently. Read-only: it reads manifests, status/checkpoint metadata and NVIDIA GPU telemetry; it does not read source records, generated answers, GT labels or playbooks.

```sh
~/acl-progress --all       # Include every known condition
~/acl-progress --once      # Print one snapshot
~/acl-progress --interval 10
```

The display separates valid/attempted predictions, adaptation attempts, committed updates, judgments, queue/held/failed states, and GPU utilization. Full-panel totals select the latest admitted revision per condition to avoid double-counting reruns. Prediction completion is separate from judging completion. Full ETA stays unavailable while required methods or judgments remain unstarted.

Installed script: `/home/sy23985/Storage/acl2027_server_v5_20260914/monitor/progress.py`. Launcher: `/home/sy23985/acl-progress`. It is outside every existing execution seal. The one-shot output and continuous refresh/interrupt were verified on the server.
