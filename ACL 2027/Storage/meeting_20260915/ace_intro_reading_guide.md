# ACE 논문 Introduction 읽기 가이드 — 인용 논문의 내용과 인용 의도

대상: Zhang et al., "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models", ICLR 2026 (OpenReview `eC4ygDs02R`, arXiv 2510.04618v3 camera-ready). 로컬 파일: `ace_paper/original_sources/paper/ace_arxiv_2510.04618.pdf`, 1–2쪽.

각 인용마다 세 가지를 적었습니다.

- **내용**: 인용된 논문이 실제로 무엇을 했는가
- **의도**: ACE 저자가 이 문장에서 그 논문을 왜 끌어왔는가
- **메모**: 인용이 주장을 얼마나 잘 받쳐 주는지, 자기 인용 여부, 우리 실험과의 연결

---

## 0. 인트로의 논리 흐름 (5문단 + 핵심 발견)

| 문단 | 한 줄 요약 | 역할 |
| --- | --- | --- |
| ¶1 | LLM 시스템은 가중치가 아니라 **컨텍스트를 바꿔서** 적응하는 쪽으로 가고 있다 | 판 깔기: context adaptation이 중심 패러다임 |
| ¶2 | 기존 방법에는 **brevity bias**와 **context collapse**라는 두 한계가 있다 | 문제 제기 |
| ¶3 | 컨텍스트는 요약본이 아니라 **길고 자세한 playbook**이어야 한다. LLM은 긴 컨텍스트에서 스스로 관련 정보를 고른다 | 입장 선언 (ACE의 철학) |
| ¶4 | ACE = generation → reflection → curation, 증분(delta) 업데이트, grow-and-refine | 해법 소개 |
| ¶5 + bullet | agent(AppWorld)와 금융 도메인(FiNER, Formula)에서 평가. +10.6% / +8.6%, 라벨 없이도 가능, 리더보드 1위급, 비용 절감 | 증거 요약 |

인용이 가장 많은 곳은 ¶1과 ¶2입니다. ¶1은 "이 분야가 넓고 중요하다"는 **배경 인용**이 대부분이고, ¶2–¶3은 ACE의 핵심 주장을 받치는 **논증 인용**입니다. 꼼꼼히 봐야 하는 것은 ¶2–¶3과 ¶5의 bullet입니다.

### Figure 1 (인트로 첫 그림)

DeepSeek-V3.1 기준 정확도(%):

| 벤치마크 | Base LLM | ICL | GEPA | DC | ACE |
| --- | ---: | ---: | ---: | ---: | ---: |
| AppWorld (agent) | 42.4 | 46.0 | 46.4 | 51.9 | 59.5 |
| FiNER (도메인 지식) | 70.7 | 72.3 | 73.5 | 74.2 | 78.3 |
| Formula (수치 추론) | 67.5 | 67.0 | 71.5 | 69.5 | 76.5 |

비교 대상 네 가지(ICL, GEPA, DC, Base)가 곧 이 논문의 baseline 구도입니다. ¶1–¶2의 인용도 이 구도에 맞춰 배치되어 있습니다. GEPA와 MIPRO는 system prompt 최적화 대표로, DC는 memory 대표로 등장합니다.

---

## ¶1. Context adaptation이 중심 패러다임이다

### 문장 1 — "LLM agents와 compound AI systems는 점점 context adaptation에 의존한다"

**ReAct** (Yao et al., ICLR 2023)
- 내용: 모델이 추론(Thought)과 행동(Action: 검색, 도구 호출)을 번갈아 생성하는 프롬프팅 방식입니다. HotpotQA, FEVER, ALFWorld, WebShop에서 추론만 하거나 행동만 하는 방식보다 좋았습니다.
- 의도: "LLM agent"의 대표 사례로 들었습니다. ACE의 AppWorld 실험은 공식 ReAct 에이전트 위에 컨텍스트를 얹는 구조(ReAct + ACE)라서, 이 인용은 실험 베이스라인의 출처이기도 합니다.

**SWE-agent** (Yang et al., NeurIPS 2024)
- 내용: LM 전용 명령어(파일 열기, 검색, 편집)로 이루어진 agent-computer interface(ACI)를 설계해 SWE-bench 성능을 크게 올렸습니다. 모델보다 **인터페이스와 컨텍스트 설계**가 성능을 좌우한다는 메시지입니다.
- 의도: 코딩 에이전트의 대표 사례입니다. 가중치를 건드리지 않고 입력 환경만 바꿔 성능을 올린 예로 쓰였습니다.

