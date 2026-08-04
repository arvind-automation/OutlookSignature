(function () {
  "use strict";

  var BASE_FORM = {
    company: "arvind-limited",
    firstName: "FirstName",
    lastName: "LastName",
    email: "name@arvind.in",
    designation: "Designation",
    phone: "+91 XXXXX XXXXX",
    organization: "Arvind Limited",
    website: "www.arvind.com",
    address: "",
    managerFirstName: "",
    managerLastName: "",
    managerDesignation: "",
    managerEmail: "",
    managerPhone: "",
    manager2FirstName: "",
    manager2LastName: "",
    manager2Designation: "",
    manager2Email: "",
    manager2Phone: "",
  };

  var MANAGER_DEFAULTS = {
    managerFirstName: "ManagerFirstName",
    managerLastName: "ManagerLastName",
    managerDesignation: "Designation",
    managerEmail: "manager@arvind.in",
    managerPhone: "+91 XXXXX XXXXX",
  };

  var cache = {};
  var showTimer = null;
  var hideTimer = null;
  var activeTeam = null;
  var activeCard = null;
  var requestId = 0;

  var popup = document.getElementById("team-preview-popup");
  var previewHtml = document.getElementById("team-preview-html");
  var cards = document.querySelectorAll(".team-card[data-team]");

  if (!popup || !previewHtml || !cards.length) return;

  function formForTeam(team) {
    var form = Object.assign({}, BASE_FORM);
    if (team === "sales") {
      Object.assign(form, MANAGER_DEFAULTS);
    }
    return form;
  }

  function clearPreviewing() {
    cards.forEach(function (card) {
      card.classList.remove("is-previewing");
    });
  }

  function positionPopup(card) {
    if (!card) return;
    var rect = card.getBoundingClientRect();
    var popupWidth = popup.offsetWidth || Math.min(460, window.innerWidth - 32);
    var popupHeight = popup.offsetHeight || 280;
    var gap = 12;

    var left = rect.left + rect.width / 2 - popupWidth / 2;
    left = Math.max(16, Math.min(left, window.innerWidth - popupWidth - 16));

    var top = rect.bottom + gap;
    if (top + popupHeight > window.innerHeight - 16) {
      top = rect.top - popupHeight - gap;
    }
    if (top < 16) {
      top = Math.max(16, (window.innerHeight - popupHeight) / 2);
    }

    popup.style.left = left + "px";
    popup.style.top = top + "px";
  }

  function showPopup(card) {
    popup.hidden = false;
    popup.setAttribute("aria-hidden", "false");
    clearPreviewing();
    if (card) card.classList.add("is-previewing");
    // Position after visible so offsetWidth/Height are accurate.
    requestAnimationFrame(function () {
      positionPopup(card);
    });
  }

  function hidePopup() {
    popup.hidden = true;
    popup.setAttribute("aria-hidden", "true");
    clearPreviewing();
    activeTeam = null;
    activeCard = null;
  }

  function setLoading() {
    previewHtml.innerHTML =
      '<p style="margin:0;padding:24px;text-align:center;color:#6b6560;font-family:Arial,Helvetica,sans-serif;font-size:14px;">Loading preview…</p>';
  }

  function fetchPreview(team, card) {
    if (cache[team]) {
      previewHtml.innerHTML = cache[team];
      showPopup(card);
      return;
    }

    var id = ++requestId;
    setLoading();
    showPopup(card);

    fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        templateId: "standard",
        team: team,
        form: formForTeam(team),
      }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("preview failed");
        return res.json();
      })
      .then(function (data) {
        if (id !== requestId || activeTeam !== team) return;
        var html = data.html || "";
        cache[team] = html;
        previewHtml.innerHTML = html;
        positionPopup(card);
      })
      .catch(function () {
        if (id !== requestId || activeTeam !== team) return;
        previewHtml.innerHTML =
          '<p style="margin:0;padding:24px;text-align:center;color:#c0392b;font-family:Arial,Helvetica,sans-serif;font-size:14px;">Could not load preview.</p>';
        positionPopup(card);
      });
  }

  function scheduleShow(team, card) {
    window.clearTimeout(hideTimer);
    window.clearTimeout(showTimer);
    activeTeam = team;
    activeCard = card;
    showTimer = window.setTimeout(function () {
      fetchPreview(team, card);
    }, 120);
  }

  function scheduleHide() {
    window.clearTimeout(showTimer);
    hideTimer = window.setTimeout(function () {
      hidePopup();
    }, 100);
  }

  cards.forEach(function (card) {
    var team = card.getAttribute("data-team");
    if (!team) return;

    card.addEventListener("mouseenter", function () {
      scheduleShow(team, card);
    });
    card.addEventListener("mouseleave", function () {
      scheduleHide();
    });
    card.addEventListener("focus", function () {
      scheduleShow(team, card);
    });
    card.addEventListener("blur", function () {
      scheduleHide();
    });
  });

  window.addEventListener("scroll", function () {
    if (!popup.hidden && activeCard) positionPopup(activeCard);
  }, { passive: true });

  window.addEventListener("resize", function () {
    if (!popup.hidden && activeCard) positionPopup(activeCard);
  });
})();
