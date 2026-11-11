const stages = ["saved", "applied", "interview", "offer", "rejected"];
const byId = (id) => document.getElementById(id);
const titleCase = (value) => value[0].toUpperCase() + value.slice(1);

function notify(message, error = false) {
  const notice = byId("notice");
  notice.setAttribute("role", error ? "alert" : "status");
  notice.setAttribute("aria-live", error ? "assertive" : "polite");
  notice.textContent = message;
  notice.hidden = !message;
  notice.className = error ? "notice error" : "notice";
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", "X-JobTrack": "1", ...options.headers },
    });
  } catch {
    throw new Error("Could not connect to JobTrack. Check that the server is running and try again.");
  }
  if (!response.ok) {
    if (response.status === 401) showAccount(null);
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc.slice(1).join(".")}: ${item.msg}`).join("; ")
      : detail || "The request failed. Please try again.";
    throw new Error(message);
  }
  if (response.status === 204) return null;
  try {
    return await response.json();
  } catch {
    throw new Error("JobTrack returned an unreadable response. Refresh to check the latest data.");
  }
}

function element(tag, text, className = "") {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  node.className = className;
  return node;
}

function filterParameters() {
  const parameters = new URLSearchParams({ search: byId("search").value });
  if (byId("stage").value) parameters.set("status", byId("stage").value);
  return parameters;
}

let loadVersion = 0;
function followUpLabel(application, now = new Date()) {
  if (!application.follow_up_date) return "No follow-up date";
  const date = application.follow_up_date;
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const active = !["offer", "rejected"].includes(application.status);
  const urgency = active && date <= today ? (date === today ? " — Today" : " — Overdue") : "";
  return `Follow up: ${date}${urgency}`;
}

async function load() {
  const version = ++loadVersion;
  const parameters = filterParameters();
  byId("applications").setAttribute("aria-busy", "true");
  let results;
  try {
    results = await Promise.all([
      request(`/api/applications?${parameters}`), request("/api/stats"),
    ]);
  } finally {
    if (version === loadVersion) byId("applications").setAttribute("aria-busy", "false");
  }
  const [applications, stats] = results;
  if (version !== loadVersion) return;
  const count = applications.length;
  const summary = count === 100
    ? "Showing the first 100 matching applications."
    : `Showing ${count} matching application${count === 1 ? "" : "s"}.`;
  byId("application-summary").textContent = `${summary} Statistics cover your whole tracker.`;
  byId("total").textContent = stats.total;
  for (const key of ["applied", "interview", "offer"]) byId(key).textContent = stats.by_status[key];
  const container = byId("applications");
  container.replaceChildren();
  if (!applications.length) {
    const message = stats.total === 0
      ? "No applications yet. Add your first opportunity using the form."
      : "No applications match these filters. Try another search or use Clear filters.";
    container.append(element("p", message, "empty"));
    return;
  }
  for (const application of applications) {
    const card = element("article", undefined, "application-card");
    const top = element("div", undefined, "card-top");
    const heading = element("div");
    heading.append(element("h3", application.company), element("p", application.role));
    const select = element("select");
    select.setAttribute("aria-label", `Stage for ${application.company} ${application.role}`);
    for (const stage of stages) {
      const option = element("option", titleCase(stage));
      option.value = stage;
      option.selected = application.status === stage;
      select.append(option);
    }
    select.addEventListener("change", async () => {
      if (select.disabled) return;
      select.disabled = true;
      const newStatus = select.value;
      let saved = false;
      try {
        await request(`/api/applications/${application.id}`, { method: "PATCH", body: JSON.stringify({ status: newStatus }) });
        application.status = newStatus;
        saved = true;
        await load();
        notify("Application stage updated.");
      } catch (error) {
        select.value = application.status;
        notify(saved ? "Stage saved, but the list could not refresh. Use Refresh to reload applications." : error.message, true);
      } finally { select.disabled = false; }
    });
    top.append(heading, select);
    card.append(top);
    if (application.notes) card.append(element("p", application.notes, "notes"));
    const actions = element("div", undefined, "card-actions");
    actions.append(element("span", followUpLabel(application), "subtle"));
    if (application.url) {
      const link = element("a", "View role ↗");
      link.setAttribute("aria-label", `View ${application.role} at ${application.company} (opens in a new tab)`);
      link.href = application.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      actions.append(link);
    }
    const remove = element("button", "Delete", "text-button");
    remove.setAttribute("aria-label", `Delete application for ${application.role} at ${application.company}`);
    remove.type = "button";
    remove.addEventListener("click", async () => {
      if (remove.disabled) return;
      if (!window.confirm(`Delete the application for ${application.role} at ${application.company}? This cannot be undone.`)) return;
      remove.disabled = true;
      remove.textContent = "Deleting…";
      let deleted = false;
      try {
        await request(`/api/applications/${application.id}`, { method: "DELETE" });
        deleted = true;
        card.remove();
        await load();
        notify("Application deleted.");
      } catch (error) {
        notify(deleted ? "Application deleted, but the list could not refresh. Use Refresh to reload applications." : error.message, true);
      } finally { remove.disabled = deleted; remove.textContent = deleted ? "Deleted" : "Delete"; }
    });
    actions.append(remove); card.append(actions); container.append(card);
  }
}

byId("application-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  if (button.disabled) return;
  const values = Object.fromEntries(new FormData(form));
  values.follow_up_date = values.follow_up_date || null;
  button.disabled = true;
  button.textContent = "Saving…";
  let saved = false;
  try {
    await request("/api/applications", { method: "POST", body: JSON.stringify(values) });
    saved = true;
    form.reset();
    byId("company").focus();
    await load();
    notify("Application saved.");
  } catch (error) {
    notify(saved ? "Application saved, but the list could not refresh. Use Refresh to reload applications." : error.message, true);
  }
  finally { button.disabled = false; button.textContent = "Save application"; }
});

let debounce;
byId("refresh").addEventListener("click", async () => {
  const button = byId("refresh");
  if (button.disabled) return;
  clearTimeout(debounce);
  button.disabled = true;
  button.textContent = "Refreshing…";
  try {
    await load();
    notify("Applications refreshed.");
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; button.textContent = "Refresh"; }
});
async function clearFilters() {
  clearTimeout(debounce);
  byId("search").value = "";
  byId("stage").value = "";
  try {
    await load();
    notify("");
  } catch (error) { notify(error.message, true); }
}
byId("clear-filters").addEventListener("click", clearFilters);
byId("search").addEventListener("keydown", async (event) => {
  if (event.key !== "Escape") return;
  event.preventDefault();
  await clearFilters();
});
byId("export-csv").addEventListener("click", () => {
  const link = element("a");
  link.href = `/api/applications/export?${filterParameters()}`;
  link.download = "jobtrack-applications.csv";
  document.body.append(link);
  link.click();
  link.remove();
});
byId("search").addEventListener("input", () => { clearTimeout(debounce); debounce = setTimeout(() => load().catch((error) => notify(error.message, true)), 200); });
byId("stage").addEventListener("change", () => load().catch((error) => notify(error.message, true)));
function setPasswordVisibility(visible) {
  byId("auth-password").type = visible ? "text" : "password";
  byId("toggle-password").textContent = visible ? "Hide password" : "Show password";
  byId("toggle-password").setAttribute("aria-pressed", String(visible));
}

byId("toggle-password").addEventListener("click", () => {
  setPasswordVisibility(byId("auth-password").type === "password");
});

function showAccount(user) {
  clearTimeout(debounce);
  byId("applications").setAttribute("aria-busy", "false");
  byId("application-summary").textContent = "";
  setPasswordVisibility(false);
  ++loadVersion;
  byId("auth-panel").hidden = Boolean(user);
  byId("tracker").hidden = !user;
  byId("account-name").textContent = user ? `Signed in as ${user.username}` : "";
  byId("applications").replaceChildren();
  for (const id of ["total", "applied", "interview", "offer"]) byId(id).textContent = "0";
  byId("application-form").reset();
  byId("search").value = "";
  byId("stage").value = "";
}

let authPending = false;
byId("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (authPending) return;
  authPending = true;
  const form = event.currentTarget;
  form.setAttribute("aria-busy", "true");
  const action = event.submitter?.value === "register" ? "register" : "login";
  const buttons = form.querySelectorAll("button");
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const user = await request(`/api/auth/${action}`, {
      method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    form.reset();
    showAccount(user);
    await load();
    notify("Signed in.");
  } catch (error) { notify(error.message, true); }
  finally {
    authPending = false;
    form.setAttribute("aria-busy", "false");
    buttons.forEach((button) => { button.disabled = false; });
  }
});

byId("logout").addEventListener("click", async () => {
  const button = byId("logout");
  if (button.disabled) return;
  button.disabled = true;
  button.textContent = "Signing out…";
  try {
    await request("/api/auth/logout", { method: "POST" });
    showAccount(null);
    notify("Signed out.");
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; button.textContent = "Sign out"; }
});

async function restoreSession() {
  let user;
  try {
    user = await request("/api/auth/me");
  } catch (error) {
    showAccount(null);
    if (error.message !== "Please sign in.") notify(error.message, true);
    return;
  }
  showAccount(user);
  try { await load(); }
  catch (error) { notify(error.message, true); }
}

restoreSession();
