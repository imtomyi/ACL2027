# Working Table 3 plus WarrantRoute-C

Retrospective personal-local diagnostic only. Not manuscript eligible.

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
| Dreaddit | WarrantRoute | Qwen3 8B | 75/100 | 75.0 [65.7, 82.5] |
| Dreaddit | WarrantRoute | Llama 3.1 8B | 14/100 | 14.0 [8.5, 22.1] |
| Dreaddit | WarrantRoute | Gemma 3 4B | 76/100 | 76.0 [66.8, 83.3] |
| Dreaddit | WarrantRoute-S | Qwen3 8B | 75/100 | 75.0 [65.7, 82.5] |
| Dreaddit | WarrantRoute-S | Llama 3.1 8B | 35/100 | 35.0 [26.4, 44.7] |
| Dreaddit | WarrantRoute-S | Gemma 3 4B | 81/100 | 81.0 [72.2, 87.5] |
| Dreaddit | WarrantRoute-C | Qwen3 8B | 71/100 | 71.0 [61.5, 79.0] |
| Dreaddit | WarrantRoute-C | Llama 3.1 8B | 22/100 | 22.0 [15.0, 31.1] |
| Dreaddit | WarrantRoute-C | Gemma 3 4B | 86/100 | 86.0 [77.9, 91.5] |
| GoEmotion | Generalist | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| GoEmotion | Generalist | Llama 3.1 8B | 56/100 | 56.0 [46.2, 65.3] |
| GoEmotion | Generalist | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] |
| GoEmotion | Fixed role | Qwen3 8B | 84/100 | 84.0 [75.6, 89.9] |
| GoEmotion | Fixed role | Llama 3.1 8B | 56/100 | 56.0 [46.2, 65.3] |
| GoEmotion | Fixed role | Gemma 3 4B | 79/100 | 79.0 [70.0, 85.8] |
| GoEmotion | All roles | Qwen3 8B | 91/100 | 91.0 [83.8, 95.2] |
| GoEmotion | All roles | Llama 3.1 8B | 76/100 | 76.0 [66.8, 83.3] |
| GoEmotion | All roles | Gemma 3 4B | 80/100 | 80.0 [71.1, 86.7] |
| GoEmotion | WarrantRoute | Qwen3 8B | 83/100 | 83.0 [74.5, 89.1] |
| GoEmotion | WarrantRoute | Llama 3.1 8B | 45/100 | 45.0 [35.6, 54.8] |
| GoEmotion | WarrantRoute | Gemma 3 4B | 69/100 | 69.0 [59.4, 77.2] |
| GoEmotion | WarrantRoute-S | Qwen3 8B | 75/100 | 75.0 [65.7, 82.5] |
| GoEmotion | WarrantRoute-S | Llama 3.1 8B | 71/100 | 71.0 [61.5, 79.0] |
| GoEmotion | WarrantRoute-S | Gemma 3 4B | 73/100 | 73.0 [63.6, 80.7] |
| GoEmotion | WarrantRoute-C | Qwen3 8B | 75/100 | 75.0 [65.7, 82.5] |
| GoEmotion | WarrantRoute-C | Llama 3.1 8B | 56/100 | 56.0 [46.2, 65.3] |
| GoEmotion | WarrantRoute-C | Gemma 3 4B | 73/100 | 73.0 [63.6, 80.7] |
| CaChe | Generalist | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| CaChe | Generalist | Llama 3.1 8B | 27/100 | 27.0 [19.3, 36.4] |
| CaChe | Generalist | Gemma 3 4B | 57/100 | 57.0 [47.2, 66.3] |
| CaChe | Fixed role | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| CaChe | Fixed role | Llama 3.1 8B | 30/100 | 30.0 [21.9, 39.6] |
| CaChe | Fixed role | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] |
| CaChe | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] |
| CaChe | All roles | Llama 3.1 8B | 55/100 | 55.0 [45.2, 64.4] |
| CaChe | All roles | Gemma 3 4B | 71/100 | 71.0 [61.5, 79.0] |
| CaChe | WarrantRoute | Qwen3 8B | 80/100 | 80.0 [71.1, 86.7] |
| CaChe | WarrantRoute | Llama 3.1 8B | 11/100 | 11.0 [6.3, 18.6] |
| CaChe | WarrantRoute | Gemma 3 4B | 55/100 | 55.0 [45.2, 64.4] |
| CaChe | WarrantRoute-S | Qwen3 8B | 80/100 | 80.0 [71.1, 86.7] |
| CaChe | WarrantRoute-S | Llama 3.1 8B | 41/100 | 41.0 [31.9, 50.8] |
| CaChe | WarrantRoute-S | Gemma 3 4B | 65/100 | 65.0 [55.3, 73.6] |
| CaChe | WarrantRoute-C | Qwen3 8B | 80/100 | 80.0 [71.1, 86.7] |
| CaChe | WarrantRoute-C | Llama 3.1 8B | 27/100 | 27.0 [19.3, 36.4] |
| CaChe | WarrantRoute-C | Gemma 3 4B | 68/100 | 68.0 [58.3, 76.3] |
| ParlaMint-GB | Generalist | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| ParlaMint-GB | Generalist | Llama 3.1 8B | 24/100 | 24.0 [16.7, 33.2] |
| ParlaMint-GB | Generalist | Gemma 3 4B | 48/100 | 48.0 [38.5, 57.7] |
| ParlaMint-GB | Fixed role | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] |
| ParlaMint-GB | Fixed role | Llama 3.1 8B | 36/100 | 36.0 [27.3, 45.8] |
| ParlaMint-GB | Fixed role | Gemma 3 4B | 67/100 | 67.0 [57.3, 75.4] |
| ParlaMint-GB | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] |
| ParlaMint-GB | All roles | Llama 3.1 8B | 52/100 | 52.0 [42.3, 61.5] |
| ParlaMint-GB | All roles | Gemma 3 4B | 69/100 | 69.0 [59.4, 77.2] |
| ParlaMint-GB | WarrantRoute | Qwen3 8B | 74/100 | 74.0 [64.6, 81.6] |
| ParlaMint-GB | WarrantRoute | Llama 3.1 8B | 15/100 | 15.0 [9.3, 23.3] |
| ParlaMint-GB | WarrantRoute | Gemma 3 4B | 56/100 | 56.0 [46.2, 65.3] |
| ParlaMint-GB | WarrantRoute-S | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| ParlaMint-GB | WarrantRoute-S | Llama 3.1 8B | 39/100 | 39.0 [30.0, 48.8] |
| ParlaMint-GB | WarrantRoute-S | Gemma 3 4B | 62/100 | 62.0 [52.2, 70.9] |
| ParlaMint-GB | WarrantRoute-C | Qwen3 8B | 73/100 | 73.0 [63.6, 80.7] |
| ParlaMint-GB | WarrantRoute-C | Llama 3.1 8B | 24/100 | 24.0 [16.7, 33.2] |
| ParlaMint-GB | WarrantRoute-C | Gemma 3 4B | 64/100 | 64.0 [54.2, 72.7] |
