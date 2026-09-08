# WarrantRoute Graphical Abstract: Single-Model Comparison

Date: 2026-09-05
Generation method: built-in image_gen tool, one generation and two targeted edits.
Final image: warrantroute_graphical_abstract_single_model_v1.png
Status: explanatory diagram of the current implementation, not a results figure.
No manuscript source or existing figure was replaced.

The lower row is an expanded view of one conditional revision cycle. The two
Controller boxes represent the same controller before and after revision and
rechecking, not two additional agents. The diagram shows one fixed LLM for all
agent calls within a condition. Routing and controller logic run in code.

Suggested caption: WarrantRoute reviews qualitative claims against source
evidence, selects specialist coverage through cost-aware routing, and coordinates
a bounded revision-and-recheck cycle. Each compared condition uses one fixed
LLM throughout. Original-flaw detection, execution cost and independently
evaluated repair quality are distinct outcomes.

## Initial Generation Prompt

Use case: infographic-diagram.
Create a polished, scientifically accurate graphical abstract for the current WarrantRoute system. This is a new explanatory research diagram, entirely in English, not a performance-results chart. Wide landscape composition, roughly 16:10, high resolution, crisp readable typography on white. Restrained flat diagram style with charcoal text, teal process accents, muted coral for revision, and a small blue accent for comparison. Generous spacing, clear arrowheads, consistent thin lines. No gradients, no photorealistic decoration, no robots or brains, no fake data, no benchmarks, no 3D effects, no watermark. Use simple document and evidence-line icons only where they clarify the process.

Main title, exact spelling: "WarrantRoute".
Subtitle: "Evidence-grounded review with cost-aware routing".

TOP BAND: emphasize the user's current single-model experiment. Header: "ONE LLM PER COMPLETE RUN".
Show three separate equal conditions side by side:
"Qwen3 8B only" | "Llama 3.1 8B only" | "Gemma 3 4B only".
Under them write: "Same packets, prompts, routing policy and budgets".
This band describes three SEPARATE executions of the identical pipeline below, not a mixed-model ensemble. Never put different model names on different agent roles. Every active role and recheck in a given run uses its one fixed LLM.

MAIN PIPELINE: clear left-to-right flow with readable labels and a genuinely understandable revision feedback loop.
1. "Input packet" with "Source context + qualitative claim".
2. "Initial review" with two equal sublabels: "Proposer" and "Evidence Scout"; supporting phrase "Separate initial assessments".
3. "Four-mode router" with phrase "Review signals - cost penalties". Show four choices as a compact aligned list:
"Generalist: no extra specialist"
"Methods: Methods Challenger"
"Domain: Domain Challenger"
"Both: Methods + Domain"
Small note directly below: "Proposer and Evidence Scout are always active".
The router chooses ROLE COVERAGE, not which LLM model to use. Initial specialist requests may expand coverage. Do not describe the router as learned or as predicting calibrated improvement.
4. "Evidence-linked issues" with concise fields "Issue / Evidence ID / Requested change".
5. A prominent "Controller" decision, connected to the issue ledger and to the revision loop and outputs.

BOUNDED LOOP: beneath the main pipeline, show a clean feedback cycle:
Controller -> "Reviser" ("Minimal evidence-supported edits") -> "Recheck" ("Evidence Scout + issue owners") -> Controller.
Label the Controller-to-Reviser edge "Open issues + budget remains".
Label the loop "At most 2 revision rounds / 12 agent calls".
Reviser must not approve its own changes. Rechecking is a separate role call, NOT a different LLM in this experiment. There must be a direct controller exit that does not require revision when no issue remains.

OUTPUTS at the right, downstream of Controller:
"Accept"
"Human escalation"
"Quarantine invalid output"
Under the exits add "Claim + evidence-linked review trace".
Do not imply that human review actually occurred; escalation is a terminal status awaiting a human.

