# Agent Looping

핵심 질문은 **“에이전트가 과거 경험을 활용해, 다음 작업을 더 잘 수행하도록 만들 수 있는가?”**이다. 두 논문 모두 모델 가중치를 업데이트하기보다, 경험에서 얻은 지식을 외부 기억에 축적하고 다음 실행의 context로 활용한다.

The central question is: **“Can we enable agents to use past experience to perform better on future tasks?”** Both papers accumulate knowledge from experience in external memory and use it as context for subsequent tasks, rather than updating model weights.

## ReasoningBank

논문: [ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory](https://arxiv.org/html/2509.25140v2)

Paper: [ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory](https://arxiv.org/html/2509.25140v2)

핵심 질문: **경험에서 무엇을 추출해 재사용할 것인가?**

Key question: **What should we extract from experience and reuse?**

### 문제점

**Problems**

1. **과거에 했던 비슷한 실수를 반복한다.**

   이전에 페이지를 끝까지 확인하지 않아 실패했는데, 다음 작업에서도 같은 실수를 반복한다.

   **They repeat similar mistakes made in the past.** For example, an agent previously failed because it did not check all pages, yet makes the same mistake on the next task.

2. **관련 문제에서 얻은 유용한 통찰을 버린다.**

   영수증 검색에서 배운 “전체 결과인지 확인해야 한다”는 요령을 배송 알림 검색에도 활용할 수 있지만, 그 통찰을 전달하지 못한다.

   **They discard valuable insights gained from related tasks.** The lesson “verify that all results have been retrieved,” learned while searching for receipts, could also help when searching for delivery notifications, but the agent fails to transfer that insight.

3. **시간이 지날수록 더 유능해지는 자기 개선 구조가 없다.**

   작업을 많이 수행하더라도 경험이 축적되지 않아, 이후 작업의 성능 개선으로 이어지지 않는다.

   **Most importantly, they lack the ability to improve themselves over time.** Even after completing many tasks, agents lack a mechanism for accumulating experience and using it to perform better on subsequent tasks.

### 해결 방식

**Proposed Solution**

**성공과 실패 경험에서 재사용 가능한 교훈을 추출하고, 기억에 추가해 다음 문제에서 참고하게 한다.** 단순한 실행 기록을 넘어, “다음에 비슷한 상황을 만나면 어떻게 판단하고 행동해야 하는가”를 저장한다.

**The agent extracts reusable lessons from both successful and failed experiences, adds them to memory, and consults them when solving subsequent tasks.** Beyond recording what happened, it stores guidance on how to reason and act when a similar situation arises.

```text
새 문제 → 관련 기억 검색 → 기억을 참고해 실행
       → 성공·실패 자체 판단 → 교훈 추출 → 기억에 추가
```

```text
New task → Retrieve relevant memories → Execute with memory guidance
         → Self-judge success or failure → Extract lessons → Add to memory
```

교훈은 **memory item**으로 구조화하여 **외부 JSON 데이터에 저장**한다. 기본 구현은 기존 행동 지침 전체를 다시 쓰는 것이 아니라, 새로운 기억 항목을 추가하는 방식이다.

Lessons are structured as **memory items** and **stored externally in JSON format**. The basic implementation appends new memory items rather than rewriting the entire set of existing behavioral guidelines.

### 구현 요약

**Implementation Summary**

1. **무엇을 저장하나?**

   교훈은 `title`, `description`, `content`로 구조화한다. 원본 실행 기록도 보관하지만, 재사용의 핵심은 추출한 전략이다.

   **What is stored?**

   Lessons are structured into `title`, `description`, and `content`. Raw execution trajectories are also retained, but the primary reusable knowledge consists of the extracted strategies.

2. **어떻게 판단하나?**

   정답 라벨 없이, LLM이 문제와 실행 기록을 바탕으로 성공 또는 실패를 판단한다.

   **How are outcomes evaluated?**

   An LLM judges success or failure based on the task and execution trajectory, without ground-truth labels.

3. **어떻게 가져오나?**

   문제 임베딩을 사용해 유사한 과거 경험을 검색하고, 해당 경험의 기억 항목을 에이전트의 시스템 프롬프트에 넣는다.

   **How are memories retrieved?**

   Task embeddings are used to retrieve similar past experiences, and their associated memory items are inserted into the agent’s system prompt.

4. **어떻게 갱신하나?**

   기본 구현은 새 기억 항목을 추가한다. 병합이나 가지치기 같은 고도화된 기억 정리 방식은 논문의 핵심 기여가 아니다.

   **How is memory updated?**

   The basic implementation simply appends new memory items. Advanced consolidation mechanisms, such as merging or pruning, are not the paper’s core contribution.

**예시:** “첫 페이지의 영수증만 합산해 누락이 발생했다”는 경험에서 **“전체 목록이 필요한 작업에서는 마지막 페이지까지 확인한 뒤 계산하라”**는 교훈을 추출한다. 이후 배송 알림 검색처럼 관련된 작업에서 이 지침을 검색해 활용한다.

**Example:** From the experience “some receipts were omitted because only the first page was included in the total,” the agent extracts the lesson: **“When a task requires the complete list, check every page before performing calculations.”** It later retrieves and applies this guidance to related tasks, such as searching for delivery notifications.

**추가 기여인 MaTTS**는 여러 실행 경로를 비교하거나 하나의 실행 경로를 재검토하여 더 좋은 교훈을 추출한다. 추가적인 추론 자원을 현재 문제 해결뿐 아니라 **미래 문제에 재사용할 기억의 품질 개선**에도 활용한다.

**An additional contribution, MaTTS**, extracts better lessons by comparing multiple trajectories or re-examining a single trajectory. It uses additional inference-time compute not only to solve the current task, but also to **improve the quality of memories that can be reused on future tasks**.

## ACE

논문: [Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models](https://arxiv.org/html/2510.04618v3)

Paper: [Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models](https://arxiv.org/html/2510.04618v3)

핵심 질문: **축적한 지식을 어떻게 보존하고 갱신할 것인가?**

Key question: **How should we preserve and update accumulated knowledge?**

### 문제점

**Problems**

| 문제 | 의미 | 직관적인 예시 |
|---|---|---|
| **Brevity bias** | 짧고 일반적인 지침을 선호하면서 필요한 세부 정보를 잃는 경향 | “다음 페이지가 없을 때까지 조회”가 “꼼꼼하게 확인”으로 바뀜 |
| **Context collapse** | 누적 context 전체를 반복해서 다시 쓰다가 기존 지식이 크게 소실되는 현상 | 기존 규칙 A·B·C를 갱신했더니 C만 남음 |

| Problem | Meaning | Intuitive Example |
|---|---|---|
| **Brevity bias** | A tendency to favor short, generic instructions at the expense of necessary details | “Continue retrieving results until there are no more pages” becomes “Check carefully.” |
| **Context collapse** | Substantial loss of existing knowledge caused by repeatedly rewriting the entire accumulated context | After updating a context containing rules A, B, and C, only C remains. |

핵심은 **짧은 context 자체가 아니라 유용한 세부 정보의 손실**이다. 특히 context collapse는 무의미한 정보가 들어오는 현상보다는, **이미 축적한 유용한 정보가 사라지는 현상**을 뜻한다.

The issue is **not a short context in itself, but the loss of useful details**. In particular, context collapse refers to **the disappearance of useful information that has already been accumulated**, rather than the introduction of irrelevant information.

### 해결 방식

**Proposed Solution**

Context를 구체적인 전략·주의사항을 담은 **playbook**으로 관리하고, 전체 재작성 대신 항목별 변경분을 반영한다.

ACE maintains context as a **playbook** of concrete strategies and precautions, applying localized updates to individual items rather than rewriting the entire context.

1. **Generator:** 현재 playbook을 참고해 문제를 실행한다.

   **Generator:** Executes the task using the current playbook.

2. **Reflector:** 실행 결과에서 성공 요인, 실패 원인, 구체적인 교훈을 추출한다.

   **Reflector:** Analyzes execution outcomes to identify what worked, what went wrong, and what concrete lessons can be learned.

3. **Curator:** 교훈을 반영할 변경분인 **delta**를 생성한다. 별도 코드가 이 변경분을 기존 playbook에 병합한다.

   **Curator:** Generates a **delta**, a set of changes that incorporates the extracted lessons. Separate code merges these changes into the existing playbook.

**예시:** 기존에 “시간대 통일”과 “영수증 ID로 중복 제거”가 있다면, 새로 배운 “마지막 페이지까지 조회”만 추가한다. 기존 지식을 보존하면서 구체적인 지침을 축적하고, *grow-and-refine*을 통해 중복을 정리한다.

**Example:** If the playbook already contains “standardize time zones” and “deduplicate receipts by receipt ID,” the system adds only the newly learned guideline, “retrieve results through the last page.” It preserves existing knowledge while accumulating concrete guidance and controls redundancy through *grow-and-refine*.

## 비교 정리

**Comparison**

| 관점 | ReasoningBank | ACE |
|---|---|---|
| 핵심 질문 | **경험에서 무엇을 추출해 재사용할까?** | **지식을 어떻게 보존·갱신할까?** |
| 주로 다루는 문제 | 반복되는 실수, 통찰의 미활용, 경험 축적 부재 | Brevity bias, context collapse |
| 주요 접근 | 성공·실패에서 추론 전략 추출 후 검색·재사용 | 구체적인 playbook을 delta 기반으로 갱신 |
| 공통점 | 모델 가중치 변경 없이 경험 기반 기억을 활용 | 모델 가중치 변경 없이 경험 기반 context를 개선 |

| Aspect | ReasoningBank | ACE |
|---|---|---|
| Key question | **What should we extract from experience and reuse?** | **How should we preserve and update knowledge?** |
| Main problems addressed | Repeated mistakes, unused insights, and a lack of experience accumulation | Brevity bias and context collapse |
| Main approach | Extract reasoning strategies from successes and failures, then retrieve and reuse them | Update a detailed playbook through deltas |
| Shared principle | Use experience-based memory without changing model weights | Improve experience-based context without changing model weights |

## 미팅용 결론

**Meeting Takeaway**

“ReasoningBank는 경험에서 재사용할 교훈의 내용에, ACE는 축적한 지식을 잃지 않고 관리하는 방법에 상대적으로 초점을 둡니다. 두 논문 모두 에이전트의 실행 경험이 다음 작업의 행동 개선으로 이어지는 순환 구조를 만든다는 공통점이 있습니다.”

“ReasoningBank places greater emphasis on the content of the lessons we extract and reuse, while ACE focuses more on managing accumulated knowledge without losing it. Both papers build a feedback loop that turns an agent’s execution experience into better behavior on subsequent tasks.”