**The Shift from Models to Compound AI Systems** (Zaharia et al., BAIR 블로그, 2024)
- 내용: 최신 SOTA는 단일 모델보다 여러 모델, 검색기, 도구를 엮은 "compound AI system"에서 나온다는 주장입니다.
- 의도: 컨텍스트를 시스템 구성요소로 보는 프레임을 가져왔습니다.
- 메모: 동료 심사를 거친 논문이 아닌 블로그 글입니다. 저자진(Khattab, Potts, Zaharia)은 DSPy, MIPRO, GEPA와 같은 생태계에 속합니다.

### 문장 3 — 컨텍스트가 떠받치는 세 가지 구성요소

**(a) System prompt**

**MIPRO** (Opsahl-Ong et al., EMNLP 2024)
- 내용: DSPy로 짠 다단계 LM 프로그램에서 각 모듈의 **instruction과 few-shot 예시를 함께** 최적화합니다.
  - 후보 생성: bootstrapped demo, 데이터와 프로그램을 참고한 instruction 제안
  - 조합 탐색: Bayesian surrogate 모델
  - 결과: Llama-3-8B로 7개 과제 중 5개에서 기존 최적화기보다 높았습니다(최대 13%p).
- 의도: offline "system prompt 최적화"의 대표입니다.
- 메모: 우리 v5의 MIPROv2 조건이 바로 이 방법입니다. DSPy 구현을 그대로 썼습니다.

**GEPA** (Agrawal et al., arXiv 2025)
- 내용: 실행 trace(추론 과정, 도구 출력, 평가 피드백)를 LLM이 자연어로 반성해 프롬프트를 **변이**시킵니다. 후보는 **Pareto front**, 즉 과제 인스턴스별로 가장 좋은 후보들을 유지하는 방식으로 고릅니다. GRPO(강화학습)보다 훨씬 적은 rollout으로 더 높은 성능을 냈고, MIPROv2보다도 우수하다고 보고했습니다.
- 의도: 가장 강한 prompt-optimizer baseline이자, 바로 다음 문단에서 brevity bias의 **표적**이 됩니다. 여기서 먼저 소개해 두는 것입니다.

**(b) Memory**

**Dynamic Cheatsheet (DC)** (Suzgun et al., 2025)
- 내용: test-time에 문제를 풀어 가면서, 재사용 가능한 전략과 코드 조각을 "cheatsheet" 메모리에 누적합니다. 변형은 두 가지입니다.
  - DC-Cu (cumulative): 매번 전체 cheatsheet을 다시 씀
  - DC-RS (retrieval & synthesis)
  - 결과: 수학(AIME), Game of 24 같은 과제에서 큰 폭으로 향상됐습니다.
- 의도: 두 가지입니다. 첫째, "memory" 방식의 대표 사례입니다. 둘째, ACE의 직접적인 선조입니다. §3에서 ACE는 DC의 agentic 설계에서 영감을 받았다고 밝힙니다. 또 ¶2의 context collapse 사례(Figure 2)가 바로 DC-Cu입니다.
- 메모:
  - James Zou가 DC와 ACE의 공저자입니다. 같은 계보의 후속작이 선행작의 약점을 짚는 구조입니다.
  - 우리 v5의 "DC (CU)" 조건이 이것입니다.
  - §2.1에서는 DC를 "Krause et al., 2019"로 잘못 인용했습니다. Krause 2019는 Dynamic *Evaluation* 논문입니다. 본문 인용 오류이니 발표 때 참고하세요.

**A-Mem** (Xu et al., NeurIPS 2025)
- 내용: Zettelkasten 방식의 에이전트 메모리입니다. 기억마다 키워드, 태그, 설명이 붙은 노트를 만들고, 노트끼리 링크를 생성합니다. 새 기억이 들어오면 기존 노트도 갱신합니다(memory evolution).
- 의도: 구조화된 에이전트 memory의 사례입니다.
- 메모: "구조화하되 계속 진화하는 메모리"라는 점에서 ACE playbook과 발상이 가깝습니다. 그런데 본문 비교는 없습니다.

**(c) Factual evidence**

