/* Trang Setting (nguồn thông báo, từ khóa, ngôn ngữ) */
(function () {
  "use strict";
  var S = window.SFIT;
  var h = S.h,
    state = S.state;

  /* ---------- Settings ---------- */
  var SUB = {
    Zalo: "Messaging application",
    "Messenger/facebook": "Social network",
    GMAIL: "Email box",
    Discord: "Chat community",
  };

  var SRC_ICON = {
    Zalo: "assets/zalo.png",
    "Messenger/facebook": "assets/messenger.png",
    GMAIL: "assets/gmail.png",
    Discord: "assets/discord.png",
  };

  function buildSettings() {
    var tabh = h("div", { class: "tabh", text: "Setting" });

    /* language buttons */
    var bVi = h("button", {
      text: "Tiếng Việt",
      onclick: function () {
        state.lang = "vi";
        paintLang();
      },
    });
    var bEn = h("button", {
      text: "English",
      onclick: function () {
        state.lang = "en";
        paintLang();
      },
    });
    function paintLang() {
      bVi.classList.toggle("on", state.lang === "vi");
      bEn.classList.toggle("on", state.lang === "en");
    }
    paintLang();

    /* theme buttons (chỉ giao diện, chưa đổi chủ đề thật) */
    if (!state.theme) state.theme = "desert";
    var THEMES = [
      ["desert", "Desert"],
      ["pond", "Pond"],
      ["ocean", "Ocean"],
    ];
    var themeBox = h("div", { class: "theme" });
    var themeBtns = THEMES.map(function (t) {
      var b = h("button", {
        text: t[1],
        onclick: function () {
          state.theme = t[0];
          paintTheme();
        },
      });
      themeBox.appendChild(b);
      return b;
    });
    function paintTheme() {
      THEMES.forEach(function (t, i) {
        themeBtns[i].classList.toggle("on", state.theme === t[0]);
      });
    }
    paintTheme();
    /* save button */
    var save = h("button", {
      class: "btn",
      text: "Save AI configuration",
    });
    var saveTimer = null;
    save.addEventListener("click", function () {
      try {
        localStorage.setItem(
          "sfit-settings",
          JSON.stringify({
            sources: state.sources,
            kws: state.kws,
            lang: state.lang,
          }),
        );
        save.textContent = "✓ Saved";
      } catch (e) {
        save.textContent = "⚠ Cannot save";
      }
      clearTimeout(saveTimer);
      saveTimer = setTimeout(function () {
        save.textContent = "Save AI configuration";
      }, 1600);
    });

    var top = h("div", { class: "top" }, [
      h("div", null, [
        h("h3", { text: "Data sources and AI configuration" }),
        h("b", {
          text: "App notification source",
          style: "font-size:18px",
        }),
        h("p", { text: "Toggle AI listening and analysis per app." }),
      ]),
      h("div", { class: "acts" }, [
        themeBox,
        h("div", { class: "lang" }, [bVi, bEn]),
        save,
      ]),
    ]);

    /* sources grid */
    var grid = h("div", { class: "grid" });
    Object.keys(state.sources).forEach(function (k) {
      var sw = h("button", {
        class: "sw",
        role: "switch",
        "aria-label": k,
      });
      var card = h("div", { class: "src" }, [
        h("img", { class: "src-ico", src: SRC_ICON[k], alt: "" }),
        h("div", { class: "src-txt" }, [
          k === "GMAIL" ? "Gmail" : k,
          h("small", { text: SUB[k] || "" }),
        ]),
        sw,
      ]);
      function paint() {
        var on = !!state.sources[k];
        card.classList.toggle("on", on);
        sw.classList.toggle("on", on);
        sw.setAttribute("aria-checked", on);
      }
      sw.addEventListener("click", function () {
        state.sources[k] = !state.sources[k];
        paint();
      });
      paint();
      grid.appendChild(card);
    });

    /* keywords */
    var input = h("input", {
      placeholder: "+ Add keywords (App will prioritize your keywords)",
      "aria-label": "Add keyword",
    });
    var kw = h("div", { class: "kw" }, [input]);
    function paintChips() {
      Array.prototype.slice
        .call(kw.querySelectorAll(".chip"))
        .forEach(function (c) {
          c.remove();
        });
      state.kws.forEach(function (k) {
        var x = h("span", {
          class: "x",
          text: "×",
          role: "button",
          "aria-label": "Remove " + k,
        });
        x.addEventListener("click", function () {
          state.kws = state.kws.filter(function (v) {
            return v !== k;
          });
          paintChips();
        });
        kw.insertBefore(h("span", { class: "chip" }, [k + " ", x]), input);
      });
    }
    input.addEventListener("keydown", function (e) {
      var v = input.value.trim();
      if (e.key === "Enter" && v) {
        if (state.kws.indexOf(v) === -1) state.kws.push(v);
        input.value = "";
        paintChips();
      }
    });
    paintChips();

    var panel = h("div", { class: "panel" }, [
      top,
      grid,
      h("div", { class: "divider" }),
      h("b", {
        text: "AI Brain Configuration",
        style: "font-size:18px",
      }),
      h("p", { text: "Your emergency keyword:" }),
      kw,
    ]);
    return [tabh, panel];
  }

  S.buildSettings = buildSettings;
})();
