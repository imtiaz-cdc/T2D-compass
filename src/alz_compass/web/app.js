"use strict";

// All registry and model output is displayed as text, never interpreted as HTML.
const byId = (id) => document.getElementById(id);
const state = { searchBusy: false, cardBusy: false, cardRequest: 0, askBusy: false, assistantAvailable: false };

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = String(text);
  return element;
}

function append(parent, ...children) {
  for (const child of children) if (child) parent.append(child);
  return parent;
}

function label(key) {
  return String(key).replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

function display(value) {
  if (value === null || value === undefined || value === "") return "Not reported in this record.";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(display).join("; ") : "No entries reported.";
  return String(value);
}

function timestamp(value) {
  if (!value) return "Not reported";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, { timeZone: "UTC", year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }) + " UTC";
}

function modeLabel(mode) {
  if (mode === "live") return "Live registry retrieval";
  if (mode === "snapshot") return "Frozen registry snapshot";
  return "Source mode not reported";
}

function sourceLink(url, text = "View registry record ↗") {
  // Source URLs are untrusted data. Only the public source site can be linked.
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || parsed.hostname !== "clinicaltrials.gov" || parsed.username || parsed.password) return null;
    const link = node("a", "source-link", text);
    link.href = parsed.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", text.replace("↗", "").trim() + " (opens a new tab)");
    return link;
  } catch { return null; }
}

function feedback(id, message = "", kind = "") {
  const element = byId(id);
  element.textContent = message;
  element.className = "feedback" + (kind ? " " + kind : "");
}

function notice(message, kind = "warning") {
  return node("div", "notice " + kind, message);
}

function clearArea(id) {
  const area = byId(id);
  area.replaceChildren();
  area.hidden = true;
}

function focusArea(area) {
  area.tabIndex = -1;
  area.focus({ preventScroll: true });
  area.scrollIntoView({ behavior: "auto", block: "start" });
}

