/* Trang chủ: Timer / Stopwatch */
(function () {
  "use strict";
  var S = window.SFIT;
  var h = S.h,
    fmt = S.fmt,
    ICONS = S.ICONS,
    PRESETS = S.PRESETS,
    state = S.state;

  /* ---------- Timer ---------- */
  var T = state.timer;
  T.started = false; // MỚI: đã bấm Start và chưa Reset (kể cả đang Pause)
  var tick = null;
  var finishTimer = null; // MỚI: chờ 1,5s sau khi hết giờ rồi mới reset về mặc định

  var CLOSE_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/></svg>';

  /* "005000" -> 3000 giây. Trả null nếu sai định dạng */
  function parseHMS(str) {
    if (!/^\d{6}$/.test(str)) return null; // bắt buộc đúng 6 chữ số
    var hh = parseInt(str.slice(0, 2), 10);
    var mm = parseInt(str.slice(2, 4), 10);
    var ss = parseInt(str.slice(4, 6), 10);
    if (mm > 59 || ss > 59) return null; // phút/giây phải < 60
    var sec = hh * 3600 + mm * 60 + ss;
    return sec > 0 ? sec : null; // không cho 000000
  }

  function total() {
    if (T.customSeconds !== undefined && T.customSeconds !== null) {
      return T.customSeconds;
    }
    return PRESETS[T.pi] * 60;
  }

  /* MỚI: nếu đang chờ reset sau khi hết giờ thì reset ngay về 00:25:00 */
  function finishNow() {
    if (finishTimer) {
      clearTimeout(finishTimer);
      finishTimer = null;
      T.el = 0;
      T.customSeconds = null;
    }
  }

  function startTick() {
    if (tick) return;
    tick = setInterval(function () {
      T.el += 1;
      if (T.mode === "timer" && T.el >= total()) {
        /* MỚI: hết giờ -> vòng tròn đủ 1 vòng, giữ 1,5s rồi reset về mặc định */
        T.run = false;
        T.started = false; // MỚI: hết giờ -> về trạng thái ban đầu
        T.el = total();
        finishTimer = setTimeout(function () {
          finishTimer = null;
          T.el = 0;
          T.customSeconds = null; // về 00:25:00 mặc định
          paintTimer();
        }, 1500);
      }
      if (!T.run) stopTick();
      paintTimer();
    }, 1000);
  }

  function stopTick() {
    if (tick) {
      clearInterval(tick);
      tick = null;
    }
  }

  function setRun(v) {
    if (v) finishNow(); // MỚI: bấm Start lúc đang chờ reset thì reset luôn rồi chạy
    if (v) {
      closeTimeModal();
      T.started = true; // MỚI: Start / Continue -> đã bắt đầu
    }
    T.run = v;
    if (v) startTick();
    else stopTick();
    paintTimer();
  }

  function reset() {
    finishNow(); // MỚI
    T.el = 0;
    T.started = false; // MỚI: Reset -> về Start focus, Reset mờ lại
    setRun(false);
  }

  /* ---------- Hộp nhập giờ (Set time) ---------- */
  function openTimeModal() {
    if (T.run || T.started || T.mode !== "timer" || !S.ui.modal) return;
    finishNow(); // MỚI: tránh bị reset đè lên giờ vừa nhập
    S.ui.tmInput.value = "";
    S.ui.tmHint.textContent = "";
    S.ui.modal.classList.remove("err");
    S.ui.modal.classList.add("show");
    S.ui.tmInput.focus();
  }

  function closeTimeModal() {
    if (!S.ui.modal) return;
    S.ui.modal.classList.remove("show");
    S.ui.tmInput.blur();
  }

  function onTimeInput() {
    var inp = S.ui.tmInput;
    var v = inp.value.replace(/\D/g, "").slice(0, 6); // chỉ giữ số, tối đa 6
    inp.value = v;
    S.ui.modal.classList.remove("err");
    S.ui.tmHint.textContent = "";
    if (v.length < 6) return; // chưa đủ 6 ký tự -> chưa làm gì

    var sec = parseHMS(v);
    if (sec === null) {
      void S.ui.modal.offsetWidth; // restart animation rung
      S.ui.modal.classList.add("err");
      S.ui.tmHint.textContent =
        "Error: Minutes and seconds cannot exceed 59, and time cannot be 00:00:00";
      return;
    }
    T.customSeconds = sec;
    T.el = 0;
    closeTimeModal();
    paintTimer(); // hiện số lên màn hình, bấm Start focus để đếm ngược
  }

  function buildTimer() {
    var R = 330,
      C = 350;
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "ring");
    svg.setAttribute("viewBox", "0 0 700 700");
    svg.innerHTML =
      '<circle cx="' +
      C +
      '" cy="' +
      C +
      '" r="' +
      R +
      '" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="5"/>' +
      '<circle id="arc" cx="' +
      C +
      '" cy="' +
      C +
      '" r="' +
      R +
      '" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="5" pathLength="100" transform="rotate(-90 ' +
      C +
      " " +
      C +
      ')"/>' +
      '<circle id="dot" r="14" fill="#fff"/>';

    S.ui.btnTimer = h("button", {
      text: "Timer",
      onclick: function () {
        switchMode("timer");
      },
    });
    S.ui.btnStop = h("button", {
      text: "Stopwatch",
      onclick: function () {
        switchMode("stop");
      },
    });
    S.ui.cats = ["Study", "Work", "Read"].map(function (m) {
      return h("button", {
        text: m,
        onclick: function () {
          T.cat = m;
          paintTimer();
        },
      });
    });
    S.ui.time = document.createTextNode("");
    S.ui.hg = h("button", {
      class: "hg",
      html: '<img src="assets/hourglass.png" alt="">',
      title: "Nhấp để nhập thời gian",
      "aria-label": "Nhấp để nhập thời gian",
      onclick: openTimeModal, // chỉ icon đồng hồ cát mở hộp nhập
    });

    // KHÔNG gắn onclick cho .clock nữa (tránh gọi 2 lần do bubbling)
    S.ui.clock = h("div", { class: "clock" }, [S.ui.time, S.ui.hg]);

    S.ui.start = h("button", {
      class: "start",
      onclick: function () {
        setRun(!T.run);
      },
    });
    S.ui.reset = h("button", {
      class: "reset",
      html: ICONS.rs,
      "aria-label": "Reset",
      onclick: reset,
    });

    var inner = h("div", { class: "in" }, [
      h("div", { class: "seg" }, [S.ui.btnTimer, S.ui.btnStop]),
      h("div", { class: "modes" }, S.ui.cats),
      S.ui.clock,
      S.ui.start,
      S.ui.reset,
    ]);

    /* Hộp nhập giờ */
    S.ui.tmInput = h("input", {
      class: "tm-input",
      type: "text",
      inputmode: "numeric",
      maxlength: "6",
      autocomplete: "off",
      placeholder: "Ex: 005000 → 00:50:00, 001249 → 00:12:49, ....",
      "aria-label": "Nhập thời gian dạng hhmmss (6 chữ số)",
      oninput: onTimeInput,
      onkeydown: function (e) {
        if (e.key === "Escape") closeTimeModal();
      },
    });
    S.ui.tmHint = h("p", { class: "tm-hint" });
    S.ui.modal = h(
      "div",
      { class: "tm-modal", role: "dialog", "aria-label": "Set timer" },
      [
        h("div", { class: "tm-head" }, [
          h("span", { class: "tm-tag", text: "Set timer" }),
          h("button", {
            class: "tm-close",
            html: CLOSE_ICON,
            "aria-label": "Đóng",
            onclick: closeTimeModal,
          }),
        ]),
        S.ui.tmInput,
        S.ui.tmHint,
      ],
    );

    var dial = h("div", { class: "dial" }, [svg, inner, S.ui.modal]);
    S.ui.arc = svg.querySelector("#arc");
    S.ui.dot = svg.querySelector("#dot");
    S.ui.stage = h("div", { class: "stage" }, [dial]);
    paintTimer();
    return S.ui.stage;
  }

  function switchMode(m) {
    finishNow(); // MỚI
    closeTimeModal();
    T.mode = m;
    T.customSeconds = null;
    T.el = 0;
    T.started = false; // MỚI
    setRun(false);
  }

  /* Icon khung tròn góc phải: fire.png (chưa Start) <-> fire2.png (đã Start) */
  function paintFocusIcon() {
    var ico = document.getElementById("ico-fire");
    if (!ico) return;
    var key = T.started ? "fire2" : "fire";
    if (ico.getAttribute("data-k") === key) return;
    ico.setAttribute("data-k", key);
    ico.innerHTML = '<img src="assets/' + key + '.png" alt="">';
  }

  function paintTimer() {
    paintFocusIcon();
    if (!S.ui.stage) return;
    var shown = T.mode === "timer" ? total() - T.el : T.el;

    /* MỚI: tính phần vòng tròn đã đi (0 -> 1), 0 = chấm ở trên cùng */
    var frac = 0;
    if (T.mode === "timer") {
      // Timer: đi hết 1 vòng khi về 0
      frac = total() > 0 ? T.el / total() : 0;
    } else if (T.el > 0) {
      // Stopwatch: 1 giờ = 1 vòng. Đủ mỗi giờ thì hiện đủ vòng, rồi về đỉnh chạy tiếp
      frac = T.el % 3600 === 0 ? 1 : (T.el % 3600) / 3600;
    }
    frac = Math.min(frac, 1);

    var f = Math.max(frac, 0.002),
      R = 330,
      C = 350;
    var a = -Math.PI / 2 + f * 2 * Math.PI;

    S.ui.arc.setAttribute("stroke-dasharray", f * 100 + " 100");
    S.ui.dot.setAttribute("cx", C + R * Math.cos(a));
    S.ui.dot.setAttribute("cy", C + R * Math.sin(a));

    S.ui.btnTimer.classList.toggle("on", T.mode === "timer");
    S.ui.btnStop.classList.toggle("on", T.mode === "stop");
    S.ui.cats.forEach(function (b) {
      b.classList.toggle("on", b.textContent === T.cat);
    });
    S.ui.time.nodeValue = fmt(shown);
    S.ui.hg.style.display = T.mode === "timer" ? "" : "none";
    S.ui.hg.disabled = T.started; // chìm khi đang chạy HOẶC đang Pause
    S.ui.reset.disabled = !T.started; // MỚI: chưa Start thì Reset mờ, không bấm được
    S.ui.btnTimer.disabled = T.started && T.mode !== "timer";
    S.ui.btnStop.disabled = T.started && T.mode !== "stop";
    S.ui.start.textContent = T.run
      ? "Pause"
      : T.started
        ? "Continue"
        : "Start focus";
    S.ui.start.classList.toggle("on", T.run);
  }

  S.buildTimer = buildTimer;
})();