**Self-RAG** (Asai et al., ICLR 2024)
- 내용: 모델이 reflection token을 직접 생성해 판단합니다. 대상은 검색이 필요한지, 검색 문서가 관련 있는지, 답이 문서로 지지되는지, 답이 유용한지입니다.
- 의도: 외부 증거를 컨텍스트에 넣으면 hallucination이 줄어든다는 사례입니다.

### 문장 4 — 가중치 대신 컨텍스트로 적응하는 것의 장점 세 가지

**(1) 해석 가능성**

**Chain-of-Thought** (Wei et al., NeurIPS 2022), **Self-Consistency** (Wang et al., ICLR 2023)
- 내용:
  - CoT: 예시에 중간 추론 단계를 넣으면 대형 모델의 추론 성능이 오릅니다.
  - Self-Consistency: 여러 추론 경로를 샘플링한 뒤 다수결로 답을 고릅니다.
- 의도: 컨텍스트(추론 단계)는 사람이 읽을 수 있다는 근거입니다.
- 메모: **느슨한 인용입니다.** 두 논문의 주장은 "성능 향상"이지 "해석 가능성"이 아닙니다. CoT가 모델의 실제 추론을 충실히 반영하지 않을 수 있다는 반론(CoT faithfulness)도 있습니다. 배경 문장이라 크게 문제 삼을 부분은 아닙니다.

**(2) 런타임에 새 지식을 빠르게 반영**

**RAG** (Lewis et al., NeurIPS 2020)
- 내용: DPR 검색기와 BART 생성기를 결합했습니다. 비모수 메모리(위키 인덱스)만 바꾸면 재학습 없이 지식을 갱신할 수 있습니다.

**RETRO** (Borgeaud et al., ICML 2022)
- 내용: 2조 토큰 DB에서 청크를 검색해 chunked cross-attention으로 참조합니다. 7.5B 모델이 25배 큰 모델급 성능을 냈습니다.

- 의도(두 논문 공통): 가중치를 고치지 않고 입력만 바꿔 지식을 추가할 수 있다는 근거입니다.

**(3) 모델과 모듈 사이의 공유**

**Decomposed Prompting** (Khot et al., ICLR 2023)
- 내용: 복잡한 과제를 하위 과제로 나누고, 각 하위 과제 handler(프롬프트, 다른 모델, 심볼릭 함수)를 모듈처럼 바꿔 끼웁니다.
- 의도: 컨텍스트는 compound system 안의 여러 모듈이 공유할 수 있다는 근거입니다.
- 메모: "여러 **모델** 간 공유"를 직접 보인 논문은 아닙니다. 모듈식 프롬프트 설계에 대한 근거입니다.

### 문장 5 — 이제 실용적이다: 긴 컨텍스트와 효율적 추론

**YaRN** (Peng et al., ICLR 2024)
- 내용: RoPE 위치 인코딩 보간을 개선해, 적은 추가 학습으로 context window를 크게(예: 128k) 늘립니다.
- 의도: 긴 playbook을 넣을 수 있는 기술적 기반이라는 근거입니다.
- 메모: 우리가 쓰는 Qwen3-8B는 기본 32,768 토큰입니다. YaRN으로 131k까지 확장을 지원하지만, 우리 실험은 32k로 고정했습니다. 따라서 "긴 컨텍스트가 실용적"이라는 전제가 우리 설정에서는 약합니다. AppWorld의 context exhausted 카운트가 그 증거입니다.

**Prompt Cache** (Gim et al., MLSys 2024)
- 내용: 자주 반복되는 프롬프트 조각(모듈)의 attention state를 미리 계산해 재사용합니다. 조각 구조는 Prompt Markup Language로 정의합니다. 첫 토큰 지연(TTFT)이 크게 줄었습니다.

**CacheBlend** (Yao et al., EuroSys 2025)
- 내용: RAG에서 prefix가 아닌 위치에 오는 여러 문서 청크의 KV cache를 재사용합니다. 대신 일부 토큰만 선택적으로 재계산해 청크 사이 cross-attention 품질을 회복합니다.

- 의도(두 논문 공통): playbook은 대부분 고정되어 있으니 KV 캐시를 재사용하면 긴 컨텍스트 비용이 줄어든다는 논리를 받칩니다. 이 논리는 결론의 비용 논의로 이어집니다.
- 메모: CacheBlend는 ACE 1저자 Qizheng Zhang과 Hanchen Li의 공저로, **자기 인용**입니다. ACE 저자진이 원래 시스템(KV cache) 연구자라는 배경이 여기서 드러납니다.

