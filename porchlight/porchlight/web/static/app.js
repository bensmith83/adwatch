// Porchlight page: polls /api/state every 5 s. No framework, no build step.
"use strict";

const $ = (id) => document.getElementById(id);
const LABELS = ["household", "known", "ignore"];
let state = null;
let openDetail = null;
let calibrating = null;
const RULE_NAMES = {R1: "Lingering stranger", R2: "Repeat visitor", R3: "New while armed", R4: "Known at odd hours"};

// The token arrives once as ?token=, which the server turns into a cookie.
if (location.search.includes("token=")) history.replaceState(null, "", location.pathname);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

function when(t) {
  if (!t) return "";
  const d = new Date(t * 1000);
  const ago = (state ? state.now : Date.now() / 1000) - t;
  if (ago < 86400) return d.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
  return d.toLocaleDateString([], {month: "short", day: "numeric"}) + " " +
         d.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
}

function dur(s) {
  s = Math.max(0, Math.round(s));
  if (s < 60) return s + " s";
  if (s < 3600) return Math.round(s / 60) + " min";
  return (s / 3600).toFixed(1) + " h";
}

function device(u) {
  const name = u.label_name || u.product || "Unknown device";
  const vendor = u.vendor && !name.includes(u.vendor) ? ` <span class="muted small">${esc(u.vendor)}</span>` : "";
  const weak = u.weak ? ` <span class="chip" title="Weak ID: may be a different device">weak ID</span>` : "";
  return `${esc(name)}${vendor} <span class="chip">…${esc(u.hint)}</span>${weak}`;
}

function labelControl(u, alertId) {
  const cur = u.label || "";
  const opts = ['<option value="">unlabelled</option>']
    .concat(LABELS.map((l) => `<option value="${l}"${l === cur ? " selected" : ""}>${l}</option>`)).join("");
  const data = alertId ? `data-alert="${alertId}"` : `data-unit="${u.id}"`;
  return `<span class="row" style="margin:0"><select class="label-select" ${data}>${opts}</select>` +
         `<input type="text" class="label-name" ${data} placeholder="name" value="${esc(u.label_name)}" size="10">` +
         `<button class="label-save" ${data}>Save</button></span>`;
}

