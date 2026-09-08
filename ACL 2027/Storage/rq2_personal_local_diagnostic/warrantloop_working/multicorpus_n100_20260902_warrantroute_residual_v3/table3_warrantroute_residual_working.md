# Working Table 3 with WarrantRoute residual discovery

Retrospective personal-local diagnostic only. Not manuscript eligible.

Scientific interpretation gate: **FAILED**. The development claims contain deterministic flaw-label templates, so these values are pipeline diagnostics, not evidence that WarrantRoute is superior.

| Dataset | Method | Model | TP/N | Recall (%) ↑ |
| --- | --- | --- | --- | --- |
| Dreaddit | Generalist | Qwen3 8B | 67/100 | 67.0 [57.3, 75.4] |
| Dreaddit | Generalist | Llama 3.1 8B | 16/100 | 16.0 [10.1, 24.4] |
| Dreaddit | Generalist | Gemma 3 4B | 73/100 | 73.0 [63.6, 80.7] |
| Dreaddit | Fixed role | Qwen3 8B | 76/100 | 76.0 [66.8, 83.3] |
| Dreaddit | Fixed role | Llama 3.1 8B | 37/100 | 37.0 [28.2, 46.8] |
| Dreaddit | Fixed role | Gemma 3 4B | 83/100 | 83.0 [74.5, 89.1] |
| Dreaddit | All roles | Qwen3 8B | 77/100 | 77.0 [67.8, 84.2] |
| Dreaddit | All roles | Llama 3.1 8B | 52/100 | 52.0 [42.3, 61.5] |
| Dreaddit | All roles | Gemma 3 4B | 89/100 | 89.0 [81.4, 93.7] |
| Dreaddit | WarrantRoute | Qwen3 8B | 99/100 | 99.0 [94.6, 99.8] |
| Dreaddit | WarrantRoute | Llama 3.1 8B | 70/100 | 70.0 [60.4, 78.1] |
| Dreaddit | WarrantRoute | Gemma 3 4B | 99/100 | 99.0 [94.6, 99.8] |
| GoEmotion | Generalist | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| GoEmotion | Generalist | Llama 3.1 8B | 56/100 | 56.0 [46.2, 65.3] |
| GoEmotion | Generalist | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] |
| GoEmotion | Fixed role | Qwen3 8B | 84/100 | 84.0 [75.6, 89.9] |
| GoEmotion | Fixed role | Llama 3.1 8B | 56/100 | 56.0 [46.2, 65.3] |
| GoEmotion | Fixed role | Gemma 3 4B | 79/100 | 79.0 [70.0, 85.8] |
| GoEmotion | All roles | Qwen3 8B | 91/100 | 91.0 [83.8, 95.2] |
| GoEmotion | All roles | Llama 3.1 8B | 76/100 | 76.0 [66.8, 83.3] |
| GoEmotion | All roles | Gemma 3 4B | 80/100 | 80.0 [71.1, 86.7] |
| GoEmotion | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [96.3, 100.0] |
| GoEmotion | WarrantRoute | Llama 3.1 8B | 100/100 | 100.0 [96.3, 100.0] |
| GoEmotion | WarrantRoute | Gemma 3 4B | 100/100 | 100.0 [96.3, 100.0] |
| CaChe | Generalist | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| CaChe | Generalist | Llama 3.1 8B | 27/100 | 27.0 [19.3, 36.4] |
| CaChe | Generalist | Gemma 3 4B | 57/100 | 57.0 [47.2, 66.3] |
| CaChe | Fixed role | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| CaChe | Fixed role | Llama 3.1 8B | 30/100 | 30.0 [21.9, 39.6] |
| CaChe | Fixed role | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] |
| CaChe | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] |
| CaChe | All roles | Llama 3.1 8B | 55/100 | 55.0 [45.2, 64.4] |
| CaChe | All roles | Gemma 3 4B | 71/100 | 71.0 [61.5, 79.0] |
| CaChe | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [96.3, 100.0] |
| CaChe | WarrantRoute | Llama 3.1 8B | 76/100 | 76.0 [66.8, 83.3] |
| CaChe | WarrantRoute | Gemma 3 4B | 100/100 | 100.0 [96.3, 100.0] |
| ParlaMint-GB | Generalist | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| ParlaMint-GB | Generalist | Llama 3.1 8B | 24/100 | 24.0 [16.7, 33.2] |
| ParlaMint-GB | Generalist | Gemma 3 4B | 48/100 | 48.0 [38.5, 57.7] |
| ParlaMint-GB | Fixed role | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| ParlaMint-GB | Fixed role | Llama 3.1 8B | 36/100 | 36.0 [27.3, 45.8] |
| ParlaMint-GB | Fixed role | Gemma 3 4B | 67/100 | 67.0 [57.3, 75.4] |
| ParlaMint-GB | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] |
| ParlaMint-GB | All roles | Llama 3.1 8B | 52/100 | 52.0 [42.3, 61.5] |
| ParlaMint-GB | All roles | Gemma 3 4B | 69/100 | 69.0 [59.4, 77.2] |
| ParlaMint-GB | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [96.3, 100.0] |
| ParlaMint-GB | WarrantRoute | Llama 3.1 8B | 74/100 | 74.0 [64.6, 81.6] |
| ParlaMint-GB | WarrantRoute | Gemma 3 4B | 98/100 | 98.0 [93.0, 99.4] |