---

## ¶2. 두 가지 한계: brevity bias와 context collapse

### Brevity bias

**GEPA** (Agrawal et al., 2025) — 재등장
- 내용: GEPA 논문은 자기 방식이 만든 최적화 프롬프트(instruction-only)가 MIPROv2의 프롬프트(데모 포함)보다 훨씬 짧아서 추론 비용이 싸다는 점을 **장점**으로 보고했습니다.
- 의도: 가장 강한 경쟁자의 **설계 가치 자체**를 문제로 규정하는 프레이밍입니다. 짧은 게 장점이라고 하지만, 그 추상화 과정에서 도메인 휴리스틱, 도구 사용 요령, 흔한 실패 유형이 빠진다는 것입니다.
- 메모 (공정성 체크):
  - GEPA의 목적함수는 짧음을 직접 최적화하지 않습니다. 짧은 결과는 부산물입니다.
  - 논문도 이 편향이 **"일부 설정에서는 validation 지표와 맞아떨어진다"**고 인정합니다(원문 "aligns with validation metrics in some settings").
  - 우리 Dreaddit에서 GEPA가 +9.7점으로 ACE GT✗ 두 조건보다 높았습니다. 짧은 판정 규칙으로 충분한 이진 분류는 바로 그 "일부 설정"일 수 있습니다.

**The Prompt Alchemist (MAPS)** (Gao et al., arXiv 2025)
- 내용: 테스트 케이스 생성용 프롬프트 최적화 연구입니다. 기존 자동 프롬프트 최적화법을 돌려 보니, 반복할수록 거의 같은 짧은 지시문으로 수렴했습니다. §2.2에 인용된 예시는 "Create unit tests to ensure methods behave as expected"입니다. 결과적으로 다양성이 떨어지고 도메인 지식이 빠졌습니다. 이를 해결하려고 MAPS의 세 모듈을 제안했습니다.
  - 다양성 유도 프롬프트 생성
  - 실패 기반 규칙 유도
  - 도메인 컨텍스트 지식 추출
- 의도: brevity bias의 **유일한 외부 경험적 근거**입니다.
- 메모: 단일 도메인(코드 테스트 생성) 근거이고, GEPA를 직접 분석한 논문도 아닙니다. 따라서 "GEPA에 brevity bias가 있다"는 주장은 GEPA 논문의 서술과 이 간접 근거를 조합한 것입니다.

### Context collapse

- 인용 없이 **자체 관찰**(Figure 2)로 제시합니다.
- 관찰 내용: AppWorld에서 DC가 매 스텝 컨텍스트 전체를 다시 쓰다가 급변했습니다.

  | 시점 | 컨텍스트 크기 | 정확도 |
  | --- | ---: | ---: |
  | step 60 | 18,282 토큰 | 66.7 |
  | step 61 | 122 토큰 | 57.1 |
  | 적응 없음 | — | 63.7 |

  step 61의 57.1은 적응하지 않은 경우(63.7)보다도 낮습니다.
- 메모: 한 번의 붕괴 사례이고, 얼마나 자주 일어나는지에 대한 통계는 없습니다. §2.2에서 "DC만의 문제가 아니라 end-to-end 재작성의 근본 위험"이라고 일반화하지만, 근거는 이 사례 하나입니다. 우리 v5의 DC(CU) memory 기록에서 같은 현상이 있었는지 확인하면 좋은 검증이 됩니다.

### "세부 지식을 버리면 안 되는 도메인" 예시 (3묶음)

이 문장의 인용들은 "이런 분야에서는 압축하면 손해"라는 **영역 예시**입니다. 인용된 논문 자체가 brevity나 collapse를 다룬 것은 아닙니다.

#### (1) Interactive agents

**AppWorld** (Trivedi et al., ACL 2024)
- 내용:
  - 구성: Amazon, Spotify, Venmo, Gmail 등을 본뜬 9개 앱, 457개 API, 100여 명의 가상 사용자, 750개 과제
  - 방식: 에이전트가 Python 코드로 API를 호출하고, **상태 기반 unit test**로 채점합니다(TGC: 과제 성공, SGC: 시나리오 성공).
  - 난이도: GPT-4o도 test-normal 약 49%, test-challenge 약 30% 수준이었습니다.
- 의도: ACE의 **주 벤치마크**입니다. ¶5에서 다시 인용됩니다.

