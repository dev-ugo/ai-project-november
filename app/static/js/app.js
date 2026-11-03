/* Parcours : connexion → analyse → résultat ; historique à la demande. */
"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const MAX_FILE_SIZE = 1024 * 1024;
  const MAX_VISIBLE_FINDINGS = 200;
  const numberFormat = new Intl.NumberFormat("fr-CH");
  const dateFormat = new Intl.DateTimeFormat("fr-CH", {dateStyle: "medium", timeStyle: "short"});
  let user = null;
  let selectedFile = null;
  let report = null;
  let busy = false;
  let ready = false;
  let pendingRoute = false;
  let authMode = "login";

  function status(id, message = "", error = false) {
    $(id).textContent = message;
    $(id).classList.toggle("is-error", error);
  }

  function showView(view, focus = true) {
    if (!user) view = "auth";
    $("main").dataset.view = view;
    $("account").hidden = view !== "auth";
    $("private-workspace").hidden = !user;
    $("account-connected").hidden = !user;
    $("upload-view").hidden = view !== "analysis";
    $("history").hidden = view !== "history";
    $("analysis-results").hidden = view !== "report";
    const headings = {
      auth: ["Un CSV plus clair.", "Repérez les doublons et les cellules vides, en quelques secondes."],
      analysis: ["Analyser un fichier", "Ajoutez votre CSV. Nous repérons les doublons et les cellules vides."],
      report: ["Votre résultat", ""],
      history: ["Vos analyses", "Vos 50 derniers rapports, visibles uniquement par vous."]
    };
    const [title, description] = headings[view];
    $("page-title").textContent = title;
    $("page-description").textContent = description;
    $("page-description").hidden = !description;
    document.title = `${title} · CSV Check`;
    for (const name of ["analysis", "history"]) {
      if (view === name) $("nav-" + name).setAttribute("aria-current", "page");
      else $("nav-" + name).removeAttribute("aria-current");
    }
    $("account-menu").open = false;
    if (focus) {
      $("page-title").focus({preventScroll: true});
      window.scrollTo({top: 0, behavior: "instant"});
    }
  }

  function setBusy(value, action = "") {
    busy = value;
    document.querySelectorAll("button, input, select").forEach(control => { control.disabled = value; });
    $("analyze-button").disabled = value || !selectedFile || !user;
    $("email-report-button").disabled = value || !report?.correction_available || Boolean(report?.email_sent_at);
    $("analyze-spinner").hidden = !(value && action === "analysis");
    $("analyze-label").textContent = value && action === "analysis" ? "Analyse en cours…" : "Analyser le fichier";
    $("auth-submit").textContent = value && action === "account" ? "Veuillez patienter…" : authMode === "register" ? "Créer mon compte" : "Se connecter";
    $("email-report-button").textContent = value && action === "email" ? "Envoi en cours…" : report?.email_sent_at ? "E-mail demandé" : "Recevoir par e-mail";
    $("csv-dropzone").setAttribute("aria-disabled", String(value));
    $("csv-form").setAttribute("aria-busy", String(value && action === "analysis"));
    $("auth-form").setAttribute("aria-busy", String(value && action === "account"));
    document.querySelectorAll('a[href^="#"]').forEach(link => {
      if (value) link.setAttribute("aria-disabled", "true");
      else link.removeAttribute("aria-disabled");
    });
    if (!value && pendingRoute) {
      pendingRoute = false;
      queueMicrotask(route);
    }
  }

  async function run(action, task, errorTarget) {
    if (busy) return;
    $("global-error").hidden = true;
    setBusy(true, action);
    try { await task(); }
    catch (error) {
      const target = !user ? "account-status" : errorTarget;
      status(target, error.message, true);
      if (target === "global-error") $(target).hidden = false;
    } finally { setBusy(false); }
  }

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const response = await fetch(path, {
        ...options, signal: controller.signal, credentials: "same-origin",
        headers: {"X-CSRF-Protection": "1", ...options.headers}
      });
      let data = null;
      if (response.status !== 204) {
        try { data = await response.json(); }
        catch (error) { if (controller.signal.aborted) throw error; }
      }
      if (!response.ok) {
        if (response.status === 401 && path !== "/auth/login") setUser(null);
        const message = path.startsWith("/analyses?") ? apiError(response.status, data?.detail)
          : typeof data?.detail === "string" ? data.detail
          : response.status >= 500 ? "Le serveur est indisponible. Réessayez dans quelques instants."
          : "Vérifiez votre adresse e-mail et votre mot de passe (12 à 128 caractères).";
        const error = new Error(response.status === 401 && path !== "/auth/login" ? "Connectez-vous pour continuer." : message);
        error.status = response.status;
        throw error;
      }
      if (response.status !== 204 && !data) throw new Error("La réponse du serveur est illisible. Vérifiez votre historique avant de réessayer.");
      return data;
    } catch (error) {
      if (controller.signal.aborted) throw new Error("Le serveur met trop de temps à répondre. Vérifiez le résultat avant de réessayer.");
      if (error instanceof TypeError) throw new Error("Connexion interrompue. Vérifiez le résultat avant de réessayer.");
      throw error;
    } finally { clearTimeout(timer); }
  }

  function clearFileError() {
    $("form-error").hidden = true;
    $("csv-file").removeAttribute("aria-invalid");
    $("csv-dropzone").classList.remove("is-invalid");
    $("file-status").classList.remove("is-error");
  }

  function resetFile() {
    $("csv-form").reset();
    selectedFile = null;
    clearFileError();
    $("csv-dropzone").classList.remove("is-selected", "is-dragover");
    $("file-title").textContent = "Déposez votre fichier CSV";
    $("file-picker-label").textContent = "Choisir un fichier";
    status("file-status", "Aucun fichier sélectionné.");
    status("request-status");
    $("reset-button").hidden = true;
  }

  function chooseFile(file) {
    if (busy || !user || !file) return;
    clearFileError();
    selectedFile = null;
    let message = "";
    if (!file.name.toLowerCase().endsWith(".csv")) message = "Choisissez un fichier avec l’extension .csv.";
    else if (file.name.trim().length > 255) message = "Le nom du fichier dépasse 255 caractères.";
    else if (!file.size) message = "Ce fichier est vide.";
    else if (file.size > MAX_FILE_SIZE) message = "Le fichier dépasse la limite de 1 Mio.";
    $("csv-file").value = "";
    $("file-title").textContent = file.name;
    $("file-picker-label").textContent = "Changer de fichier";
    $("reset-button").hidden = false;
    $("csv-dropzone").classList.toggle("is-selected", !message);
    if (message) {
      $("csv-file").setAttribute("aria-invalid", "true");
      $("csv-dropzone").classList.add("is-invalid");
      status("file-status", message, true);
    } else {
      selectedFile = file;
      status("file-status", `${numberFormat.format(Math.max(1, Math.ceil(file.size / 1024)))} Kio · Prêt à analyser`);
    }
    status("request-status");
    setBusy(false);
  }

  function setUser(value) {
    user = value;
    if (!user) setAuthMode("login");
    report = null;
    resetFile();
    $("history-body").replaceChildren();
    $("findings-body").replaceChildren();
    $("history-table-region").hidden = true;
    $("history-empty").hidden = true;
    $("account-email").textContent = user?.email || "";
    $("auth-password").value = "";
    $("auth-form").hidden = Boolean(user);
    $("auth-switch-row").hidden = Boolean(user);
    status("account-status");
    status("history-status");
    status("email-status");
    showView(user ? "analysis" : "auth", false);
  }
  function apiError(status, detail) {
    const messages = {
      "Upload a CSV file.": "Choisissez un fichier avec l’extension .csv.",
      "Filename is too long.": "Le nom du fichier doit contenir au maximum 255 caractères.",
      "Maximum file size is 1 MiB.": "Le fichier dépasse la limite de 1 Mio.",
      "CSV contains null bytes.": "Le fichier contient des caractères non valides. Réexportez-le au format CSV UTF-8.",
      "The CSV file must use UTF-8 encoding.": "Réexportez le fichier avec l’encodage UTF-8, puis réessayez.",
      "A header is required for every column.": "La première ligne doit contenir un nom pour chaque colonne.",
      "Column headers must be unique.": "Chaque colonne doit avoir un nom différent dans la première ligne.",
      "Use a comma or semicolon delimiter.": "Choisissez une virgule ou un point-virgule comme séparateur.",
      "unexpected end of data": "Le CSV contient un champ entre guillemets qui n’est pas fermé. Vérifiez son format."
    };
    if (typeof detail === "string") {
      if (messages[detail]) return messages[detail];
      const match = detail.match(/^Row (\d+) has an unexpected number of columns\.$/);
      if (match) return `La ligne ${match[1]} ne contient pas le nombre de colonnes attendu. Vérifiez le séparateur et le fichier.`;
    }
    if (status === 413) return "Le fichier dépasse la taille autorisée. La limite est de 1 Mio.";
    if (status === 422) return "L’envoi n’a pas pu être validé. Vérifiez le fichier et le séparateur, puis réessayez.";
    if (status >= 500) return "Le serveur n’a pas pu confirmer l’analyse. Réessayez dans quelques instants.";
    return "Le CSV n’a pas pu être analysé. Vérifiez ses en-têtes, son séparateur et son encodage UTF-8.";
  }

  function isValidReport(report) {
    if (!report || !Number.isSafeInteger(report.id) || report.id < 1) return false;
    if (typeof report.filename !== "string" || typeof report.created_at !== "string" || !Number.isFinite(Date.parse(report.created_at))) return false;
    if (![report.row_count, report.duplicate_count, report.empty_cell_count].every(n => Number.isSafeInteger(n) && n >= 0)) return false;
    return Array.isArray(report.anomalies) && report.anomalies.every(item =>
      item && typeof item.type === "string" && Number.isSafeInteger(item.row) && item.row > 0
      && (item.column === undefined || item.column === null || typeof item.column === "string")
    );
  }

  function renderReport(value) {
    report = value;
    $("report-filename").textContent = report.filename;
    const date = new Date(report.created_at);
    $("report-date").dateTime = date.toISOString();
    $("report-date").textContent = dateFormat.format(date);
    $("saved-label").textContent = "Enregistré dans votre historique";
    for (const key of ["row", "duplicate", "empty-cell"]) {
      $(key + "-count").textContent = numberFormat.format(report[key.replaceAll("-", "_") + "_count"]);
    }
    const total = report.anomalies.length;
    const headerOnly = report.row_count === 0;
    $("result-message").className = `cc-alert cc-result-message cc-alert--${headerOnly ? "info" : total ? "warning" : "success"}`;
    $("result-message-text").textContent = headerOnly ? "Ce fichier contient seulement les en-têtes. Aucune ligne de données à analyser."
      : total ? "Ces points sont à vérifier selon votre contexte. Une cellule vide n’est pas forcément une erreur."
      : "Aucun doublon ni cellule vide détecté.";
    $("findings-details").hidden = total === 0;
    $("findings-details").open = false;
    $("findings-label").textContent = numberFormat.format(total);
    const rows = document.createDocumentFragment();
    for (const item of report.anomalies.slice(0, MAX_VISIBLE_FINDINGS)) {
      const row = document.createElement("tr");
      const duplicate = item.type === "duplicate_row";
      const values = [numberFormat.format(item.row), duplicate ? "Doublon" : "Cellule vide", item.column || "—", duplicate ? "Ligne identique déjà présente" : "Valeur absente ou composée d’espaces"];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      rows.append(row);
    }
    $("findings-body").replaceChildren(rows);
    $("findings-limit").hidden = total <= MAX_VISIBLE_FINDINGS;
    $("findings-limit").textContent = `Les ${MAX_VISIBLE_FINDINGS} premiers points sur ${numberFormat.format(total)} sont affichés.`;
    $("email-recipient").textContent = user.email;
    status("email-status", report.email_sent_at ? "Fichier transmis au service d’e-mail. Vérifiez aussi vos indésirables."
      : report.correction_available ? "" : "Réimportez ce fichier pour recevoir une version corrigée.");
    showView("report");
  }

  async function loadHistory() {
    status("history-status", "Chargement…");
    const reports = await api("/analyses");
    if (!Array.isArray(reports)) throw new Error("L’historique est illisible. Réessayez.");
    const rows = document.createDocumentFragment();
    for (const item of reports) {
      if (!Number.isSafeInteger(item.id) || typeof item.filename !== "string" || !Number.isFinite(Date.parse(item.created_at))) throw new Error("L’historique est illisible. Réessayez.");
      const row = document.createElement("tr");
      const file = document.createElement("td");
      const name = document.createElement("span");
      name.className = "cc-history-file";
      name.textContent = item.filename;
      const meta = document.createElement("span");
      meta.className = "cc-history-meta";
      meta.textContent = `${numberFormat.format(item.row_count)} ligne${item.row_count > 1 ? "s" : ""} analysée${item.row_count > 1 ? "s" : ""}`;
      file.append(name, meta);
      const date = document.createElement("td");
      date.textContent = dateFormat.format(new Date(item.created_at));
      const result = document.createElement("td");
      const badge = document.createElement("span");
      const count = item.duplicate_count + item.empty_cell_count;
      badge.className = `cc-badge cc-badge--${count ? "warning" : "neutral"}`;
      badge.textContent = count ? `${numberFormat.format(count)} point${count > 1 ? "s" : ""} à vérifier` : item.row_count ? "Aucun point détecté" : "Aucune donnée";
      result.append(badge);
      const action = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "cc-btn cc-btn--quiet";
      button.textContent = "Ouvrir";
      button.setAttribute("aria-label", `Ouvrir le rapport de ${item.filename}`);
      button.disabled = busy;
      button.addEventListener("click", () => navigate(`#report/${item.id}`));
      action.append(button);
      row.append(file, date, result, action);
      rows.append(row);
    }
    $("history-body").replaceChildren(rows);
    $("history-table-region").hidden = !reports.length;
    $("history-empty").hidden = Boolean(reports.length);
    status("history-status", reports.length ? `${reports.length} analyse${reports.length > 1 ? "s" : ""}` : "");
  }

  function navigate(hash) {
    if (busy) return;
    if (window.location.hash === hash) route();
    else window.location.hash = hash;
  }

  function route() {
    if (!ready) return;
    if (busy) { pendingRoute = true; return; }
    if (!user) { showView("auth"); return; }
    const hash = window.location.hash;
    if (hash === "#history") {
      showView("history");
      run("history", loadHistory, "history-status");
      return;
    }
    const match = hash.match(/^#report\/(\d+)$/);
    if (match && Number.isSafeInteger(Number(match[1])) && Number(match[1]) > 0) {
      const id = Number(match[1]);
      if (report?.id === id) { renderReport(report); setBusy(false); return; }
      showView("history");
      status("history-status", "Ouverture du rapport…");
      run("history", async () => {
        try {
          const result = await api(`/analyses/${id}`);
          if (!isValidReport(result)) throw new Error("Le rapport reçu est illisible.");
          renderReport(result);
        } catch (error) {
          // Un rapport indisponible mène à un écran avec des actions de navigation.
          if (!pendingRoute) window.history.replaceState(null, "", "#history");
          throw error;
        }
      }, "history-status");
      return;
    }
    if (hash !== "#analysis") window.history.replaceState(null, "", "#analysis");
    showView("analysis");
  }

  window.addEventListener("hashchange", route);
  document.addEventListener("click", event => {
    const link = event.target.closest('a[href^="#"]');
    if (link?.classList.contains("cc-skip")) {
      event.preventDefault();
      $("main").focus();
      return;
    }
    if (busy && link && !link.classList.contains("cc-skip")) event.preventDefault();
    if (!event.target.closest("#account-menu")) $("account-menu").open = false;
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && $("account-menu").open) {
      $("account-menu").open = false;
      $("account-menu").querySelector("summary").focus();
    }
  });

  function setAuthMode(mode) {
    authMode = mode;
    const registration = mode === "register";
    $("account-heading").textContent = registration ? "Créer un compte" : "Connexion";
    $("auth-description").textContent = registration ? "Un compte pour garder vos rapports privés." : "Retrouvez vos analyses dans votre espace privé.";
    $("auth-switch-label").textContent = registration ? "Déjà un compte ?" : "Pas encore de compte ?";
    $("auth-switch").textContent = registration ? "Se connecter" : "Créer un compte";
    $("auth-password").autocomplete = registration ? "new-password" : "current-password";
    $("password-help").hidden = !registration;
  }

  $("auth-switch").addEventListener("click", () => {
    if (busy) return;
    setAuthMode(authMode === "login" ? "register" : "login");
    status("account-status");
    setBusy(false);
    $("auth-email").focus();
  });

  $("auth-form").addEventListener("submit", event => {
    event.preventDefault();
    run("account", async () => {
      status("account-status");
      const identity = await api(`/auth/${authMode}`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email: $("auth-email").value.trim(), password: $("auth-password").value})
      });
      setUser(identity);
      pendingRoute = true;
    }, "account-status");
  });

  $("logout-button").addEventListener("click", () => run("account", async () => {
    await api("/auth/logout", {method: "POST"});
    setUser(null);
    window.history.replaceState(null, "", "#analysis");
    status("account-status", "Vous êtes déconnecté.");
    showView("auth");
  }, "global-error"));

  $("csv-file").addEventListener("change", () => chooseFile($("csv-file").files[0]));
  $("csv-delimiter").addEventListener("change", () => { clearFileError(); status("request-status"); });
  $("reset-button").addEventListener("click", () => {
    if (busy) return;
    resetFile(); setBusy(false); $("csv-file").focus();
  });
  $("new-analysis-button").addEventListener("click", () => {
    if (busy) return;
    resetFile(); setBusy(false); navigate("#analysis");
  });
  for (const name of ["dragenter", "dragover"]) $("csv-dropzone").addEventListener(name, event => {
    event.preventDefault();
    if (!busy) $("csv-dropzone").classList.add("is-dragover");
  });
  $("csv-dropzone").addEventListener("dragleave", () => $("csv-dropzone").classList.remove("is-dragover"));
  $("csv-dropzone").addEventListener("drop", event => {
    event.preventDefault();
    $("csv-dropzone").classList.remove("is-dragover");
    if (busy) return;
    const files = event.dataTransfer?.files;
    if (files?.length === 1) chooseFile(files[0]);
    else if (files?.length > 1) {
      resetFile(); status("file-status", "Déposez un seul fichier à la fois.", true); setBusy(false);
    }
  });

  $("csv-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!user || !selectedFile) return;
    run("analysis", async () => {
      clearFileError();
      status("request-status", "Analyse en cours. Vous retrouverez le résultat dans votre historique.");
      const data = new FormData();
      data.append("file", selectedFile, selectedFile.name);
      try {
        const result = await api(`/analyses?delimiter=${encodeURIComponent($("csv-delimiter").value)}`, {method: "POST", body: data});
        if (!isValidReport(result)) throw new Error("Le résultat est illisible. Consultez votre historique avant de réessayer.");
        renderReport(result);
        status("request-status");
        if (!pendingRoute) window.history.pushState(null, "", `#report/${result.id}`);
      } catch (error) {
        status("request-status");
        if (user) {
          $("error-message").textContent = error.message;
          $("form-error").hidden = false;
        } else throw error;
      }
    }, "request-status");
  });

  $("refresh-history").addEventListener("click", () => run("history", loadHistory, "history-status"));
  $("email-report-button").addEventListener("click", () => {
    if (!user || !report || report.email_sent_at || !report.correction_available) return;
    run("email", async () => {
      status("email-status", "Envoi du fichier…");
      const result = await api(`/analyses/${report.id}/email`, {method: "POST"});
      report.email_sent_at = result.email_sent_at;
      status("email-status", result.message);
    }, "email-status");
  });

  run("account", async () => {
    try { setUser(await api("/auth/me")); }
    catch (error) {
      setUser(null);
      if (error.status !== 401) status("account-status", error.message, true);
    }
    ready = true;
    pendingRoute = true;
  }, "account-status");
})();
