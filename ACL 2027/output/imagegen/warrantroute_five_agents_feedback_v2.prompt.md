# WarrantRoute: Model Versions, Five Agent Roles and Feedback

Date: 2026-09-05
Method: built-in image_gen tool, editing the previous graphical abstract.
Final image: warrantroute_five_agents_feedback_v2.png
Reference: warrantroute_graphical_abstract_single_model_v1.png

## Description

Three experimental conditions use Qwen3 8B, Llama 3.1 8B or Gemma 3 4B
throughout every agent call within a condition. Five prompted roles are
available: Proposer (P), Evidence Scout (E), Methods Challenger (M), Domain
Challenger (D) and Reviser (R). They are not five different language models.
P and E always perform initial reviews. M and D are activated conditionally.
R is called only when revision is needed and the remaining budget permits it.

Reviewers identify issues linked to source evidence. R proposes a correction,
then E and active specialist issue owners check the revised claim. Issues
originally raised by P are assigned to E for rechecking. Recheck is another
call to an existing role, not an additional agent. R cannot approve its own
changes. Router and Controller are software logic rather than LLM agents.
The repeated Controller boxes show one cycle returning to the same controller.

The initial mode determines two, three or four review calls. The complete
trajectory permits at most two revision rounds and twelve total agent calls.
Acceptance is an internal operational decision, not proof of improved quality.
No result, dataset example or manuscript content was generated or replaced.

## Generation Prompt

Redesign the attached WarrantRoute explanatory diagram to make THREE things immediately obvious: (1) there are THREE separate single-model versions, (2) there are exactly FIVE agent ROLES, and (3) feedback means an issue is revised by R and then checked by existing auditor roles, not by a new sixth agent. Use the attached image only as the visual-style starting point. You may fully rearrange it. All text must be English. Clean high-resolution research infographic, white background, charcoal typography, teal plus blue and coral accents. More explanatory and less visually crowded than the reference. Large legible labels, no overlapping arrows/text, no decorative robot/brain graphics, no fabricated results. Landscape or slightly tall landscape layout with enough room for three clear horizontal sections.

TITLE: "WarrantRoute"
SUBTITLE: "Three model versions. Five agent roles. One bounded feedback process."

SECTION A, compact upper band, heading "ONE FIXED LLM THROUGHOUT EACH VERSION".
Three equal columns:
"WarrantRoute / Qwen" and "Qwen3 8B in every role"
"WarrantRoute / Llama" and "Llama 3.1 8B in every role"
"WarrantRoute / Gemma" and "Gemma 3 4B in every role"
Under all three, one sentence:
"Separate experiments. Same packets, role prompts, routing rules and budgets."
Do NOT draw arrows from one model version into another. Do NOT assign different model families to different roles. These are three executions of the same architecture.

SECTION B, middle band, prominently headed "5 AGENT ROLES, NOT 5 DIFFERENT MODELS".
Show exactly FIVE equal role tiles, each with a large LETTER badge, not a process-step number:
P | "Proposer" | "Generalist assessment"
E | "Evidence Scout" | "Support and counterevidence"
M | "Methods Challenger" | "Methodological checks"
D | "Domain Challenger" | "Domain and scope checks"
R | "Reviser" | "Minimal supported corrections"
Use teal for P/E, blue for M/D, coral for R.
Directly below the role tiles show this clear activation legend:
"P + E: always start" / "M and D: selected when needed" / "R: called only for revision".
Then a compact exact initial-routing strip:
"Generalist: P + E (2 calls)"
"Methods: P + E + M (3 calls)"
"Domain: P + E + D (3 calls)"
"Both: P + E + M + D (4 calls)"
Label this strip "Initial review modes".
The count is initial calls, not a fixed total per full run. Subsequent rechecks reuse roles.

SECTION C, lower band, heading "HOW FEEDBACK WORKS".
First, a compact setup sentence:
"Reviewers record: issue, evidence ID and requested correction."
Then show ONE horizontal expanded cycle with exactly FOUR clearly connected boxes:
"Controller (code)" / "Open issues + budget?"
  -> "R: Revise" / "Address the recorded issues"
  -> "E + issue owners: Recheck" / "Resolve the issue or report remaining concerns"
  -> "Controller (same code)" / "Accept, repeat or escalate".
The arrows are only three short left-to-right links between these four neighboring boxes. This is an UNROLLED view of a cycle, so the repeated Controller depicts the return to the same controller. Do not invent complicated curved or dangling feedback arrows. Under the last box, or in a clear decision legend, explain:
"No open issues: accept"
"Unresolved + budget remains: another revision"
"Unresolved + budget exhausted: human escalation"
Optional separate small note "Invalid output is quarantined", if room allows.
Under the cycle, emphasize these three facts:
"Recheck reuses E and relevant M/D. It is not a sixth agent."
"R cannot approve its own corrections."
"Maximum: 2 revision rounds and 12 total agent calls."

FOOTER:
"Router and Controller are code, not LLM agents."
"Internal acceptance is not an independent quality score."

Scientific fidelity:
- P reviews the supplied qualitative claim; do not suggest P creates a new source dataset.
- P and E initial calls are isolated, although executed serially.
- Recheck is always E plus whichever active M/D roles own open issues. P-origin issues are assigned to E for rechecking.
- All five possible agent roles within one version, including rechecks, use one identical model, but have different role prompts.
- Source text plus claim is the input. Intended flaw labels are not model inputs.
- Do not draw self-approval by R. Do not count Router, Controller, the issue ledger or Recheck as additional agents.
- Do not show winner rankings, numerical performance, automatic Playbook learning or dynamic switching between LLM families.
Prioritize a teaching diagram that makes the five roles and the repeated audit feedback understandable at a glance.

