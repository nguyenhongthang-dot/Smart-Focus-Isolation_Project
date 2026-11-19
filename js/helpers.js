/* Hàm tiện ích: h() tạo phần tử DOM, pad(), fmt() */
(function () {
  "use strict";
  var S = window.SFIT;

  /* ---------- Helpers ---------- */
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs)
      for (var k in attrs) {
        if (k === "class") el.className = attrs[k];
        else if (k === "html") el.innerHTML = attrs[k];
        else if (k === "text") el.textContent = attrs[k];
        else if (k.slice(0, 2) === "on")
          el.addEventListener(k.slice(2), attrs[k]);
        else el.setAttribute(k, attrs[k]);
      }
    (children || []).forEach(function (c) {
      if (c == null) return;
      el.appendChild(
        typeof c === "string" ? document.createTextNode(c) : c,
      );
    });
    return el;
  }
  function pad(n) {
    return String(n).padStart(2, "0");
  }
  function fmt(s) {
    return (
      pad(Math.floor(s / 3600)) +
      ":" +
      pad(Math.floor(s / 60) % 60) +
      ":" +
      pad(s % 60)
    );
  }

  S.h = h;
  S.pad = pad;
  S.fmt = fmt;
})();
