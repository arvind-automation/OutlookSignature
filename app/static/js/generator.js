(function () {
  "use strict";

  var MANAGER_L1_KEYS = [
    "managerFirstName",
    "managerLastName",
    "managerEmail",
  ];
  var MANAGER_L2_KEYS = [
    "manager2FirstName",
    "manager2LastName",
    "manager2Email",
  ];

  var DEFAULT_FORM = {
    company: "arvind-limited",
    firstName: "",
    lastName: "",
    email: "",
    designation: "",
    phone: "",
    organization: "Arvind Limited",
    website: "www.arvind.com",
    address: "",
    managerFirstName: "",
    managerLastName: "",
    managerEmail: "",
    manager2FirstName: "",
    manager2LastName: "",
    manager2Email: "",
  };

  var PREFILL_KEYS = [
    "firstName",
    "lastName",
    "email",
    "designation",
    "phone",
    "organization",
    "address",
  ].concat(MANAGER_L1_KEYS);

  // Editable: company, address, L2 manager fields. L1 stays locked from SSO.
  var LOCKED_FIELD_KEYS = [
    "firstName",
    "lastName",
    "email",
    "designation",
    "phone",
    "organization",
    "website",
  ].concat(MANAGER_L1_KEYS);

  function bootPrefill() {
    var boot = window.__SIG_BOOT__ || {};
    return boot.prefill && typeof boot.prefill === "object" ? boot.prefill : {};
  }

  function baseFormDefaults() {
    var values = Object.assign({}, DEFAULT_FORM);
    var boot = window.__SIG_BOOT__ || {};
    var prefill = bootPrefill();
    PREFILL_KEYS.forEach(function (key) {
      if (prefill[key]) values[key] = prefill[key];
    });
    if (boot.userEmail) values.email = boot.userEmail;
    // Avoid flashing demo placeholder identity when SSO prefill is available.
    if (prefill.firstName || prefill.lastName || boot.userEmail) {
      if (!prefill.designation) values.designation = "";
      if (!prefill.phone) values.phone = "";
      if (!prefill.organization) values.organization = "";
    }
    if (values.company === DEFAULT_FORM.company && !values.organization) {
      values.organization = DEFAULT_FORM.organization;
    }
    return values;
  }

  function applyPrefillToEmpty(form) {
    var prefill = bootPrefill();
    var merged = Object.assign({}, form || {});
    PREFILL_KEYS.forEach(function (key) {
      var current = (merged[key] || "").trim();
      var incoming = (prefill[key] || "").trim();
      if (!current && incoming) {
        merged[key] = incoming;
      }
    });
    return merged;
  }

  var state = {
    templateId: "standard",
    orgsBySlug: {},
    saveTimer: null,
    team: "",
    managerLevel: 0,
  };

  var fields = {};
  var els = {};

  function getOrgData() {
    var node = document.getElementById("org-data");
    if (!node) return [];
    try {
      return JSON.parse(node.textContent || "[]");
    } catch (e) {
      return [];
    }
  }

  function clearManagerKeys(keys) {
    keys.forEach(function (key) {
      if (fields[key]) fields[key].value = "";
    });
  }

  function hasAnyData(values, keys) {
    values = values || {};
    return keys.some(function (key) {
      return !!(values[key] || "").trim();
    });
  }

  function resolveManagerLevel(formValues) {
    var form = formValues || {};
    var prefill = bootPrefill();
    if (hasAnyData(form, MANAGER_L2_KEYS)) {
      return 2;
    }
    if (hasAnyData(form, MANAGER_L1_KEYS) || hasAnyData(prefill, MANAGER_L1_KEYS)) {
      return 1;
    }
    return 0;
  }

  function applyL2PrefillToEmpty() {
    var prefill = bootPrefill();
    MANAGER_L2_KEYS.forEach(function (key) {
      if (!fields[key]) return;
      var current = (fields[key].value || "").trim();
      var incoming = (prefill[key] || "").trim();
      if (!current && incoming) {
        fields[key].value = incoming;
      }
    });
  }

  function getFormValues() {
    var values = {};
    Object.keys(fields).forEach(function (key) {
      values[key] = fields[key] ? fields[key].value : "";
    });
    if (state.team !== "sales" || state.managerLevel < 1) {
      MANAGER_L1_KEYS.forEach(function (k) {
        values[k] = "";
      });
    }
    if (state.team !== "sales" || state.managerLevel < 2) {
      MANAGER_L2_KEYS.forEach(function (k) {
        values[k] = "";
      });
    }
    return values;
  }

  function setFormValues(values) {
    Object.keys(fields).forEach(function (key) {
      if (fields[key] && values[key] != null) {
        fields[key].value = values[key];
      }
    });
  }

  function lockReadOnlyFields() {
    LOCKED_FIELD_KEYS.forEach(function (key) {
      if (!fields[key]) return;
      fields[key].disabled = true;
      if (key === "website") {
        fields[key].readOnly = true;
      }
    });
    if (fields.company) fields.company.disabled = false;
    if (fields.address) fields.address.disabled = false;
  }

  function syncManagerSection() {
    if (!els.managerSection) return;
    var isSales = state.team === "sales";
    els.managerSection.hidden = !isSales;
    if (!isSales) return;

    if (els.managerLevel1) els.managerLevel1.hidden = state.managerLevel < 1;
    if (els.managerLevel2) els.managerLevel2.hidden = state.managerLevel < 2;

    if (els.addManagerL2Btn) {
      els.addManagerL2Btn.hidden = state.managerLevel >= 2;
    }
  }

  function handleAddManagerL2() {
    state.managerLevel = 2;
    applyL2PrefillToEmpty();
    syncManagerSection();
    lockReadOnlyFields();
    renderPreview();
    scheduleSave();
  }

  function handleRemoveManagerL2() {
    clearManagerKeys(MANAGER_L2_KEYS);
    state.managerLevel = 1;
    syncManagerSection();
    lockReadOnlyFields();
    renderPreview();
    scheduleSave();
  }

  function showStatus(message, isError) {
    els.status.textContent = message;
    els.status.style.color = isError ? "#c0392b" : "#1f8a5b";
    window.clearTimeout(showStatus.timer);
    showStatus.timer = window.setTimeout(function () {
      els.status.textContent = "";
    }, 2800);
  }

  function renderTemplateSelection() {
    var cards = els.templateList.querySelectorAll("[data-template]");
    cards.forEach(function (card) {
      if (card.getAttribute("data-template") === state.templateId) {
        card.classList.add("is-active");
      } else {
        card.classList.remove("is-active");
      }
    });
  }

  function fetchPreview(forEmail) {
    return fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        form: getFormValues(),
        templateId: state.templateId,
        forEmail: !!forEmail,
        assetOrigin: window.location.origin,
        team: state.team,
      }),
    }).then(function (res) {
      if (!res.ok) throw new Error("Preview failed");
      return res.json();
    });
  }

  function renderPreview() {
    renderTemplateSelection();
    return fetchPreview(false)
      .then(function (data) {
        els.preview.innerHTML = data.html || "";
      })
      .catch(function (err) {
        console.error(err);
        showStatus("Could not refresh preview.", true);
      });
  }

  function scheduleSave() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(saveSignature, 500);
  }

  function saveSignature() {
    return fetch("/api/signature", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        form: getFormValues(),
        templateId: state.templateId,
      }),
    }).catch(function (err) {
      console.error(err);
    });
  }

  function loadSignature() {
    return fetch("/api/signature", { credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("Load failed");
        return res.json();
      })
      .then(function (data) {
        // Server demo defaults are non-empty ("Shalom…"); replace with SSO prefill when no saved signature.
        var savedForm = data.form || {};
        var form = data.isDefault
          ? baseFormDefaults()
          : applyPrefillToEmpty(savedForm || baseFormDefaults());
        var defaultOrg = state.orgsBySlug[form.company] || {};
        var hasSavedAddress = !!(savedForm.address || "").trim();
        if (defaultOrg.defaultAddress && (data.isDefault || !hasSavedAddress)) {
          form.address = defaultOrg.defaultAddress;
        }
        setFormValues(form);
        if (form.templateId) state.templateId = form.templateId;
        state.managerLevel = state.team === "sales" ? resolveManagerLevel(form) : 0;
        var boot = window.__SIG_BOOT__ || {};
        if (boot.userEmail && fields.email) {
          fields.email.value = boot.userEmail;
        }
        lockReadOnlyFields();
        syncManagerSection();
        renderTemplateSelection();
        return renderPreview();
      });
  }

  function handleCompanyChange() {
    var slug = fields.company.value;
    var org = state.orgsBySlug[slug];
    if (org) {
      fields.organization.value = org.organization;
      fields.website.value = org.website || "";
      fields.address.value = org.defaultAddress || "";
    }
    lockReadOnlyFields();
    renderPreview();
    scheduleSave();
  }

  function fallbackCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }

  function audit(action, details) {
    fetch("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ action: action, details: details || {} }),
    }).catch(function () {});
  }

  function copyRenderedSelection(signature) {
    var selection = window.getSelection ? window.getSelection() : null;
    if (!selection || !document.createRange) return false;
    var previousRanges = [];
    for (var index = 0; index < selection.rangeCount; index += 1) {
      previousRanges.push(selection.getRangeAt(index).cloneRange());
    }
    var range = document.createRange();
    range.selectNode(signature);
    selection.removeAllRanges();
    selection.addRange(range);
    var copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      selection.removeAllRanges();
      previousRanges.forEach(function (previousRange) {
        selection.addRange(previousRange);
      });
    }
    return copied;
  }

  function writeRichClipboard(signature) {
    if (!signature) {
      return Promise.reject(new Error("Signature preview not found"));
    }
    var html = signature.outerHTML;
    var plainText = (signature.innerText || signature.textContent || "").trim();
    if (!plainText) {
      return Promise.reject(new Error("Signature preview is empty"));
    }
    if (navigator.clipboard && navigator.clipboard.write && window.ClipboardItem) {
      var item = new window.ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([plainText], { type: "text/plain" }),
      });
      return navigator.clipboard.write([item]).then(function () {
        return "clipboard-api";
      });
    }
    if (copyRenderedSelection(signature)) {
      return Promise.resolve("rendered-selection");
    }
    return Promise.reject(new Error("Rich clipboard access is unavailable"));
  }

  function copyRenderedSignature() {
    showStatus("Preparing signature…");
    fetchPreview(true)
      .then(function (data) {
        if (data.needsOrganization) {
          throw new Error("Select an organization first.");
        }
        if (data.copyReady === false) {
          throw new Error(data.copyError || "Signature assets are not ready for rich copy.");
        }
        els.preview.innerHTML = data.html || "";
        var signature = els.preview.firstElementChild;
        return writeRichClipboard(signature).catch(function (clipboardError) {
          if (signature && copyRenderedSelection(signature)) {
            return "rendered-selection";
          }
          throw clipboardError;
        });
      })
      .then(function (copyMethod) {
        showStatus(
          "Signature copied. In Outlook on the web, open Settings → Accounts → Signatures and paste it into the signature editor."
        );
        audit("signature_copied", { method: copyMethod });
      })
      .catch(function (err) {
        console.error(err);
        var message =
          err &&
          (err.message === "Select an organization first." ||
            err.message.indexOf("PUBLIC_ASSET_BASE_URL") !== -1)
            ? err.message
            : "Rich copy was blocked. Select the rendered signature and press Ctrl+C, then paste it into Outlook.";
        showStatus(message, true);
      });
  }

  function copyHtmlCode() {
    fetchPreview(true)
      .then(function (data) {
        if (data.needsOrganization) {
          showStatus("Select an organization first.", true);
          return;
        }
        var html = data.html;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          return navigator.clipboard.writeText(html).then(function () {
            showStatus("HTML code copied to clipboard.");
            audit("html_copied");
          });
        }
        fallbackCopy(html);
        showStatus("HTML code copied to clipboard.");
        audit("html_copied");
      })
      .catch(function (err) {
        console.error(err);
        showStatus("Could not copy HTML code.", true);
      });
  }

  function resetForm() {
    var values = baseFormDefaults();
    values.company = DEFAULT_FORM.company;
    values.organization = DEFAULT_FORM.organization;
    values.website =
      (state.orgsBySlug[DEFAULT_FORM.company] || {}).website || DEFAULT_FORM.website;
    values.address = (state.orgsBySlug[DEFAULT_FORM.company] || {}).defaultAddress || "";
    MANAGER_L2_KEYS.forEach(function (k) {
      values[k] = "";
    });
    if (state.team === "sales") {
      state.managerLevel =
        hasAnyData(values, MANAGER_L1_KEYS) || hasAnyData(bootPrefill(), MANAGER_L1_KEYS) ? 1 : 0;
    } else {
      state.managerLevel = 0;
    }
    if (state.managerLevel < 1) {
      MANAGER_L1_KEYS.forEach(function (k) {
        values[k] = "";
      });
    }
    setFormValues(values);
    state.templateId = "standard";
    lockReadOnlyFields();
    syncManagerSection();
    renderPreview();
    scheduleSave();
    showStatus("Form reset to defaults.");
  }

  function onFormInput() {
    renderPreview();
    scheduleSave();
  }

  function bindEvents() {
    if (fields.address) {
      fields.address.addEventListener("input", onFormInput);
      fields.address.addEventListener("change", onFormInput);
    }
    MANAGER_L2_KEYS.forEach(function (key) {
      if (!fields[key]) return;
      fields[key].addEventListener("input", onFormInput);
      fields[key].addEventListener("change", onFormInput);
    });
    fields.company.addEventListener("change", handleCompanyChange);
    if (els.addManagerL2Btn) {
      els.addManagerL2Btn.addEventListener("click", handleAddManagerL2);
    }
    if (els.removeManagerL2) {
      els.removeManagerL2.addEventListener("click", handleRemoveManagerL2);
    }
    els.form.addEventListener("submit", function (e) {
      e.preventDefault();
    });

    document.getElementById("copy-rendered").addEventListener("click", copyRenderedSignature);
    document.getElementById("copy-html").addEventListener("click", copyHtmlCode);
    document.getElementById("reset-form").addEventListener("click", resetForm);

    els.templateList.addEventListener("click", function (event) {
      var button = event.target.closest("[data-template]");
      if (!button) return;
      state.templateId = button.getAttribute("data-template");
      renderPreview();
      scheduleSave();
    });
  }

  function init() {
    var boot = window.__SIG_BOOT__ || {};
    state.team = (boot.team || "").toLowerCase();

    els = {
      form: document.getElementById("signature-form"),
      preview: document.getElementById("signature-preview"),
      status: document.getElementById("copy-status"),
      templateList: document.getElementById("template-list"),
      previewView: document.getElementById("preview-view"),
      managerSection: document.getElementById("manager-section"),
      managerLevel1: document.getElementById("manager-level1"),
      managerLevel2: document.getElementById("manager-level2"),
      addManagerL2Btn: document.getElementById("add-manager-l2-btn"),
      removeManagerL2: document.getElementById("remove-manager-l2"),
    };

    fields = {
      company: document.getElementById("company"),
      firstName: document.getElementById("firstName"),
      lastName: document.getElementById("lastName"),
      email: document.getElementById("email"),
      designation: document.getElementById("designation"),
      phone: document.getElementById("phone"),
      organization: document.getElementById("organization"),
      website: document.getElementById("website"),
      address: document.getElementById("address"),
      managerFirstName: document.getElementById("managerFirstName"),
      managerLastName: document.getElementById("managerLastName"),
      managerEmail: document.getElementById("managerEmail"),
      manager2FirstName: document.getElementById("manager2FirstName"),
      manager2LastName: document.getElementById("manager2LastName"),
      manager2Email: document.getElementById("manager2Email"),
    };

    getOrgData().forEach(function (org) {
      state.orgsBySlug[org.slug] = org;
    });

    syncManagerSection();
    bindEvents();
    lockReadOnlyFields();
    loadSignature();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
