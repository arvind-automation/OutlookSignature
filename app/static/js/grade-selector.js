(function () {
  "use strict";

  var form = document.getElementById("grade-form");
  var hiddenInput = document.getElementById("grade");
  var search = document.getElementById("grade-search");
  var toggle = document.getElementById("grade-options-toggle");
  var options = document.getElementById("grade-options");
  var noResults = document.getElementById("grade-no-results");
  var modal = document.getElementById("grade-confirm-modal");
  var message = document.getElementById("grade-confirm-message");
  var confirm = document.getElementById("grade-confirm");
  var cancel = document.getElementById("grade-cancel");
  var referenceModal = document.getElementById("grade-reference-modal");
  var referenceOpen = document.getElementById("grade-reference-open");
  var referenceClose = document.getElementById("grade-reference-close");
  var referenceRows = Array.prototype.slice.call(document.querySelectorAll(".grade-reference-row"));
  var choices = Array.prototype.slice.call(options.querySelectorAll("[data-grade]"));
  var activeIndex = -1;

  function visibleChoices() {
    return choices.filter(function (choice) { return !choice.hidden; });
  }

  function openList() {
    options.hidden = false;
    search.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-expanded", "true");
  }

  function closeList() {
    options.hidden = true;
    search.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-expanded", "false");
    activeIndex = -1;
    search.removeAttribute("aria-activedescendant");
    choices.forEach(function (choice) { choice.classList.remove("is-active"); });
  }

  function filterChoices() {
    var query = search.value.trim().toUpperCase();
    var matches = 0;
    choices.forEach(function (choice) {
      var match = !query || choice.dataset.label.toUpperCase().indexOf(query) !== -1;
      choice.hidden = !match;
      if (match) matches += 1;
    });
    noResults.hidden = matches !== 0;
    activeIndex = -1;
  }

  function showAllChoices() {
    search.value = "";
    filterChoices();
    openList();
  }

  function selectChoice(choice) {
    hiddenInput.value = choice.dataset.grade;
    search.value = choice.dataset.label;
    choices.forEach(function (item) { item.setAttribute("aria-selected", item === choice ? "true" : "false"); });
    closeList();
  }

  function selectGrade(grade, label) {
    hiddenInput.value = grade;
    search.value = label;
    choices.forEach(function (item) {
      item.setAttribute("aria-selected", item.dataset.grade === grade ? "true" : "false");
    });
    closeList();
  }

  function focusChoice(index) {
    var visible = visibleChoices();
    if (!visible.length) return;
    activeIndex = (index + visible.length) % visible.length;
    choices.forEach(function (choice) { choice.classList.remove("is-active"); });
    var active = visible[activeIndex];
    active.classList.add("is-active");
    search.setAttribute("aria-activedescendant", active.id);
    active.scrollIntoView({ block: "nearest" });
  }

  // The dropdown is primary: reopening it always starts with every grade.
  search.addEventListener("focus", showAllChoices);
  search.addEventListener("input", function () { hiddenInput.value = ""; filterChoices(); openList(); });
  search.addEventListener("keydown", function (event) {
    if (event.key === "ArrowDown") { event.preventDefault(); openList(); focusChoice(activeIndex + 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); openList(); focusChoice(activeIndex - 1); }
    else if (event.key === "Enter" && !options.hidden && activeIndex >= 0) { event.preventDefault(); selectChoice(visibleChoices()[activeIndex]); }
    else if (event.key === "Escape") { closeList(); }
  });
  toggle.addEventListener("mousedown", function (event) { event.preventDefault(); });
  toggle.addEventListener("click", function () {
    if (options.hidden) {
      showAllChoices();
      search.focus();
    } else {
      closeList();
    }
  });
  choices.forEach(function (choice) {
    choice.addEventListener("mousedown", function (event) { event.preventDefault(); selectChoice(choice); });
  });
  document.addEventListener("mousedown", function (event) { if (!event.target.closest(".grade-picker")) closeList(); });

  referenceOpen.addEventListener("click", function () { referenceModal.hidden = false; referenceClose.focus(); });
  referenceClose.addEventListener("click", function () { referenceModal.hidden = true; referenceOpen.focus(); });
  referenceRows.forEach(function (row) {
    function chooseReferenceGrade() {
      selectGrade(row.dataset.grade, row.dataset.label);
      referenceModal.hidden = true;
    }
    row.addEventListener("click", chooseReferenceGrade);
    row.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); chooseReferenceGrade(); }
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !referenceModal.hidden) { referenceModal.hidden = true; referenceOpen.focus(); }
  });

  cancel.addEventListener("click", function () { modal.hidden = true; search.focus(); });
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!hiddenInput.value) { search.focus(); openList(); return; }
    message.textContent = "You have selected " + hiddenInput.value + " as your current grade. Please make sure this is your current grade.";
    modal.hidden = false;
    confirm.focus();
  });
  confirm.addEventListener("click", function () { confirm.disabled = true; confirm.textContent = "Saving…"; form.submit(); });
}());