function downloadButton(data, filename, text = "Export JSON") {
  const button = node("button", "button quiet small", text);
  button.type = "button";
  button.addEventListener("click", () => {
    // Export only actual response data. Nothing is stored in the browser.
    const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = node("a");
    link.href = url;
    link.download = filename.replace(/[^a-zA-Z0-9_.-]/g, "_");
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  return button;
}

function disclosure(title, content, open = false) {
  const details = node("details", "detail-section");
  details.open = open;
  append(details, node("summary", "", title), content);
  return details;
}

function jsonDisclosure(title, data) {
  return disclosure(title, node("pre", "raw-json", JSON.stringify(data, null, 2)));
}

function fieldList(values) {
  if (!values || typeof values !== "object") return node("p", "missing small", display(values));
  const dl = node("dl", "data-fields");
  for (const [key, value] of Object.entries(values)) {
    const dd = node("dd");
    if (value && typeof value === "object" && !Array.isArray(value)) dd.append(fieldList(value));
    else if (Array.isArray(value) && value.some((item) => item && typeof item === "object")) dd.append(recordList(value));
    else {
      dd.textContent = display(value);
      if (value === null || value === undefined) dd.className = "missing";
    }
    append(dl, node("dt", "", label(key)), dd);
  }
  return dl;
}

function recordList(records) {
  if (!Array.isArray(records) || !records.length) return node("p", "missing small", display(records));
  const group = node("div");
  records.forEach((record, index) => {
    const item = node("section", "record-group");
    append(item, node("h4", "", "Entry " + (index + 1)), fieldList(record));
    group.append(item);
  });
  return group;
}

function flagsList(flags) {
  const list = node("ul", "flag-list");
  for (const flag of Array.isArray(flags) ? flags : []) {
    const item = node("li");
    append(item, node("span", "", flag.message || label(flag.code || "Review flag")), flag.field ? node("span", "flag-field", flag.field) : null);
    list.append(item);
  }
  return list;
}

function resultBadge(status) {
  const text = status === "posted" ? "Results posted" : status === "not_posted" ? "Results not posted" : "Results availability unknown";
  return node("span", "badge " + (status === "posted" ? "teal" : "amber"), text);
}

function evidenceCard(card) {
  const article = node("article", "evidence-card");
  const identity = card.identity || {};
  const provenance = card.provenance || {};
  const status = card.status || {};
  const design = card.design || {};
  const enrollment = card.enrollment || {};
  const results = card.results || {};
  if (card.source_mode !== "live") article.append(node("p", "source-mode-banner", card.source_mode === "snapshot" ? "Snapshot evidence: this is a frozen public registry record, not a current registry response." : "The source mode was not reported. Check the raw response before using this evidence."));
  const header = node("header", "evidence-header");
  const badges = append(node("div", "badge-row"), node("span", "badge", display(status.overall_status)), resultBadge(results.status), node("span", "badge " + (card.source_mode === "live" ? "teal" : "amber"), modeLabel(card.source_mode)));
  append(header, node("span", "record-id", display(identity.nct_id)), node("h2", "", display(identity.title)), badges, sourceLink(identity.study_url), node("p", "provenance-line", "Retrieved " + timestamp(provenance.retrieved_at) + " · Registry updated " + display(provenance.registry_update_date)), node("p", "review-label", card.label || "Registry extraction pending human review"));
  article.append(header);
  const stats = node("div", "evidence-stats");
  for (const [name, value] of [["Phase", display(design.phases)], ["Enrollment · " + display(enrollment.type), display(enrollment.count)], ["Completion · " + display(status.completion_date_type), display(status.completion_date)]]) {
    stats.append(append(node("div"), node("span", "stat-label", name), node("span", "stat-value", value)));
  }
  article.append(stats);
  const body = node("div", "evidence-body");
  const flags = Array.isArray(card.review_flags) ? card.review_flags : [];
  append(body,
    disclosure("Review flags (" + flags.length + ")", flags.length ? flagsList(flags) : node("p", "muted small", "No flags returned. Human review is still needed."), true),
    disclosure("Study identity and status", append(node("div"), fieldList(identity), node("hr"), fieldList(status))),
    disclosure("Study design and enrollment", append(node("div"), fieldList(design), node("hr"), fieldList(enrollment))),
    disclosure("Population and eligibility", fieldList(card.population)),
    disclosure("Study arms", recordList(card.arms)),
    disclosure("Interventions", recordList(card.interventions)),
    disclosure("Primary outcomes listed in the registry", recordList(card.primary_outcomes)),
    disclosure("Results availability", append(node("div"), fieldList(results), sourceLink(results.url, results.status === "posted" ? "Open posted registry results ↗" : "Inspect results availability at source ↗"))),
  );
  const limits = node("ul", "limitation-list");
  for (const limitation of Array.isArray(card.limitations) ? card.limitations : []) limits.append(node("li", "", limitation));
  body.append(disclosure("Interpretation limits", limits, true));
  const provenanceContent = append(node("div"), fieldList({ retrieved_at: provenance.retrieved_at, registry_update_date: provenance.registry_update_date, source_mode: card.source_mode, schema_version: card.schema_version, snapshot_sha256: provenance.snapshot_sha256 }), sourceLink(provenance.api_url, "Open source API record ↗"), node("p", "muted small", "The full export preserves each mapped field’s original value and source path."), node("pre", "raw-json", JSON.stringify(provenance.fields || {}, null, 2)));
  append(body, disclosure("Field provenance and original source values", provenanceContent));
  article.append(body);
  return article;
}

function studyList(studies, allowLookup = true) {
  const list = node("div", "trial-list");
  for (const study of studies) {
    const article = node("article", "trial-item");
    const top = append(node("div", "trial-topline"), node("span", "record-id", display(study.nct_id)), resultBadge(study.results_status));
    const actions = node("div", "trial-actions");
    if (allowLookup && /^NCT[0-9]{8}$/.test(study.nct_id || "")) {
      const button = node("button", "button secondary small", "Open evidence card");
      button.type = "button";
      button.dataset.cardLookup = "true";
      button.disabled = state.cardBusy;
      button.addEventListener("click", () => {
        byId("nct-id").value = study.nct_id;
        loadCard(study.nct_id);
      });
      actions.append(button);
    }
    append(actions, sourceLink(study.study_url));
    append(article, top, node("h3", "", display(study.title)), node("p", "conditions", display(study.conditions)), actions);
    list.append(article);
  }
  return list;
}

async function api(path, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), path === "/api/ask" ? 240000 : 135000);
  try {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: controller.signal,
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error("The app did not return a readable response. Refresh this page to check your sign-in, then try again."); }
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("The app returned an unexpected response. Please try again.");
    if (!response.ok) {
      const error = new Error(data.error?.message || "The request could not be completed (HTTP " + response.status + ").");
      error.data = data;
      throw error;
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request took too long. No new result was accepted. Please try again.");
    if (error instanceof TypeError) throw new Error("The app could not be reached. Check your connection and sign-in, then try again.");
    throw error;
  } finally { clearTimeout(timer); }
}

