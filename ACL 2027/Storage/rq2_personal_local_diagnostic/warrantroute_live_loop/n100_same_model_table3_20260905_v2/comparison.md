# WarrantRoute n=100 working comparison

Private diagnostic results. Acceptance is a loop decision, not a repair-quality score.

| Dataset | Configuration | Method | Seed | TP/N | Recall | Calls | Seconds |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cache | qwen_only | warrantroute | 20260905 | 100/100 | 1.000 | 7.05 | 152.60 |
| cache | llama_only | warrantroute | 20260905 | 64/100 | 0.640 | 6.03 | 88.79 |
| cache | gemma_only | warrantroute | 20260905 | 55/100 | 0.550 | 6.02 | 46.84 |
| dreaddit | qwen_only | warrantroute | 20260905 | 99/100 | 0.990 | 6.30 | 130.21 |
| dreaddit | llama_only | warrantroute | 20260905 | 68/100 | 0.680 | 6.00 | 82.93 |
| dreaddit | gemma_only | warrantroute | 20260905 | 42/100 | 0.420 | 6.24 | 50.38 |
| goemotions | qwen_only | warrantroute | 20260905 | 100/100 | 1.000 | 6.06 | 114.44 |
| goemotions | llama_only | warrantroute | 20260905 | 63/100 | 0.630 | 6.00 | 78.95 |
| goemotions | gemma_only | warrantroute | 20260905 | 47/100 | 0.470 | 7.10 | 50.70 |
| parlamint-gb | qwen_only | warrantroute | 20260905 | 100/100 | 1.000 | 6.60 | 152.46 |
| parlamint-gb | llama_only | warrantroute | 20260905 | 67/100 | 0.670 | 6.06 | 99.04 |
| parlamint-gb | gemma_only | warrantroute | 20260905 | 50/100 | 0.500 | 5.92 | 68.08 |