**Gorilla** (Patil et al., NeurIPS 2024)
- 내용: API 호출 생성에 특화해 fine-tune한 LLaMA입니다. APIBench(HuggingFace, TorchHub, TensorHub)를 만들었고, retriever-aware training으로 API 문서 변경에 대응하고 hallucination을 줄였습니다.
- 의도: 도구 사용 에이전트에는 API별 세부 지식이 필요하다는 예시입니다.
- 메모: 역설적으로 Gorilla는 **가중치 학습**으로 푼 방법입니다.

**Caravan** (Zhang et al., OSDI 2024)
- 내용: 네트워크 장비 안에서 도는 ML 모델(in-network ML)을 온라인으로 학습시키는 시스템입니다. 휴리스틱, 접근제어 목록, foundation model을 labeling agent로 써서 변하는 트래픽에 자동으로 라벨을 붙이고, accuracy proxy로 재학습 시점을 잡습니다.
- 의도: 에이전트 활용 사례입니다.
- 메모: ACE 1저자와 Olukotun의 **자기 인용**입니다. "interactive agent" 예시로는 느슨합니다.

#### (2) Domain-specific programming

**SymGen** (Ye et al., EMNLP 2023)
- 내용: LLM으로 SQL, 코드 같은 기호 언어 과제의 학습 데이터를 생성합니다. 정보가 풍부한 프롬프트와 실행 기반 합의 검증을 씁니다. 그 데이터로 1% 크기의 모델이 LLM 수준에 도달했습니다.
- 의도: 기호 언어 과제에는 과제별 지식이 필요하다는 예시입니다.
- 메모: 데이터 생성 논문이라, "컨텍스트에 지식을 보존해야 한다"는 주장과는 간접적으로만 연결됩니다.

**Adaptive Self-improvement Agentic System for ML Library Development** (Zhang et al., ICML 2025a)
- 내용: 아키텍처 특화 언어(ASPL)로 ML 라이브러리(LLM 연산자)를 짜는 에이전트입니다. 자기가 생성한 경험을 누적해 반복적으로 개선하며, 26개 연산자 중 25개를 구현했고 단일 LLM 대비 최대 3.9배 좋았습니다.

**AccelOpt** (Zhang et al., arXiv 2025b)
- 내용: AWS Trainium 가속기 커널을 최적화하는 에이전트입니다. 느린 커널과 빠른 커널 쌍에서 얻은 통찰을 **optimization memory**에 누적합니다(NKIBench). 최고 처리량 대비 비율을 Trainium 1에서 49%→61%로 올렸습니다.

- 의도(2025a, 2025b 공통): 경험을 누적하는 self-improvement가 도메인 프로그래밍에서 통한다는 사례로, ACE와 철학이 같습니다.
- 메모: 둘 다 Olukotun 랩(ACE 교신저자)의 **자기 인용**입니다.

**FrontierCS** (Mang et al., arXiv 2025)
- 내용: 최적해는 알려져 있지 않지만 해의 품질은 객관적으로 채점할 수 있는 CS 문제 156개를 모은 벤치마크입니다(알고리즘 트랙, 연구 트랙). 프론티어 모델도 전문가에 한참 못 미쳤습니다.
- 의도: 세부 전략이 필요한 영역의 예시입니다.
- 메모:
  - ACE 저자 Hanchen Li가 공저자인 **자기 인용**입니다.
  - arXiv 등록이 2025년 12월로, ACE 첫 arXiv(2025년 10월)보다 늦습니다. AccelOpt(2025년 11월)와 함께 camera-ready에서 **추가된 인용**입니다.

#### (3) 금융·법률 분석

**FiNER-139** (Loukas et al., ACL 2022)
- 내용: 10-K/10-Q 공시 문장 110만 개에 139종의 XBRL 태그를 붙인 데이터셋입니다. 대부분 숫자 토큰이며, 숫자 엔티티를 올바른 회계 태그로 분류해야 합니다.
- 의도: ACE의 **도메인 벤치마크 1**입니다(Figure 1의 FiNER).

**LegalBench** (Guha et al., NeurIPS 2023)
- 내용: 법률 전문가들이 협업해 만든 162개 과제로, 6가지 법률 추론 유형을 다룹니다.
- 의도: 법률도 세부 지식이 필요하다는 예시입니다.
- 메모: ACE는 LegalBench로 **평가하지 않았습니다**. 영역 예시로만 인용했습니다.