async function api(path, body) {
  const opts = body === undefined ? {} :
    {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opts);
  if (r.status === 401) throw new Error("This page needs its token: open it once as /?token=…");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function alertCard(a, actions) {
  const sev = a.severity === "alert" ? "" : a.severity;
  return `<div class="alert ${sev}"><div class="title">${esc(a.title)}</div>
    <div>${esc(a.message)}</div>
    <div class="small muted">${esc(a.rule)} · ${when(a.created)}</div>
    ${actions && a.unit ? `<div class="row"><button class="ack" data-alert="${a.id}">Acknowledge</button>
      or label it: ${labelControl(a.unit, a.id)}</div>` : ""}</div>`;
}

function render() {
  const s = state;
  const arm = s.armed;
  $("armed-badge").textContent = arm.armed ? "ARMED" : "disarmed";
  $("armed-badge").className = "badge " + (arm.armed ? "armed" : "disarmed");
  const auto = arm.mode === "manual" ? "" : ` · automatic: ${arm.auto ? "armed" : "disarmed"}`;
  $("mode").textContent = `mode: ${arm.mode}${auto}${arm.override !== null ? " · overridden" : ""}`;
  $("arm-toggle").textContent = arm.armed ? "Disarm" : "Arm";
  $("clear-override").hidden = arm.override === null;

  $("alert-count").textContent = s.alerts.length ? `(${s.alerts.length})` : "";
  $("alerts").innerHTML = s.alerts.length ? s.alerts.map((a) => alertCard(a, true)).join("")
    : '<p class="empty">No open alerts.</p>';
  $("info-wrap").hidden = !s.info.length;
  $("info-count").textContent = s.info.length;
  $("info").innerHTML = s.info.map((a) => alertCard(a, true)).join("");

  const near = s.near.filter((n) => n.near);
  $("near-count").textContent = `(${near.length} near, ${s.near.length - near.length} further off)`;
  $("near").innerHTML = s.near.length ? s.near.map((n) => `<tr class="${n.near ? "" : "far"}">
      <td>${device(n)}</td><td class="hide-sm small">${esc(n.id_types.join(", "))}</td>
      <td>${esc(n.mobility)}</td><td>${dur(n.dwell_s)}</td>
      <td>${n.rssi} dBm <button class="calibrate small" data-unit="${n.id}" title="Follow this device's RSSI">track</button></td>
      <td>${n.label ? esc(n.label) : '<span class="muted">—</span>'}</td></tr>`).join("")
    : '<tr><td colspan="6" class="empty">Nothing with a persistent ID in range.</td></tr>';
  $("anon").textContent = `${s.about.anonymous_nearby} anonymous devices nearby (phones, trackers and ` +
    "other rotating addresses: counted, never tracked).";

  $("presence-section").hidden = arm.mode !== "presence";
  $("presence").innerHTML = s.presence_keys.length ? s.presence_keys.map((u) => `<div>${device(u)}</div>`).join("")
    : '<p class="empty">No presence keys yet. Label a device you carry as household.</p>';

  const l = s.learning;
  $("learning").innerHTML = l.active
    ? `<p>Learning until <b>${when(l.ends)}</b>. Nothing is pushed yet; what would have alerted is listed below so you can tune the thresholds.</p>`
    : `<p>Learning finished ${when(l.ends)}. Neighbours' fixed devices and regulars were baselined as known.</p>`;
  $("would-count").textContent = s.would_have.length;
  $("would").innerHTML = s.would_have.map((a) => alertCard(a, false)).join("") || '<p class="empty">Nothing.</p>';

  $("rule-counts").innerHTML = '<thead><tr><th>Rule</th><th>Pushed</th><th>Info only</th><th>Would have (learning)</th></tr></thead>' +
    Object.entries(s.rule_counts).map(([r, c]) => `<tr><td>${esc(r)} ${esc(RULE_NAMES[r] || "")}</td>
      <td>${c.alert + c.warn}</td><td>${c.info}</td><td>${c.would_have}</td></tr>`).join("");

  const ab = s.about;
  $("about").innerHTML = [
    ["Parsers", ab.parsers ?? "?"], ["Parser commit", ab.commit ?? "?"],
    ["Uptime", dur(ab.uptime_s)], ["Ads/s", ab.ads_per_s], ["Devices known", ab.units],
    ["Anonymous nearby", ab.anonymous_nearby],
  ].map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
}

async function refresh() {
  try {
    state = await api("/api/state");
    render();
  } catch (e) {
    $("alerts").innerHTML = `<p class="alert">${esc(e.message)}</p>`;
  }
}

function sparkline(samples, floor) {
  if (!samples.length) return "";
  const t0 = samples[samples.length - 1][0] - 60;
  const lo = Math.min(floor, ...samples.map((x) => x[1])) - 3, hi = Math.max(floor, ...samples.map((x) => x[1])) + 3;
  const y = (r) => (60 * (hi - r) / (hi - lo)).toFixed(1);
  const pts = samples.map(([t, r]) => `${(300 * (t - t0) / 60).toFixed(1)},${y(r)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 300 60" preserveAspectRatio="none">
    <line x1="0" x2="300" y1="${y(floor)}" y2="${y(floor)}"></line><polyline points="${pts}"></polyline></svg>`;
}

async function calibrate() {
  if (calibrating === null) return;
  try {
    const c = await api(`/api/units/${calibrating}/rssi`);
    $("calibrate").innerHTML = `<div>${device(c.unit)}</div>
      <div class="big">${c.rssi === null ? "—" : c.rssi + " dBm"}</div>
      <div class="small">${c.rssi === null ? "not heard in the last minute" :
        (c.near ? "near" : "far") + ` (floor ${c.floor} dBm) · last minute: ${c.min} to ${c.max} dBm`}</div>
      ${sparkline(c.samples, c.floor)}`;
  } catch (e) { $("calibrate").textContent = e.message; }
}

async function loadDevices() {
  const list = await api("/api/units?q=" + encodeURIComponent($("search").value));
  $("device-count").textContent = `${list.length} shown`;
  $("devices").innerHTML = list.map((u) => `<tr><td><a href="#" class="open-unit" data-unit="${u.id}">${device(u)}</a></td>
      <td class="hide-sm small">${esc(u.id_types.join(", "))}</td><td>${esc(u.mobility)}</td>
      <td>${when(u.last_seen)}</td><td>${labelControl(u)}</td></tr>`).join("")
    || '<tr><td colspan="5" class="empty">No devices.</td></tr>';
}

async function showDetail(id) {
  openDetail = id;
  const d = await api("/api/units/" + id);
  $("device-detail").innerHTML = `<h3>${device(d)}</h3>
    <p class="small muted">${esc(d.id_types.join(", "))} · moves: ${esc(d.mobility)} · first seen ${when(d.first_seen)}
      ${d.baseline ? " · baselined" : ""}</p>
    <table><thead><tr><th>Visit</th><th>Length</th><th>Sightings</th><th>Max RSSI</th></tr></thead><tbody>
    ${d.visits.map((v) => `<tr><td>${when(v.start)}</td><td>${dur(v.end - v.start)}</td><td>${v.n}</td>
      <td>${v.max_rssi} dBm</td></tr>`).join("") || '<tr><td colspan="4" class="empty">No visits.</td></tr>'}
    </tbody></table>`;
}

document.addEventListener("click", async (ev) => {
  const t = ev.target;
  try {
    if (t.id === "arm-toggle") { await api("/api/arm", {armed: !state.armed.armed}); }
    else if (t.id === "clear-override") { await api("/api/arm", {clear_override: true}); }
    else if (t.id === "relearn") {
      if (!confirm("Clear the automatic baseline and learn again? Labels are kept.")) return;
      await api("/api/relearn", {});
    }
    else if (t.classList.contains("ack")) { await api(`/api/alerts/${t.dataset.alert}/ack`, {}); }
    else if (t.classList.contains("label-save")) {
      const sel = t.dataset.alert ? `[data-alert="${t.dataset.alert}"]` : `[data-unit="${t.dataset.unit}"]`;
      const label = document.querySelector(".label-select" + sel).value || null;
      const name = document.querySelector(".label-name" + sel).value;
      if (t.dataset.alert) await api(`/api/alerts/${t.dataset.alert}/ack`, {label, name});
      else await api(`/api/units/${t.dataset.unit}/label`, {label, name});
      loadDevices();
    }
    else if (t.classList.contains("calibrate")) {
      calibrating = t.dataset.unit;
      $("calibrate-section").hidden = false;
      await calibrate();
      $("calibrate-section").scrollIntoView({behavior: "smooth"});
      return;
    }
    else if (t.id === "calibrate-close") { calibrating = null; $("calibrate-section").hidden = true; return; }
    else if (t.closest(".open-unit")) { ev.preventDefault(); await showDetail(t.closest(".open-unit").dataset.unit); return; }
    else return;
    await refresh();
  } catch (e) { alert(e.message); }
});

let searchTimer = null;
$("search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadDevices, 250); });

refresh();
loadDevices();
setInterval(refresh, 5000);
setInterval(calibrate, 1000);
setInterval(() => { if (!document.activeElement || !document.activeElement.closest("#devices")) loadDevices(); }, 30000);
