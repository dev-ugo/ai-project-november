/* Local interactions for the component reference. No API requests. */
"use strict";

const fileInput = document.getElementById("demo-file");
const dropzone = document.getElementById("demo-dropzone");
const uploadTitle = document.getElementById("upload-title");
const uploadStatus = document.getElementById("upload-status");
const filenameInput = document.getElementById("demo-filename");
const analyzeButton = document.getElementById("demo-analyze");
const resetButton = document.getElementById("demo-reset");
const actionStatus = document.getElementById("demo-action-status");
const initialButton = analyzeButton.innerHTML;
let loadingTimer;

function resetUpload() {
  fileInput.value = "";
  fileInput.removeAttribute("aria-invalid");
  dropzone.classList.remove("is-invalid", "is-dragover");
  uploadStatus.classList.remove("is-error");
  uploadTitle.textContent = "Déposez votre fichier CSV ici";
  filenameInput.value = "contacts.csv";
  uploadStatus.textContent = "Démonstration locale : aucun fichier n’est envoyé.";
}

function showFile(file) {
  if (!file) return;
  const message = !file.name.toLowerCase().endsWith(".csv")
    ? "Choisissez un fichier avec l’extension .csv."
    : file.size > 1024 * 1024 ? "Le fichier dépasse la limite de 1 Mio." : "";
  fileInput.setAttribute("aria-invalid", String(Boolean(message)));
  dropzone.classList.toggle("is-invalid", Boolean(message));
  uploadStatus.classList.toggle("is-error", Boolean(message));
  uploadTitle.textContent = file.name;
  filenameInput.value = file.name;
  uploadStatus.textContent = message || "Fichier sélectionné pour la démonstration. Aucun envoi effectué.";
}

fileInput.addEventListener("change", () => showFile(fileInput.files[0]));
for (const name of ["dragenter", "dragover"]) {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragover");
  });
}
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("is-dragover"));
dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragover");
  showFile(event.dataTransfer.files[0]);
});

function finishLoading() {
  clearTimeout(loadingTimer);
  analyzeButton.disabled = false;
  analyzeButton.removeAttribute("aria-busy");
  analyzeButton.innerHTML = initialButton;
}

analyzeButton.addEventListener("click", () => {
  analyzeButton.disabled = true;
  analyzeButton.setAttribute("aria-busy", "true");
  analyzeButton.innerHTML = '<span class="cc-spinner" aria-hidden="true"></span><span>Analyse en cours…</span>';
  actionStatus.textContent = "Démonstration du chargement en cours…";
  loadingTimer = setTimeout(() => {
    finishLoading();
    actionStatus.textContent = "Démonstration terminée. Aucun rapport n’a été créé.";
  }, 1600);
});

resetButton.addEventListener("click", () => {
  finishLoading();
  resetUpload();
  document.getElementById("demo-delimiter").value = ",";
  actionStatus.textContent = "Démonstration réinitialisée.";
});

const navigationLinks = [...document.querySelectorAll(".cc-nav a")];
for (const link of navigationLinks) {
  link.addEventListener("click", () => {
    for (const other of navigationLinks) other.removeAttribute("aria-current");
    link.setAttribute("aria-current", "location");
  });
}