**FinLoRA** (Wang et al., arXiv 2025a)
- 내용: 금융 데이터셋 19개로 LoRA fine-tuning 기법을 벤치마크했습니다. SEC 공시 150건 기반의 XBRL 분석 데이터셋 4종을 새로 만들었고, 그중 하나가 formula calculation입니다. 관련 태그와 값을 골라 재무 공식(예: Net Profit Margin)을 세우고 계산하는 과제입니다.
- 의도: ACE의 **도메인 벤치마크 2**인 "Formula"의 출처입니다(§4.1에서 "Formula (Wang et al., 2025a)"로 명시).
- 메모: 원래는 **가중치 학습(LoRA)** 벤치마크입니다. ACE는 같은 과제를 컨텍스트 적응으로 풀었습니다.

---

## ¶3. 입장: 컨텍스트는 길고 자세한 playbook이어야 한다

두 개의 주장이 있고, 각각 인용이 붙어 있습니다.

### 주장 A — "최근 연구는 유용할 수 있는 정보로 컨텍스트를 **포화**시키는 방향으로 이동했다"

**Putting It All into Context** (Jiang et al., arXiv 2025)
- 내용: 복잡한 에이전트 스캐폴딩 없이, 저장소 전체를 긴 컨텍스트 모델에 넣고 바로 행동을 생성하게 했습니다. SWE-bench Verified에서 Gemini-1.5-Pro가 38%로, 세심하게 튜닝한 스캐폴드(32%)와 비슷하거나 더 높았습니다.
- 의도: 긴 컨텍스트가 복잡한 파이프라인을 대체할 수 있다는 근거입니다.
- 메모: Gemini급 **강한 장문 모델**이 전제입니다.

**Is Long Context All You Need? (NL2SQL)** (Chung et al., VLDB 2025)
- 내용: Gemini-1.5-Pro에 스키마 전체, 컬럼 예시 값, 질문-SQL 예시, 힌트, SQL 문서까지 모두 넣었습니다. 긴 컨텍스트에서도 모델이 길을 잃지 않았고, fine-tuning이나 self-consistency 없이 BIRD 67.41%를 기록했습니다.
- 의도: 풍부한 컨텍스트가 정확도를 올린다는 근거입니다.
- 메모: 논문은 지연시간 비용과의 트레이드오프도 분석했습니다. ACE 인트로는 이 부분을 가져오지 않았습니다.

**Flora** (Chen et al., AAAI 2026)
- 내용: 사람이나 LLM 없이, 짧은 instruction들을 카테고리별로 임의 조립해 **임의 길이의 장문 SFT 학습 데이터**를 만드는 방법입니다. 장문 성능은 오르고 단문 성능 손실은 적었습니다.
- 의도: 장문 트렌드의 예시입니다.
- 메모: **인용 위치와 잘 맞지 않습니다.** 응용 단계에서 컨텍스트를 채우는 연구가 아니라, 장문 능력을 **학습시키는 데이터 구성** 연구입니다.

**YaRN** (재등장), **LIFT** (Mao et al., arXiv 2024)
- 내용: LIFT는 긴 입력을 test-time fine-tuning으로 **모델 파라미터에 저장**해, 짧은 context 모델의 장문 이해를 높입니다.
- 의도: "장문 LLM의 발전" 사례입니다.
- 메모: LIFT는 오히려 "컨텍스트 대신 가중치" 쪽 방법이라 넓은 의미의 인용입니다.

### 주장 B — "사람과 달리 LLM은 길고 자세한 컨텍스트에서 더 잘하고, 관련성을 **스스로 증류**한다"

**Jiang et al., 2025** (재등장)
- 의도: 저장소 전체를 넣어도 모델이 알아서 필요한 부분을 찾는다는 근거입니다.

**SelfElicit** (Liu et al., ACL 2025b)
- 내용: 모델의 깊은 층 attention 신호로 컨텍스트 속 핵심 증거 문장을 찾아 명시적으로 강조합니다. 학습 없이 여러 evidence 기반 QA 과제에서 성능이 올랐습니다.
- 의도: 모델이 어디가 중요한지 스스로 안다는 근거입니다.
- 메모: **반쪽짜리 근거입니다.** SelfElicit의 문제의식은 "LM은 노이즈가 섞인 컨텍스트에서 핵심 증거를 **충분히 활용하지 못한다**"입니다. 신호는 내부에 있지만 명시적으로 강조해 줘야 성능이 난다는 결과라서, "알아서 증류한다"는 주장을 오히려 제한합니다. 긴 컨텍스트 중간의 정보를 놓치는 현상(예: *Lost in the Middle*, Liu et al., TACL 2024) 같은 반대 증거는 인용되지 않았습니다.

