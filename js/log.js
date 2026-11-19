/* Trang Log (thông báo khẩn) */
(function () {
  "use strict";
  var S = window.SFIT;
  var h = S.h;

  /* ---------- Log ---------- */
  var LOGS = [
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "",
      "#F0484B",
      "Gmail • Phòng Đào Tạo",
      "13:50",
      "[THÔNG BÁO] Hoãn lịch thi môn Cơ Sở Dữ Liệu tuần sau",
    ],
    [
      "Z",
      "#2F5BE8",
      "Messenger • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Discord • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
    [
      "Z",
      "#2F5BE8",
      "Zalo • Nguyễn Văn Hải (Trợ Giảng)",
      "14:30",
      "Em ơi hạn nộp bài tập C++ hết hạn lúc 5h chiều nay nhé, nộp gấp!",
    ],
  ];

  /* Bảng ảnh theo tên nguồn (viết thường, lấy từ chữ đứng trước dấu •) */
  var LOG_ICON = {
    zalo: "assets/zalo.png",
    messenger: "assets/messenger.png",
    gmail: "assets/gmail.png",
    discord: "assets/discord.png",
  };

  function logIcon(title) {
    var name = title.split("•")[0].trim().toLowerCase();
    return LOG_ICON[name] || "";
  }

  function buildLog() {
    var head = h(
      "div",
      {
        class: "top",
        style:
          "align-items:center;padding-bottom:2vh;border-bottom:1px solid rgba(255,255,255,.4)",
      },
      [
        h("b", {
          text: "Recent emergency notification log (last 2 days)",
          style: "font-size:clamp(16px,2.8vh,24px)",
        }),
        h("button", {
          class: "btn",
          text: "▶ Back to focus mode",
          onclick: function () {
            S.go("home");
          },
        }),
      ],
    );
    /* chỉnh chiều cao của bảng */
    var panel = h("div", { class: "panel" }, [head]);
    LOGS.forEach(function (l) {
      var icon = logIcon(l[2]);
      var av = icon
        ? h("img", { class: "av", src: icon, alt: "" })
        : h("div", {
            class: "av",
            text: l[0],
            style: "background:" + l[1],
          });

      panel.appendChild(
        h("div", { class: "log" }, [
          av,
          h("div", null, [
            h("b", { text: l[2], style: "font-size:14px" }),
            h("small", { text: l[3] }),
            h("p", { text: l[4] }),
          ]),
          h("span", { class: "ur" }, [
            h("img", { src: "assets/warning.png", alt: "" }),
            "Urgent",
          ]),
        ]),
      );
    });
    return panel;
  }
  S.buildLog = buildLog;
})();
