"use strict";

const METRICS = [
  ["evidential_credibility", "Evidential credibility"],
  ["voice_boundary_preservation", "Voice-and-boundary preservation"],
  ["scope_calibration", "Scope calibration"],
];

const ERROR_FLAGS = [
  "fabricated_or_altered_quote",
  "wrong_attribution",
  "unsupported_inference",
  "hidden_source_concentration",
  "lost_negative_case",
  "contextual_flattening",
  "unsupported_abstraction",
  "sensitive_or_diagnostic_inference",
  "inconsistent_codebook",
  "other",
];

const STATUS_BY_DISPOSITION = {
  accept: "no_change",
  revise: "actionable_revision",
  reject: "reject_or_regenerate",
  escalate: "human_escalation",
};

const ALLOWED_LOCATION = [
  /^\/proposed_interpretation\/(?:theme_name|claim|explanation)$/,
  /^\/proposed_interpretation\/boundary_conditions\/\d+$/,
  /^\/evidence\/\d+\/(?:candidate_role|candidate_attributed_excerpt_id|candidate_attributed_source_id|candidate_attributed_speaker_id|candidate_quote|candidate_warrant)$/,
];

const state = {
  launchNonce: null,
  sessionToken: null,
  item: null,
  assignment: null,
  lockedRating: null,
  timingReceiptSha256: null,
  timer: null,
  ratingPayloadAfterSubmit: null,
};

const byId = (id) => document.getElementById(id);

function setError(target, message) {
  byId(target).textContent = message || "";
}

function uniqueNonemptyLines(value, maximum) {
  const values = value
    .split(/\r?\n|,/)
    .map((part) => part.trim())
    .filter(Boolean);
  return [...new Set(values)].slice(0, maximum);
}