**Dynamic Cheatsheet** (재등장)
- 의도: 누적된 cheatsheet이 성능을 올린다는 근거입니다.

**"사람은 간결한 일반화에서 이득을 본다"**는 부분에는 인용이 없습니다. 저자의 단언입니다.

→ ¶3의 결론: 도메인 휴리스틱을 압축하지 말고 보존해서, 무엇이 중요한지는 **추론 시점에 모델이 고르게 하자.** 이것이 ACE의 설계 철학입니다.

- 메모 (우리 실험과의 연결): 이 전제는 "강한 장문 모델"을 가정합니다. Qwen3-8B, 32k 설정에서는 다음 현상이 관찰됐습니다.
  - AppWorld에서 context exhausted 호출이 많습니다.
  - Dreaddit playbook은 200개 bullet 중 198개가 한 섹션에 몰렸고, 같은 공식이 9번 반복됐습니다.

  "8B 모델도 스스로 관련성을 고르는가"라는 질문 자체가 발표 토론거리가 됩니다.

---

## ¶4. ACE 소개 (인용 없음)

용어만 정리합니다.

| 용어 | 뜻 |
| --- | --- |
| Offline 적응 | 학습 데이터로 system prompt(playbook)를 만든 뒤 고정하고 테스트 |
| Online 적응 | 테스트 문항을 풀면서 매 문항 뒤에 memory(playbook)를 갱신 (test-time memory) |
| Generation → reflection → curation | Generator가 풀고, Reflector가 성공·실패에서 교훈을 뽑고, Curator가 playbook에 반영 |
| Structured, incremental (delta) update | 전체를 다시 쓰지 않고 bullet 단위로 추가·수정 → context collapse 방지 |
| Grow-and-refine | 계속 추가하되 주기적으로 중복 제거·병합 (우리 v5는 refine을 끈 ADD-only 설정) |

---

## ¶5. 평가 설계와 핵심 발견

**평가 대상**
- Agents: AppWorld (Trivedi et al., 2024). 여러 턴의 추론, 도구 사용, 환경 상호작용이 필요하고, 누적된 전략을 에피소드 사이에 재사용할 수 있습니다.
- 도메인 벤치마크: FiNER (Loukas et al., 2022), Formula (Wang et al., 2025a)

### 핵심 발견 bullet 4개와 본문 대조

**1. "Strong baseline 대비 agent 평균 +10.6%, 도메인 평균 +8.6%"**
- offline과 online 설정을 모두 합친 **평균**입니다. 조건별 편차는 본문 Table 1–2에서 확인하세요.

**2. "라벨 없이 execution feedback만으로 효과적인 컨텍스트를 만든다"**
- AppWorld에서는 코드 실행 결과와 환경 신호만으로도 됩니다.
- 금융 과제는 사정이 다릅니다. §4.4와 §5의 한계 서술에서 **GT가 없고 피드백이 약하면 성능이 떨어질 수 있다**고 인정합니다.
- 우리 Dreaddit의 GT✗ ACE +7점은 이 주장과 일관됩니다.

**3. "AppWorld 리더보드 1위였던 IBM-CUGA (GPT-4.1)를 open-source DeepSeek-V3.1로 **넘어섰다**"**

**IBM CUGA** (Marreed et al., arXiv 2025)
- 내용: 계층적 planner-executor 구조의 엔터프라이즈용 범용 에이전트입니다. 당시 AppWorld 리더보드 1위였습니다.
- 인트로와 본문의 표현 차이 (**주의**):
  - 인트로 bullet: CUGA를 "surpasses"한다고 씁니다.
  - 본문 §4.3: 평균은 **59.4 대 60.3으로 "matches"**라고 씁니다. online 적응의 test-challenge에서만 TGC +8.4, SGC +0.7로 앞섭니다.
  - 초록: "전체 평균은 필적, test-challenge에서는 능가"로 정확하게 씁니다.
  - 각주: CUGA는 **방법론적 baseline이 아니라 대략적인 참고 수치**이며 직접 비교하지 않는다고 명시합니다.

  인트로 bullet이 가장 강하게 쓰여 있는 셈입니다.
