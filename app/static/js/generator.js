(function () {
  "use strict";

  var MANAGER_L1_KEYS = [
    "managerFirstName",
    "managerLastName",
    "managerDesignation",
    "managerEmail",
    "managerPhone",
  ];
  var MANAGER_L2_KEYS = [
    "manager2FirstName",
    "manager2LastName",
    "manager2Designation",
    "manager2Email",
    "manager2Phone",
  ];

  var DEFAULT_FORM = {
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

  var FIXED_WEBSITE = "www.arvind.com";

  var PREFILL_KEYS = [
    "firstName",
    "lastName",
    "email",
    "designation",
    "phone",
    "organization",
    "address",
  ].concat(MANAGER_L1_KEYS);

  var DETAIL_KEYS = [
    "firstName",
    "lastName",
    "email",
    "designation",
    "phone",
    "organization",
    "website",
    "address",
  ].concat(MANAGER_L1_KEYS, MANAGER_L2_KEYS);

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

  function getFormValues() {
    var values = {};
    Object.keys(fields).forEach(function (key) {
      values[key] = fields[key] ? fields[key].value : "";
    });
    values.website = FIXED_WEBSITE;
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
    if (fields.website) fields.website.value = FIXED_WEBSITE;
  }

  function setDetailFieldsEnabled(enabled) {
    DETAIL_KEYS.forEach(function (key) {
      if (!fields[key] || key === "website") return;
      fields[key].disabled = !enabled;
    });
    if (fields.website) {
      fields.website.value = FIXED_WEBSITE;
      fields.website.readOnly = true;
      fields.website.disabled = false;
    }
  }

  function syncManagerSection() {
    if (!els.managerSection) return;
    var isSales = state.team === "sales";
    els.managerSection.hidden = !isSales;
    if (!isSales) return;

    if (els.managerLevel1) els.managerLevel1.hidden = state.managerLevel < 1;
    if (els.managerLevel2) els.managerLevel2.hidden = state.managerLevel < 2;

    if (els.addManagerBtn) {
      if (state.managerLevel >= 2) {
        els.addManagerBtn.hidden = true;
      } else {
        els.addManagerBtn.hidden = false;
        els.addManagerBtn.textContent =
          state.managerLevel === 0 ? "Add Manager" : "Add Level 2 Manager";
      }
    }
  }

  function handleAddManager() {
    if (state.managerLevel < 2) {
      state.managerLevel += 1;
      syncManagerSection();
      renderPreview();
      scheduleSave();
    }
  }

  function handleRemoveManagerL1() {
    clearManagerKeys(MANAGER_L1_KEYS);
    clearManagerKeys(MANAGER_L2_KEYS);
    state.managerLevel = 0;
    syncManagerSection();
    renderPreview();
    scheduleSave();
  }

  function handleRemoveManagerL2() {
    clearManagerKeys(MANAGER_L2_KEYS);
    state.managerLevel = 1;
    syncManagerSection();
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
        var form = data.isDefault
          ? baseFormDefaults()
          : applyPrefillToEmpty(data.form || baseFormDefaults());
        setFormValues(form);
        if (form.templateId) state.templateId = form.templateId;
        if (hasAnyData(form, MANAGER_L2_KEYS)) {
          state.managerLevel = 2;
        } else if (hasAnyData(form, MANAGER_L1_KEYS)) {
          state.managerLevel = 1;
        } else {
          state.managerLevel = 0;
        }
        var boot = window.__SIG_BOOT__ || {};
        if (boot.userEmail && fields.email) {
          fields.email.value = boot.userEmail;
        }
        // Sales: surface Level 1 manager section when Graph provided manager data.
        if (
          state.team === "sales" &&
          state.managerLevel < 1 &&
          hasAnyData(bootPrefill(), MANAGER_L1_KEYS)
        ) {
          state.managerLevel = 1;
        }
        setDetailFieldsEnabled(!!fields.company.value);
        syncManagerSection();
        renderTemplateSelection();
        return renderPreview();
      });
  }

  function handleCompanyChange() {
    var slug = fields.company.value;
    var org = state.orgsBySlug[slug];
    setDetailFieldsEnabled(!!org);
    if (org) {
      fields.organization.value = org.organization;
      fields.website.value = FIXED_WEBSITE;
    }
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

  function waitForImages(root) {
    var images = Array.prototype.slice.call(root.querySelectorAll("img"));
    if (!images.length) return Promise.resolve();
    return Promise.all(
      images.map(function (img) {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return new Promise(function (resolve) {
          var done = function () {
            resolve();
          };
          img.addEventListener("load", done, { once: true });
          img.addEventListener("error", done, { once: true });
        });
      })
    );
  }

  function downloadPngBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename || "signature.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function copyPngBlob(blob) {
    if (navigator.clipboard && window.ClipboardItem) {
      return navigator.clipboard
        .write([new ClipboardItem({ "image/png": blob })])
        .then(function () {
          return true;
        })
        .catch(function () {
          return false;
        });
    }
    return Promise.resolve(false);
  }

  function copyRenderedSignature() {
    if (typeof html2canvas !== "function") {
      showStatus("Image copy is unavailable. Try Copy HTML Code instead.", true);
      return;
    }

    showStatus("Creating signature image…");
    fetchPreview(true)
      .then(function (data) {
        if (data.needsOrganization) {
          showStatus("Select an organization first.", true);
          return null;
        }
        els.preview.innerHTML = data.html || "";
        return waitForImages(els.preview).then(function () {
          return html2canvas(els.preview, {
            backgroundColor: "#ffffff",
            scale: 2,
            useCORS: true,
            logging: false,
          });
        });
      })
      .then(function (canvas) {
        if (!canvas) return;
        return new Promise(function (resolve, reject) {
          canvas.toBlob(function (blob) {
            if (!blob) {
              reject(new Error("Could not create PNG"));
              return;
            }
            resolve(blob);
          }, "image/png");
        });
      })
      .then(function (blob) {
        if (!blob) return;
        return copyPngBlob(blob).then(function (ok) {
          if (ok) {
            showStatus("Signature image copied. Paste it into Outlook, Gmail, or Zoho Mail.");
          } else {
            downloadPngBlob(blob, "signature.png");
            showStatus(
              "Clipboard image copy blocked. Downloaded signature.png instead — insert that image into your email."
            );
          }
          audit("signature_copied");
        });
      })
      .catch(function (err) {
        console.error(err);
        showStatus("Copy failed. Try Copy HTML Code instead.", true);
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
    values.website = FIXED_WEBSITE;
    MANAGER_L2_KEYS.forEach(function (k) {
      values[k] = "";
    });
    if (state.team === "sales" && hasAnyData(bootPrefill(), MANAGER_L1_KEYS)) {
      state.managerLevel = 1;
    } else {
      state.managerLevel = 0;
      if (!hasAnyData(bootPrefill(), MANAGER_L1_KEYS)) {
        MANAGER_L1_KEYS.forEach(function (k) {
          values[k] = "";
        });
      }
    }
    setFormValues(values);
    state.templateId = "standard";
    setDetailFieldsEnabled(false);
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
    Object.keys(fields).forEach(function (key) {
      if (key === "company" || !fields[key]) return;
      fields[key].addEventListener("input", onFormInput);
      fields[key].addEventListener("change", onFormInput);
    });
    fields.company.addEventListener("change", handleCompanyChange);
    if (els.addManagerBtn) {
      els.addManagerBtn.addEventListener("click", handleAddManager);
    }
    if (els.removeManagerL1) {
      els.removeManagerL1.addEventListener("click", handleRemoveManagerL1);
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
      addManagerBtn: document.getElementById("add-manager-btn"),
      removeManagerL1: document.getElementById("remove-manager-l1"),
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
      managerDesignation: document.getElementById("managerDesignation"),
      managerEmail: document.getElementById("managerEmail"),
      managerPhone: document.getElementById("managerPhone"),
      manager2FirstName: document.getElementById("manager2FirstName"),
      manager2LastName: document.getElementById("manager2LastName"),
      manager2Designation: document.getElementById("manager2Designation"),
      manager2Email: document.getElementById("manager2Email"),
      manager2Phone: document.getElementById("manager2Phone"),
    };

    getOrgData().forEach(function (org) {
      state.orgsBySlug[org.slug] = org;
    });

    syncManagerSection();
    bindEvents();
    setDetailFieldsEnabled(false);
    loadSignature();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