function renderSearch(data) {
  const area = byId("search-results");
  area.replaceChildren();
  area.hidden = false;
  const studies = Array.isArray(data.studies) ? data.studies : [];
  const heading = append(node("div"), node("h2", "", studies.length + " candidate " + (studies.length === 1 ? "trial" : "trials")), node("p", "", modeLabel(data.source_mode) + " · Retrieved " + timestamp(data.retrieved_at)));
  append(area, append(node("div", "result-toolbar"), heading, downloadButton(data, "t2d-compass-search.json")));
  if (data.error) area.append(notice((data.error.message || "Search could not be completed.") + (studies.length ? " The records below are partial results only." : ""), "error"));
  if (studies.length) area.append(studyList(studies));
  else if (data.status === "no_matches" || data.status === "ok") area.append(append(node("div", "empty-result"), node("h3", "", "No candidate records returned"), node("p", "", "Try a different intervention or clear the field to browse. No matches in this bounded search does not establish that no relevant trials exist.")));
  if (Array.isArray(data.review_flags) && data.review_flags.length) area.append(append(node("div", "notice warning"), flagsList(data.review_flags)));
  append(area, jsonDisclosure("Search criteria and full response", data));
}

byId("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.searchBusy) return;
  state.searchBusy = true;
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  form.setAttribute("aria-busy", "true");
  clearArea("search-results");
  state.cardRequest += 1;
  clearArea("card-area");
  feedback("card-feedback");
  byId("starting-state").hidden = true;
  feedback("search-feedback", "Searching the configured registry source…", "loading");
  try {
    const data = await api("/api/search", { intervention: byId("intervention").value.trim() || null, limit: Number(byId("limit").value) });
    renderSearch(data);
    feedback("search-feedback", data.error ? "Search returned a problem. See the response below." : "Search finished.", data.error ? "error" : "success");
  } catch (error) {
    feedback("search-feedback", error.message, "error");
    if (error.data) renderSearch(error.data);
  } finally {
    state.searchBusy = false;
    button.disabled = false;
    form.removeAttribute("aria-busy");
  }
});

function setCardBusy(busy) {
  state.cardBusy = busy;
  byId("card-form").querySelector("button").disabled = busy;
  document.querySelectorAll("[data-card-lookup]").forEach((button) => { button.disabled = busy; });
  byId("card-form").setAttribute("aria-busy", String(busy));
}

async function loadCard(nctId) {
  if (state.cardBusy) return;
  const request = ++state.cardRequest;
  setCardBusy(true);
  clearArea("card-area");
  byId("starting-state").hidden = true;
  feedback("card-feedback", "Retrieving " + nctId + "…", "loading");
  try {
    const data = await api("/api/card", { nct_id: nctId });
    if (request !== state.cardRequest) return;
    if (data.status !== "ok" || !data.card) {
      const error = new Error(data.error?.message || "No evidence card was returned.");
      error.data = data;
      throw error;
    }
    const area = byId("card-area");
    area.hidden = false;
    append(area, append(node("div", "result-toolbar"), node("h2", "", "Evidence card"), downloadButton(data, "t2d-compass-" + nctId + ".json")), evidenceCard(data.card), jsonDisclosure("Full evidence response", data));
    feedback("card-feedback", nctId + " retrieved. Review the evidence and flags.", "success");
    focusArea(area);
  } catch (error) {
    if (request !== state.cardRequest) return;
    feedback("card-feedback", error.message, "error");
    if (error.data) {
      const area = byId("card-area");
      area.hidden = false;
      append(area, notice("Evidence card unavailable: " + error.message, "error"), downloadButton(error.data, "t2d-compass-card-error.json", "Export error response"));
    }
  } finally { setCardBusy(false); }
}

byId("card-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const nctId = byId("nct-id").value.trim().toUpperCase();
  if (!/^NCT[0-9]{8}$/.test(nctId)) { feedback("card-feedback", "Enter NCT followed by exactly 8 digits.", "error"); return; }
  byId("nct-id").value = nctId;
  loadCard(nctId);
});