- "더 작은 open-source 모델"이라는 표현도 따져 볼 만합니다. DeepSeek-V3.1은 671B 파라미터 MoE(활성 37B)이고, GPT-4.1은 크기가 공개되지 않았습니다.

**4. "훨씬 적은 rollout과 낮은 적응 지연"**

본문 §4.7의 수치입니다.

| 비교 | 지연시간 | 기타 |
| --- | ---: | --- |
| AppWorld offline, GEPA 대비 | −82.3% | rollout −75.1% |
| FiNER online, DC 대비 | −91.5% | 토큰 비용 −83.6% |
| 평균 | −86.9% | — |

- 메모: 절감의 이유는 delta 업데이트와 **LLM을 쓰지 않는** 병합·중복 제거입니다. 비교 대상 선택(offline은 GEPA, online은 DC)에 유의하세요.

---

## 발표용 체크리스트 — 인용 구조에서 읽히는 것

1. **baseline 구도와 인용 구도가 일치합니다.** MIPRO와 GEPA는 prompt 대표로 brevity bias의 표적이 되고, DC는 memory 대표로 context collapse의 표적이 됩니다. 두 한계가 각각 비교 대상 하나씩을 겨냥하도록 짜여 있습니다.
2. **핵심 주장의 외부 근거가 얇습니다.**
   - Brevity bias: 외부 근거는 Gao et al. 한 편(테스트 생성 단일 도메인)입니다.
   - Context collapse: 자체 관찰 1건(Figure 2)입니다.
   - "LLM이 알아서 관련성을 고른다": 근거로 쓴 SelfElicit이 오히려 한계를 보여 줍니다.
3. **느슨한 배경 인용이 있습니다.** CoT와 Self-Consistency를 해석 가능성의 근거로, Flora와 LIFT를 컨텍스트 포화의 근거로, Caravan을 interactive agent의 예로 쓴 것은 느슨합니다.
4. **자기 인용 클러스터가 있습니다.** Olukotun 랩(Caravan, ML library agent, AccelOpt), 1저자와 공저자의 시스템 연구(CacheBlend, FrontierCS), James Zou(DC)가 해당합니다. 그중 AccelOpt와 FrontierCS는 첫 arXiv 이후 추가됐습니다.
5. **표현 강도가 다릅니다.** CUGA 비교는 인트로가 초록과 본문보다 강하게 씁니다.
6. **우리 결과와 연결됩니다.**
   - Dreaddit GEPA +9.7은 "brevity가 validation 지표와 맞는 설정"의 사례일 수 있습니다.
   - Qwen3-8B의 context 한계와 playbook 반복은 ¶3 전제("긴 컨텍스트에서 스스로 고른다")에 대한 반례 후보입니다.
   - DC(CU)가 Base보다 5–6점 낮은 것은 context collapse 가설과 일관되지만, 붕괴가 실제로 일어났는지는 memory 기록으로 확인해야 합니다.

---

## 확인에 사용한 출처

논문 원문 외에, 기억이 불확실했던 인용은 아래에서 확인했습니다.

- Flora: [arXiv 2507.19786](https://arxiv.org/abs/2507.19786), [GitHub](https://github.com/txchen-USTC/Flora)
- FrontierCS: [arXiv 2512.15699](https://arxiv.org/abs/2512.15699)
- AccelOpt: [arXiv 2511.15915](https://arxiv.org/abs/2511.15915)
- Caravan: [USENIX OSDI '24](https://www.usenix.org/conference/osdi24/presentation/zhang-qizheng)
- Long-context NL2SQL: [arXiv 2501.12372](https://arxiv.org/abs/2501.12372)
- FinLoRA: [arXiv 2505.19819](https://arxiv.org/abs/2505.19819)
- The Prompt Alchemist: [arXiv 2501.01329](https://arxiv.org/abs/2501.01329)
- IBM CUGA: [IBM Research blog](https://research.ibm.com/blog/cuga-agent-framework), [arXiv 2503.01861](https://arxiv.org/abs/2503.01861)
- ML library agent: [arXiv 2502.02534](https://arxiv.org/abs/2502.02534)
- LCLM agents: [arXiv 2505.08120](https://arxiv.org/abs/2505.08120)
- SelfElicit: [ACL Anthology](https://aclanthology.org/2025.acl-long.448/)
- SymGen: [ACL Anthology](https://aclanthology.org/2023.emnlp-main.523/)
