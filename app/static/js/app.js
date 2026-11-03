/* Real CSV upload, using the existing same-origin POST /analyses API. */
"use strict";

(() => {
  const MAX_FILE_SIZE = 1024 * 1024;
  const MAX_VISIBLE_FINDINGS = 200;
  const REQUEST_TIMEOUT = 90000;
  const form = document.getElementById("csv-form");
  const fileInput = document.getElementById("csv-file");
  const dropzone = document.getElementById("csv-dropzone");
  const fileTitle = document.getElementById("file-title");
  const fileStatus = document.getElementById("file-status");
  const pickerLabel = document.getElementById("file-picker-label");
  const delimiter = document.getElementById("csv-delimiter");
  const submitButton = document.getElementById("analyze-button");
  const submitLabel = document.getElementById("analyze-label");
  const spinner = document.getElementById("analyze-spinner");
  const arrow = document.getElementById("analyze-arrow");
  const resetButton = document.getElementById("reset-button");
  const errorBox = document.getElementById("form-error");
  const requestStatus = document.getElementById("request-status");
  const results = document.getElementById("analysis-results");
  const numberFormat = new Intl.NumberFormat("fr-CH");
  const dateFormat = new Intl.DateTimeFormat("fr-CH", {dateStyle: "medium", timeStyle: "short"});
  let selectedFile = null;
  let busy = false;

  function clearError() {
    errorBox.hidden = true;
    fileInput.removeAttribute("aria-invalid");
    dropzone.classList.remove("is-invalid");
    fileStatus.classList.remove("is-error");
  }

  function showError(message, title = "L’analyse ne peut pas démarrer.") {
    document.getElementById("error-title").textContent = title;
    document.getElementById("error-message").textContent = message;
    errorBox.hidden = false;
  }

  function setBusy(value) {
    busy = value;
    form.setAttribute("aria-busy", String(value));
    dropzone.setAttribute("aria-disabled", String(value));
    fileInput.disabled = value;
    delimiter.disabled = value;
    submitButton.disabled = value || !selectedFile;
    resetButton.disabled = value || (!selectedFile && errorBox.hidden);
    spinner.hidden = !value;
    arrow.hidden = value;
    submitLabel.textContent = value ? "Analyse en cours…" : "Analyser le CSV";
    if (value) submitButton.setAttribute("aria-busy", "true");
    else submitButton.removeAttribute("aria-busy");
  }

  function chooseFile(file) {
    if (busy || !file) return;
    clearError();
    results.hidden = true;
    selectedFile = null;
    let message = "";
    if (!file.name.toLowerCase().endsWith(".csv")) message = "Choisissez un fichier avec l’extension .csv.";
    else if (file.name.trim().length > 255) message = "Le nom du fichier doit contenir au maximum 255 caractères.";
    else if (file.size === 0) message = "Le fichier est vide. Choisissez un CSV contenant au moins une ligne d’en-tête.";
    else if (file.size > MAX_FILE_SIZE) message = "Le fichier dépasse la limite de 1 Mio. Choisissez un fichier plus petit.";

    fileInput.value = "";
    fileTitle.textContent = file.name;
    pickerLabel.textContent = "Changer de fichier";
    if (message) {
      fileInput.setAttribute("aria-invalid", "true");
      dropzone.classList.add("is-invalid");
      fileStatus.classList.add("is-error");
      fileStatus.textContent = message;
      showError(message);
    } else {
      selectedFile = file;
      const size = numberFormat.format(Math.max(1, Math.ceil(file.size / 1024)));
      fileStatus.textContent = `${size} Kio · Prêt à analyser`;
    }
    requestStatus.textContent = "Les résultats seront enregistrés après l’analyse.";
    setBusy(false);
  }

  function resetForm() {
    if (busy) return;
    form.reset();
    selectedFile = null;
    clearError();
    results.hidden = true;
    dropzone.classList.remove("is-dragover");
    fileTitle.textContent = "Glissez votre CSV ici";
    pickerLabel.textContent = "Choisir un fichier";
    fileStatus.textContent = "Aucun fichier sélectionné.";
    requestStatus.textContent = "Les résultats seront enregistrés après l’analyse.";
    setBusy(false);
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

  function renderReport(report) {
    document.getElementById("row-count").textContent = numberFormat.format(report.row_count);
    document.getElementById("duplicate-count").textContent = numberFormat.format(report.duplicate_count);
    document.getElementById("empty-cell-count").textContent = numberFormat.format(report.empty_cell_count);
    document.getElementById("report-filename").textContent = report.filename;
    document.getElementById("saved-label").textContent = `✓ Rapport #${report.id} enregistré`;
    const date = new Date(report.created_at);
    const dateElement = document.getElementById("report-date");
    dateElement.dateTime = date.toISOString();
    dateElement.textContent = dateFormat.format(date);

    const total = report.anomalies.length;
    const headerOnly = report.row_count === 0;
    const findingsLabel = document.getElementById("findings-label");
    findingsLabel.className = `cc-badge cc-badge--${headerOnly ? "neutral" : total ? "warning" : "success"}`;
    findingsLabel.textContent = headerOnly ? "Aucune ligne de données" : total ? `${numberFormat.format(total)} point${total > 1 ? "s" : ""} à vérifier` : "Aucun point détecté";
    const message = document.getElementById("result-message");
    message.className = `cc-alert cc-result-message cc-alert--${headerOnly ? "info" : total ? "warning" : "success"}`;
    document.getElementById("result-message-text").textContent = headerOnly
      ? "Le fichier contient uniquement ses en-têtes et éventuellement des lignes vierges. Ajoutez des données pour les analyser."
      : total ? "Des points à vérifier ont été repérés. Leur contexte vous permettra de décider s’ils nécessitent une correction."
      : "Aucun doublon ni cellule vide n’a été détecté par ces deux contrôles.";

    const body = document.getElementById("findings-body");
    const rows = document.createDocumentFragment();
    for (const item of report.anomalies.slice(0, MAX_VISIBLE_FINDINGS)) {
      const row = document.createElement("tr");
      const line = document.createElement("td");
      line.className = "cc-number";
      line.textContent = numberFormat.format(item.row);
      const type = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "cc-badge cc-badge--warning";
      badge.textContent = item.type === "empty_cell" ? "Cellule vide" : item.type === "duplicate_row" ? "Doublon" : "Point à vérifier";
      type.append(badge);
      const column = document.createElement("td");
      const code = document.createElement("code");
      code.textContent = item.column || "—";
      column.append(code);
      const detail = document.createElement("td");
      detail.textContent = item.type === "empty_cell" ? "Valeur absente ou composée d’espaces" : item.type === "duplicate_row" ? "Ligne identique déjà présente dans le fichier" : "Vérifiez cette ligne dans le fichier";
      row.append(line, type, column, detail);
      rows.append(row);
    }
    body.replaceChildren(rows);
    document.getElementById("findings-table-region").hidden = total === 0;
    const empty = document.getElementById("no-findings");
    empty.hidden = total !== 0;
    empty.classList.toggle("is-header-only", headerOnly);
    document.getElementById("no-findings-title").textContent = headerOnly ? "Aucune ligne de données à analyser" : "Aucun point à vérifier détecté";
    document.getElementById("no-findings-text").textContent = headerOnly ? "Choisissez un fichier contenant des données sous la ligne d’en-tête." : "Aucun doublon ni cellule vide n’a été trouvé lors de ces deux contrôles.";
    const limit = document.getElementById("findings-limit");
    limit.hidden = total <= MAX_VISIBLE_FINDINGS;
    limit.textContent = total > MAX_VISIBLE_FINDINGS ? `Les ${MAX_VISIBLE_FINDINGS} premiers points sur ${numberFormat.format(total)} sont affichés. Le rapport complet a été enregistré.` : "";
    results.hidden = false;
    requestStatus.textContent = `Analyse terminée. Rapport #${report.id} enregistré.`;
    results.focus({preventScroll: true});
    results.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    if (!selectedFile) {
      showError("Choisissez un fichier CSV avant de lancer l’analyse.");
      setBusy(false);
      return;
    }
    clearError();
    results.hidden = true;
    setBusy(true);
    requestStatus.textContent = "Le fichier est en cours d’analyse. Patientez quelques instants.";
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    try {
      const data = new FormData();
      data.append("file", selectedFile, selectedFile.name);
      const response = await fetch(`/analyses?delimiter=${encodeURIComponent(delimiter.value)}`, {
        method: "POST", body: data, signal: controller.signal
      });
      let payload = null;
      try { payload = await response.json(); }
      catch (error) { if (controller.signal.aborted) throw error; }
      if (!response.ok) throw new Error(apiError(response.status, payload?.detail));
      if (!isValidReport(payload)) throw new Error("Le serveur a répondu, mais le rapport n’a pas pu être affiché. Il a peut-être été enregistré.");
      renderReport(payload);
    } catch (error) {
      let message = error.message;
      if (controller.signal.aborted) message = "Le serveur a mis trop de temps à répondre. Le rapport a peut-être été enregistré. Vérifiez la connexion avant de réessayer.";
      else if (error instanceof TypeError) message = "La réponse du serveur a été interrompue. Vérifiez votre connexion puis réessayez.";
      showError(message, "L’analyse n’a pas pu être confirmée.");
      requestStatus.textContent = "Une erreur est survenue. Consultez le message au-dessus du bouton.";
    } finally {
      clearTimeout(timer);
      setBusy(false);
    }
  });

  fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));
  delimiter.addEventListener("change", () => {
    if (!selectedFile) return;
    clearError();
    results.hidden = true;
    requestStatus.textContent = "Les résultats seront enregistrés après l’analyse.";
    setBusy(false);
  });
  resetButton.addEventListener("click", resetForm);
  document.getElementById("new-analysis-button").addEventListener("click", () => {
    resetForm();
    fileInput.focus();
    dropzone.scrollIntoView({block: "center", behavior: "auto"});
  });
  for (const name of ["dragenter", "dragover"]) {
    dropzone.addEventListener(name, event => {
      event.preventDefault();
      if (!busy) dropzone.classList.add("is-dragover");
    });
  }
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("is-dragover"));
  dropzone.addEventListener("drop", event => {
    event.preventDefault();
    dropzone.classList.remove("is-dragover");
    if (busy) return;
    const files = event.dataTransfer?.files;
    if (files?.length === 1) chooseFile(files[0]);
    else if (files?.length > 1) {
      resetForm();
      showError("Déposez un seul fichier CSV à la fois.");
      setBusy(false);
    }
  });
})();