function formatSeconds(ms) {
  const whole = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

async function api(path, payload = null) {
  const options = {
    method: payload === null ? "GET" : "POST",
    cache: "no-store",
    credentials: "same-origin",
    headers: { "Accept": "application/json" },
  };
  if (payload !== null) {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-WarrantRoute-Launch"] = state.launchNonce || "";
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({ error: "Unreadable local response." }));
  if (!response.ok) {
    throw new Error(body.error || `Local instrument error (${response.status}).`);
  }
  return body;
}

class DirectionJTimer {
  constructor() {
    this.graceMs = 120000;
    this.origin = null;
    this.startedAtUtc = null;
    this.segmentStart = null;
    this.currentState = null;
    this.remainingGrace = this.graceMs;
    this.idleDeadline = null;
    this.idleTimeout = null;
    this.uiInterval = null;
    this.closed = false;
    this.segments = [];
    this.rawTotals = { active: 0, hidden: 0, idle_paused: 0 };
    this.counts = { keyboard: 0, pointer: 0, scroll: 0, resume_from_idle: 0 };
    this.boundVisibility = () => this.onVisibility();
    this.boundKeyboard = () => this.onActivity("keyboard");
    this.boundPointer = () => this.onActivity("pointer");
    this.boundScroll = () => this.onActivity("scroll");
  }

  start() {
    if (document.hidden) throw new Error("The page must be visible before timing starts.");
    const now = performance.now();
    this.origin = now;
    this.segmentStart = now;
    this.currentState = "active";
    this.startedAtUtc = new Date().toISOString();
    this.idleDeadline = now + this.graceMs;
    document.addEventListener("visibilitychange", this.boundVisibility, true);
    document.addEventListener("keydown", this.boundKeyboard, true);
    document.addEventListener("pointerdown", this.boundPointer, true);
    document.addEventListener("pointermove", this.boundPointer, true);
    document.addEventListener("wheel", this.boundScroll, { capture: true, passive: true });
    document.addEventListener("scroll", this.boundScroll, { capture: true, passive: true });
    this.scheduleIdle();
    this.uiInterval = window.setInterval(() => this.renderStatus(), 250);
    byId("timer-card").hidden = false;
    this.renderStatus();
  }

  offset(now) { return now - this.origin; }

  closeSegment(at, reason) {
    const rawDuration = Math.max(0, at - this.segmentStart);
    this.rawTotals[this.currentState] += rawDuration;
    this.segments.push({
      index: this.segments.length + 1,
      state: this.currentState,
      start_offset_ms: Math.round(this.offset(this.segmentStart)),
      end_offset_ms: Math.round(this.offset(at)),
      duration_ms: Math.round(rawDuration),
      end_reason: reason,
    });
  }

  transition(nextState, reason, at = performance.now()) {
    if (this.closed || nextState === this.currentState) return;
    this.closeSegment(at, reason);
    this.currentState = nextState;
    this.segmentStart = at;
  }

  clearIdle() {
    if (this.idleTimeout !== null) window.clearTimeout(this.idleTimeout);
    this.idleTimeout = null;
  }

  scheduleIdle() {
    this.clearIdle();
    if (this.closed || this.currentState !== "active" || document.hidden) return;
    const delay = Math.max(0, this.idleDeadline - performance.now());
    this.idleTimeout = window.setTimeout(() => {
      if (this.closed || this.currentState !== "active" || document.hidden) return;
      const boundary = this.idleDeadline;
      this.remainingGrace = 0;
      this.transition("idle_paused", "idle_grace_elapsed", boundary);
      this.renderStatus();
    }, delay);
  }

  onVisibility() {
    if (this.closed) return;
    const now = performance.now();
    if (document.hidden) {
      if (this.currentState === "active") {
        this.remainingGrace = Math.max(0, this.idleDeadline - now);
      }
      this.clearIdle();
      this.transition("hidden", "page_hidden", now);
    } else if (this.currentState === "hidden") {
      // Direction J v1 resumes a hidden/idle pause only on the next visible
      // keyboard, pointer, or scroll event. Merely revealing the page does not
      // restart counted review time.
      this.remainingGrace = 0;
      this.transition("idle_paused", "page_visible", now);
    }
    this.renderStatus();
  }

  onActivity(kind) {
    if (this.closed || document.hidden) return;
    this.counts[kind] += 1;
    const now = performance.now();
    if (this.currentState === "idle_paused") {
      this.counts.resume_from_idle += 1;
      this.transition("active", "activity_resumed", now);
    }
    if (this.currentState === "active") {
      this.remainingGrace = this.graceMs;
      this.idleDeadline = now + this.graceMs;
      this.scheduleIdle();
    }
    this.renderStatus();
  }

  liveTotal(name, now) {
    return this.rawTotals[name] + (this.currentState === name ? Math.max(0, now - this.segmentStart) : 0);
  }

  renderStatus() {
    if (this.closed || this.origin === null) return;
    const now = performance.now();
    const active = this.liveTotal("active", now);
    const card = byId("timer-card");
    card.classList.toggle("paused", this.currentState !== "active");
    byId("timer-active").textContent = `${formatSeconds(active)} active`;
    if (this.currentState === "active") {
      const remaining = Math.max(0, Math.ceil((this.idleDeadline - now) / 1000));
      byId("timer-state").textContent = "Active";
      byId("timer-idle").textContent = `Idle grace: ${remaining}s · keyboard, pointer, or scroll resets it`;
    } else if (this.currentState === "hidden") {
      byId("timer-state").textContent = "Paused · page hidden";
      byId("timer-idle").textContent = "Hidden time is excluded.";
    } else {
      byId("timer-state").textContent = "Paused · visible idle";
      byId("timer-idle").textContent = "Move the pointer, type, or scroll to resume.";
    }
  }

  stop() {
    if (this.closed) throw new Error("The rating timer has already stopped.");
    const now = performance.now();
    if (this.currentState === "active" && now > this.idleDeadline) {
      this.remainingGrace = 0;
      this.transition("idle_paused", "idle_grace_elapsed", this.idleDeadline);
    }
    this.closeSegment(now, "rating_submitted");
    this.closed = true;
    this.clearIdle();
    window.clearInterval(this.uiInterval);
    document.removeEventListener("visibilitychange", this.boundVisibility, true);
    document.removeEventListener("keydown", this.boundKeyboard, true);
    document.removeEventListener("pointerdown", this.boundPointer, true);
    document.removeEventListener("pointermove", this.boundPointer, true);
    document.removeEventListener("wheel", this.boundScroll, true);
    document.removeEventListener("scroll", this.boundScroll, true);

    const wallMs = Math.round(now - this.origin);
    const hiddenMs = Math.round(this.rawTotals.hidden);
    const idlePausedMs = Math.round(this.rawTotals.idle_paused);
    const activeMs = Math.round(this.rawTotals.active);
    const submittedAtUtc = new Date().toISOString();
    byId("timer-state").textContent = "Rating submitted · timer stopped";
    byId("timer-active").textContent = `${formatSeconds(activeMs)} active`;
    byId("timer-idle").textContent = "Feedback time is outside the canonical rating timer.";
    byId("timer-card").classList.remove("paused");
    return {
      started_at_utc: this.startedAtUtc,
      rating_submitted_at_utc: submittedAtUtc,
      timing_log: {
        rule_version: "direction-j-human-review-timing-v1",
        clock: "browser_performance_monotonic",
        start_event: "second_animation_frame_after_complete_guide_and_item_dom_render",
        stop_event: "rating_form_submit_received_by_browser_instrument_before_feedback",
        hidden_intervals_counted: false,
        visible_idle_grace_ms: 120000,
        visible_idle_after_grace_counted: false,
        resume_event: "next_visible_keyboard_pointer_or_scroll_event",
        wall_ms: wallMs,
        hidden_ms: hiddenMs,
        idle_paused_ms: idlePausedMs,
        active_ms: activeMs,
        duration_sum_error_ms: wallMs - hiddenMs - idlePausedMs - activeMs,
        activity_event_counts: this.counts,
        segments: this.segments,
      },
    };
  }
}

function buildStaticForms() {
  const metrics = byId("metric-fields");
  for (const [id, label] of METRICS) {
    const wrapper = document.createElement("label");
    wrapper.textContent = label;
    const select = document.createElement("select");
    select.id = id;
    select.required = true;
    const options = [
      ["", "Choose"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["cj", "Cannot judge"],
    ];
    for (const [value, text] of options) select.add(new Option(text, value));
    wrapper.append(select);
    metrics.append(wrapper);
  }
  const flags = byId("error-flags");
  for (const flag of ERROR_FLAGS) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = flag;
    label.append(input, document.createTextNode(flag));
    flags.append(label);
  }
}

function selectedFlags() {
  return [...byId("error-flags").querySelectorAll("input:checked")].map((node) => node.value);
}

function buildRating() {
  const rating = { rating_schema_version: "direction-j-shared-rating-v1" };
  const cannot = [];
  for (const [id] of METRICS) {
    const raw = byId(id).value;
    if (!raw) throw new Error(`Choose a value for ${id}.`);
    rating[id] = raw === "cj" ? null : Number(raw);
    if (raw === "cj") cannot.push(id);
  }
  rating.cannot_judge = cannot;
  rating.confidence = Number(byId("confidence").value);
  rating.disposition = byId("disposition").value;
  rating.requested_expertise = byId("expertise").value;
  rating.serious_error_flags = selectedFlags();
  rating.rationale = byId("rationale").value.trim();
  if (!Number.isInteger(rating.confidence) || rating.confidence < 1 || rating.confidence > 5) {
    throw new Error("Choose confidence from 1 to 5.");
  }
  if (!STATUS_BY_DISPOSITION[rating.disposition]) throw new Error("Choose a disposition.");
  if (!["none", "qualitative_methods", "domain", "both"].includes(rating.requested_expertise)) {
    throw new Error("Choose requested expertise.");
  }
  if (!rating.rationale || rating.rationale.length > 1000) {
    throw new Error("Provide a rationale of 1–1,000 characters.");
  }
  if (cannot.length && rating.disposition !== "escalate") {
    throw new Error("Any Cannot judge response requires disposition escalate.");
  }
  if (rating.disposition === "escalate" && rating.requested_expertise === "none") {
    throw new Error("Escalate requires qualitative, domain, or both expertise.");
  }
  if (rating.disposition !== "escalate" && rating.requested_expertise !== "none") {
    throw new Error("Non-escalation dispositions require requested expertise none.");
  }
  if (rating.serious_error_flags.length && rating.disposition === "accept") {
    throw new Error("Accept cannot include a serious-error flag.");
  }
  if (rating.disposition === "accept") {
    const scores = METRICS.map(([id]) => rating[id]);
    if (scores.some((value) => value === null || value < 4)) {
      throw new Error("Accept requires all three quality ratings to be 4 or 5.");
    }
  }
  return rating;
}

function lockRatingUi(rating) {
  byId("rating-form").hidden = true;
  byId("locked-rating").hidden = false;
  byId("locked-rating-json").textContent = JSON.stringify(rating, null, 2);
}

function addFinding() {
  const findings = byId("findings");
  if (findings.children.length >= 12) return;
  const fragment = byId("finding-template").content.cloneNode(true);
  const fieldset = fragment.querySelector(".finding");
  const select = fragment.querySelector(".finding-flag");
  for (const flag of ERROR_FLAGS) select.add(new Option(flag, flag));
  fragment.querySelector(".remove-finding").addEventListener("click", () => {
    fieldset.remove();
    renumberFindings();
  });
  findings.append(fragment);
  renumberFindings();
}

function renumberFindings() {
  [...byId("findings").children].forEach((node, index) => {
    node.querySelector(".finding-number").textContent = String(index + 1);
  });
}

function decodePointerToken(token) {
  return token.replace(/~1/g, "/").replace(/~0/g, "~");
}

function resolvePointer(documentValue, pointer) {
  if (!pointer.startsWith("/")) throw new Error("must start with /");
  let current = documentValue;
  for (const raw of pointer.slice(1).split("/")) {
    const token = decodePointerToken(raw);
    if (Array.isArray(current)) {
      if (!/^(0|[1-9]\d*)$/.test(token) || Number(token) >= current.length) throw new Error("array index is out of range");
      current = current[Number(token)];
    } else if (current !== null && typeof current === "object" && Object.hasOwn(current, token)) {
      current = current[token];
    } else {
      throw new Error("path does not exist");
    }
  }
  return current;
}

function collectFindings() {
  const excerptIds = new Set(state.item.evidence.map((row) => row.excerpt_id));
  return [...byId("findings").children].map((node, index) => {
    const locations = uniqueNonemptyLines(node.querySelector(".finding-locations").value, 12);
    const evidenceIds = uniqueNonemptyLines(node.querySelector(".finding-excerpts").value, 20);
    if (!locations.length) throw new Error(`Finding ${index + 1} needs at least one editable location.`);
    for (const pointer of locations) {
      if (!ALLOWED_LOCATION.some((pattern) => pattern.test(pointer))) {
        throw new Error(`Finding ${index + 1} location ${pointer} is not an editable candidate field.`);
      }
      try { resolvePointer(state.item, pointer); }
      catch (error) { throw new Error(`Finding ${index + 1} location ${pointer}: ${error.message}.`); }
    }
    const unknown = evidenceIds.filter((value) => !excerptIds.has(value));
    if (unknown.length) throw new Error(`Finding ${index + 1} cites unknown excerpt ID(s): ${unknown.join(", ")}.`);
    const issue = node.querySelector(".finding-issue").value.trim();
    const requestedChange = node.querySelector(".finding-change").value.trim();
    if (!issue || !requestedChange) throw new Error(`Finding ${index + 1} needs an issue and requested change.`);
    return {
      finding_id: `F${String(index + 1).padStart(2, "0")}`,
      error_flag: node.querySelector(".finding-flag").value,
      severity: node.querySelector(".finding-severity").value,
      output_locations: locations,
      evidence_excerpt_ids: evidenceIds,
      issue,
      requested_change: requestedChange,
    };
  });
}

function buildFeedback() {
  const status = STATUS_BY_DISPOSITION[state.lockedRating.disposition];
  const summary = byId("feedback-summary").value.trim();
  if (!summary) throw new Error("Provide an identity-free feedback summary.");
  const findings = collectFindings();
  if (status === "no_change" && findings.length) throw new Error("An accepted no-change rating cannot include findings.");
  if (["actionable_revision", "reject_or_regenerate"].includes(status) && !findings.length) {
    throw new Error("This disposition requires at least one actionable finding.");
  }
  const seriousFindingFlags = new Set(findings.filter((row) => row.severity === "serious").map((row) => row.error_flag));
  const ratingFlags = new Set(state.lockedRating.serious_error_flags);
  if (seriousFindingFlags.size !== ratingFlags.size || [...seriousFindingFlags].some((value) => !ratingFlags.has(value))) {
    throw new Error("Findings marked serious must exactly match the locked rating’s serious-error flags.");
  }
  return {
    feedback_status: status,
    model_feedback: {
      feedback_summary: summary,
      findings,
      preserve: uniqueNonemptyLines(byId("preserve").value, 12),
      uncertainties: uniqueNonemptyLines(byId("uncertainties").value, 12),
    },
  };
}

function showFeedback(rating, timingReceiptSha256) {
  state.lockedRating = rating;
  state.timingReceiptSha256 = timingReceiptSha256;
  lockRatingUi(rating);
  const status = STATUS_BY_DISPOSITION[rating.disposition];
  byId("feedback-status").textContent = status;
  byId("feedback-form").hidden = false;
  byId("add-finding").hidden = status === "no_change";
  if (["actionable_revision", "reject_or_regenerate"].includes(status) && byId("findings").children.length === 0) addFinding();
  byId("feedback-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitRating(event) {
  event.preventDefault();
  setError("rating-error", "");
  let rating;
  try { rating = buildRating(); }
  catch (error) { setError("rating-error", error.message); return; }

  const button = byId("submit-rating");
  button.disabled = true;
  [...byId("rating-form").elements].forEach((control) => { control.disabled = true; });
  let timing;
  try {
    timing = state.timer.stop();
    state.ratingPayloadAfterSubmit = { session_token: state.sessionToken, rating, ...timing };
  } catch (error) {
    setError("rating-error", error.message);
    return;
  }
  try {
    const response = await api("/api/rating", state.ratingPayloadAfterSubmit);
    state.ratingPayloadAfterSubmit = null;
    state.sessionToken = response.session_token;
    showFeedback(response.rating, response.timing_receipt_sha256);
  } catch (error) {
    setError("rating-error", `${error.message} The rating fields remain frozen. Use “Retry lock submission”; do not change them.`);
    button.textContent = "Retry lock submission";
    button.disabled = false;
    button.onclick = async () => {
      button.disabled = true;
      try {
        const response = await api("/api/rating", state.ratingPayloadAfterSubmit);
        state.ratingPayloadAfterSubmit = null;
        showFeedback(response.rating, response.timing_receipt_sha256);
      } catch (retryError) {
        setError("rating-error", retryError.message);
        button.disabled = false;
      }
    };
  }
}

async function submitFeedback(event) {
  event.preventDefault();
  setError("feedback-error", "");
  let feedback;
  try { feedback = buildFeedback(); }
  catch (error) { setError("feedback-error", error.message); return; }
  const button = byId("submit-feedback");
  button.disabled = true;
  try {
    const response = await api("/api/feedback", { session_token: state.sessionToken, ...feedback });
    byId("feedback-form").hidden = true;
    byId("done").hidden = false;
    byId("done-message").textContent = `${response.completed_count} of 24 frozen assignments complete. No outcomes have been computed.`;
    if (response.completed_count >= 24) byId("next-item").hidden = true;
    byId("done").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setError("feedback-error", error.message);
    button.disabled = false;
  }
}

function waitForVisibleStart() {
  const startAfterFrames = () => requestAnimationFrame(() => requestAnimationFrame(() => {
    state.timer = new DirectionJTimer();
    state.timer.start();
    byId("rating-form").hidden = false;
  }));
  if (!document.hidden) startAfterFrames();
  else {
    byId("timer-card").hidden = false;
    byId("timer-state").textContent = "Waiting · page hidden";
    byId("timer-idle").textContent = "Return to this page; timing has not started.";
    const listener = () => {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", listener);
        startAfterFrames();
      }
    };
    document.addEventListener("visibilitychange", listener);
  }
}

function renderSession(response) {
  state.sessionToken = response.session_token;
  state.item = response.item;
  state.assignment = response.assignment;
  byId("launch").hidden = true;
  byId("review").hidden = false;
  byId("assignment-heading").textContent = `Sequence ${response.assignment.sequence} of 24 · ${response.item.item_id}`;
  byId("guide").textContent = response.guide;
  byId("item").textContent = JSON.stringify(response.item, null, 2);
  if (response.state === "feedback_pending") {
    byId("rating-form").hidden = true;
    byId("timer-card").hidden = false;
    byId("timer-state").textContent = "Rating already locked";
    byId("timer-active").textContent = `${response.review_seconds.toFixed(3)}s active`;
    byId("timer-idle").textContent = "Resuming only the incomplete feedback sidecar.";
    showFeedback(response.rating, response.timing_receipt_sha256);
  } else {
    waitForVisibleStart();
  }
}

async function begin() {
  byId("begin").disabled = true;
  setError("rating-error", "");
  try {
    const response = await api("/api/session/start", { launch_nonce: state.launchNonce });
    renderSession(response);
  } catch (error) {
    byId("launch-status").textContent = error.message;
    byId("begin").disabled = false;
  }
}

async function bootstrap() {
  buildStaticForms();
  byId("begin").addEventListener("click", begin);
  byId("rating-form").addEventListener("submit", submitRating);
  byId("feedback-form").addEventListener("submit", submitFeedback);
  byId("add-finding").addEventListener("click", addFinding);
  byId("next-item").addEventListener("click", () => window.location.reload());
  window.addEventListener("beforeunload", (event) => {
    if (state.timer && !state.timer.closed) {
      event.preventDefault();
      event.returnValue = "An active unsubmitted review will lose its timing session.";
    }
  });
  try {
    const response = await api("/api/bootstrap");
    state.launchNonce = response.launch_nonce;
    byId("launch-status").textContent = response.feedback_pending
      ? `A rating is locked and awaits its feedback sidecar (${response.completed_count} of 24 complete).`
      : `${response.completed_count} of 24 assignments complete. The next item remains undisplayed until you begin.`;
    byId("begin").textContent = response.feedback_pending ? "Resume locked item feedback" : "Begin next assigned item";
    byId("begin").disabled = false;
  } catch (error) {
    byId("launch-status").textContent = error.message;
  }
}

bootstrap();