function renderTrace(trace) {
  const area = byId("assistant-results");
  area.replaceChildren();
  area.hidden = false;
  const panel = node("article", "answer-panel");
  const complete = trace.status === "completed";
  append(panel, append(node("div", "result-toolbar"), node("h2", "", complete ? "Assistant response" : "Request not completed"), downloadButton(trace, "t2d-compass-assistant-trace.json", "Export trace")));
  if (trace.question) panel.append(append(node("div", "notice neutral"), node("strong", "", "Your question"), node("span", "", trace.question)));
  if (trace.error) panel.append(notice(trace.error.message || "The assistant did not complete this request.", "error"));
  if (trace.final_output) panel.append(node("div", "answer-body", trace.final_output));
  else if (!trace.error) panel.append(notice("No final answer was returned. Inspect the trace below.", "warning"));
  const events = Array.isArray(trace.tool_calls) ? trace.tool_calls : [];
  append(panel, node("p", "trace-summary", "Run status: " + display(trace.status) + " · " + events.length + " tool " + (events.length === 1 ? "call" : "calls") + " · Started " + timestamp(trace.started_at)), notice("AI-generated interpretation is pending human review. Check the retrieved records and their limitations before using the answer.", "neutral"));
  if (events.length) {
    const evidence = node("div");
    events.forEach((event, index) => {
      const item = node("section", "trace-event");
      const data = event.result?.data;
      const title = event.name === "find_completed_trials" ? "Candidate trial search" : event.name === "get_trial_evidence_card" ? "Trial evidence card" : "Tool response";
      append(item, node("h4", "", (index + 1) + ". " + title + " · " + display(event.status)), fieldList({ arguments: event.arguments }));
      if (data?.error) item.append(notice(data.error.message || "The source request returned a problem.", "error"));
      if (data?.card) item.append(evidenceCard(data.card));
      if (Array.isArray(data?.studies)) {
        item.append(node("p", "provenance-line", modeLabel(data.source_mode) + " · Retrieved " + timestamp(data.retrieved_at)));
        if (data.studies.length) item.append(studyList(data.studies, false));
        else item.append(node("p", "muted small", "No candidate records returned."));
        if (Array.isArray(data.review_flags)) item.append(flagsList(data.review_flags));
      }
      append(item, jsonDisclosure("Exact tool call and response", event));
      evidence.append(item);
    });
    panel.append(disclosure("Retrieved evidence and tool calls (" + events.length + ")", evidence, true));
  } else panel.append(notice("No tool calls were recorded for this answer. It should not be treated as newly retrieved trial evidence.", "warning"));
  panel.append(jsonDisclosure("Full run trace", trace));
  area.append(panel);
}

byId("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.askBusy || !state.assistantAvailable) return;
  const question = byId("question").value.trim();
  if (!question) { feedback("ask-feedback", "Enter a research question first.", "error"); return; }
  state.askBusy = true;
  byId("ask-submit").disabled = true;
  byId("ask-form").setAttribute("aria-busy", "true");
  clearArea("assistant-results");
  feedback("ask-feedback", "The assistant is working with the trial tools. This may take a few minutes…", "loading");
  try {
    const trace = await api("/api/ask", { question });
    renderTrace(trace);
    feedback("ask-feedback", trace.status === "completed" ? "Response ready for review." : "The request did not complete. See the details below.", trace.status === "completed" ? "success" : "error");
  } catch (error) {
    feedback("ask-feedback", error.message, "error");
    if (error.data) renderTrace(error.data);
  } finally {
    state.askBusy = false;
    byId("ask-submit").disabled = !state.assistantAvailable;
    byId("ask-form").removeAttribute("aria-busy");
  }
});

const tabs = [byId("explore-tab"), byId("assistant-tab")];
function selectTab(selected) {
  tabs.forEach((tab) => {
    const active = tab === selected;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    byId(tab.getAttribute("aria-controls")).hidden = !active;
  });
}
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") next = tabs[(index + 1) % tabs.length];
    if (event.key === "Home") next = tabs[0];
    if (event.key === "End") next = tabs[tabs.length - 1];
    if (next) { event.preventDefault(); selectTab(next); next.focus(); }
  });
});

async function checkStatus() {
  try {
    const status = await api("/api/status");
    const source = byId("source-status");
    source.textContent = modeLabel(status.data_mode);
    source.className = "status-indicator " + (status.data_mode === "live" ? "live" : "snapshot");
    byId("version").textContent = status.version ? "Version " + status.version : "";
    if (status.data_mode !== "live") {
      byId("connection-notice").hidden = false;
      byId("connection-notice").textContent = status.data_mode === "snapshot" ? "Snapshot mode is active. Results come from selected frozen public records; they do not establish the current state of the registry." : "The app did not identify its data mode. Check the source information on each result.";
    }
    const assistant = status.assistant || {};
    state.assistantAvailable = assistant.available === true;
    byId("question").disabled = !state.assistantAvailable;
    byId("ask-submit").disabled = !state.assistantAvailable;
    byId("assistant-model").textContent = assistant.model || "Not configured";
    byId("assistant-availability").textContent = assistant.message || (state.assistantAvailable ? "Assistant is configured. Model access is checked when you submit a question." : "The optional assistant is not configured. You can still search trials and open evidence cards in Explore evidence.");
    byId("assistant-availability").className = "notice " + (state.assistantAvailable ? "neutral" : "warning");
  } catch (error) {
    byId("source-status").textContent = "App status unavailable";
    byId("connection-notice").hidden = false;
    byId("connection-notice").textContent = error.message;
    byId("assistant-availability").textContent = "Assistant availability could not be checked. Refresh the page after checking the app connection.";
    byId("assistant-model").textContent = "Unavailable";
  }
}

checkStatus();