BOTTOM STRIP, compact but readable:
"Measure: original-flaw detection, calls, tokens and time".
"Repair quality requires independent evaluation".
Optional tiny design-status note if space permits: "Playbook learning is disabled".
The diagram must communicate: fixed LLM per run; adaptive reviewer roles; conditional evidence-grounded revision; bounded checking; separate scientific evaluation. Do not show improvement percentages, winners, learned weights, paragraph-by-paragraph switching, autonomous Playbook learning, or a changing LLM within the loop. Prioritize legibility and correct arrow logic over dense text.

## First Edit Prompt

Edit this WarrantRoute graphical abstract. Preserve the title, three single-model conditions, upper input/review/router/issue stages, right-side outputs, and the footer. Preserve its clean white, teal, coral and blue style and readable English typography.

Correct the lower revision loop and Controller connections. The existing lower arrows are dangling, and the dashed Controller arrow leading to the floating phrase "No issues or budget exhausted" is misleading.
Remove that entire dashed downward arrow and the floating "No issues or budget exhausted" phrase.
Redraw the lower area as ONE continuous, unmistakable cycle with connected arrow endpoints:
Controller -> Reviser -> Recheck -> Controller.
The Controller-to-Reviser arrow must visibly START at the Controller node and END on the Reviser node, labeled "Open issues + budget remains".
The Reviser-to-Recheck arrow must visibly join those two nodes.
The Recheck-to-Controller arrow must visibly START on Recheck and END on Controller, labeled "Updated checks".
No arrows may terminate on a dashed container border or in empty space. Feel free to move or rearrange the Reviser and Recheck nodes, their labels, and the dashed boundary to make this topology clear, with absolutely no overlapping lines/text. Use a spacious U-shaped or rectangular feedback loop. The right-side Controller exits to Accept, Human escalation and Quarantine invalid output stay.
Keep the loop budget label "At most 2 revision rounds / 12 agent calls".
Keep "Reviser does not approve its own changes."
Replace the other small lower note with the exact text "Same LLM, separate audit call." This makes clear that rechecking uses the same model as every other step in this condition.
Remove unnecessary numeric circles 6 and 7 if that helps prevent the layout from implying a mandatory linear step after acceptance.
Do not change any model name or imply mixed-model execution. Do not add data, scores or claims of successful repair.

## Final Edit Prompt

Edit only the lower revision section of this WarrantRoute diagram. Keep the entire upper half, model-comparison header, title and footer unchanged.

The lower arrows are still ambiguous. Solve this by replacing the whole lower coral section with an EXPANDED LINEAR VIEW of the conditional cycle, using a repeated Controller node at the end. This is a deliberate unrolled depiction of one cycle, not a literal curved feedback arrow.

DELETE all existing lower coral connector lines, all dangling arrowheads, and both existing lower boxes. In the same lower whitespace, draw a clean wide section with the heading:
"Conditional revision cycle"
Below the heading place exactly FOUR compact equally aligned boxes in one horizontal row, from left to right:
1. "Controller" with subtitle "Open issues + budget remains"
2. "Reviser" with subtitle "Minimal supported edits"
3. "Recheck" with subtitle "Evidence Scout + issue owners"
4. "Controller" with subtitle "Reassess and stop or repeat"

Connect ONLY neighboring boxes with three short straight right-pointing arrows:
Controller -> Reviser -> Recheck -> Controller.
Every arrow starts on the right edge of one box and ends on the left edge of the next box. NO other lower arrows, NO curved arrows, NO lines linking the expanded detail to the upper row. The repeated Controller is the SAME controller, showing the return to it after rechecking.

One centered line under the four boxes:
"At most 2 revision rounds / 12 agent calls".
A second smaller line:
"Same LLM throughout. The Reviser cannot approve its own changes."

Fit this entire lower section neatly between the existing upper pipeline and the existing bottom measurement strip. Use coral outlines for the Reviser/Recheck boxes and teal outlines for Controller boxes. Plenty of padding and readable text. Remove the existing two crossed-circle note boxes; their meaning is now in the centered sentence. Do not add any new content outside this revision section.

