/* Trang Introduce */
(function () {
  "use strict";
  var S = window.SFIT;
  var h = S.h;

  /* ---------- Introduce ---------- */
  function buildIntro() {
    var tabh = h("div", { class: "tabh", text: "Introduce" });

    var problem = h("p", { class: "p" }, [
      'Managing computer notifications is a constant dilemma: turning on "Do Not Disturb" blocks everything—risking missed emergencies or deadlines—while leaving it off invites endless distractions. We need a smart filter that silences everyday noise while letting urgent, time-sensitive messages through.',
    ]);

    var rules = h("p", { class: "p" }, [
      h("b", { text: "Processing Rules:" }),
      h("br"),
      "• Non-urgent: System remains silent and auto-saves.",
      h("br"),
      "• Urgent: Activates sound and pushes a priority alert.",
    ]);

    // --- PHẦN SỬA MỚI: Tạo biến fbInput và lấy lại chữ đã lưu trong state ---
    var fbInput = h("input", {
      type: "text",
      class: "fb",
      placeholder: "+ Your feedback",
      value: S.state.fbDraft || "", // Khôi phục chữ nếu trước đó đã gõ
      oninput: function () {
        S.state.fbDraft = fbInput.value; // Lưu liên tục mỗi khi gõ phím
      },
    });
    // ---------------------------------------------------------------------

    var sent = h("button", { class: "sent", type: "button" });
    sent.innerHTML =
      '<span class="lbl">Sent</span>' +
      '<svg class="tick" viewBox="0 0 20 20" width="18" height="18">' +
      '<circle cx="10" cy="10" r="10" fill="#fff"/>' +
      '<path d="M4.5 10.5l3.5 3.5 7.5-8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>' +
      "</svg>";

    sent.addEventListener("click", function () {
      // --- PHẦN THÊM MỚI: Chặn gửi nếu ô input trống hoặc chỉ chứa khoảng trắng ---
      if (!fbInput.value.trim()) {
        fbInput.focus(); // Tự động đưa con trỏ chuột vào ô nhập để nhắc người dùng
        return;
      }
      // --------------------------------------------------------------------------

      if (sent.classList.contains("done")) return;

      sent.classList.add("done");

      fbInput.value = "";
      S.state.fbDraft = "";

      setTimeout(function () {
        sent.classList.remove("done");
      }, 2000);
    });

    var panel = h("div", { class: "panel" }, [
      problem,
      h("br"),
      h("h3", { text: "Smart Focus Isolation (SFIT)" }),
      h("p", {
        class: "p",
        text: "This is an AI-integrated software running in the background on Windows to protect your deep work space. By using AI to analyze the context of every incoming message, the application completely suppresses unnecessary, distracting messages. It only triggers a sound and pop-up alert when it detects truly urgent information or deadlines, helping users eliminate the fear of missing important messages during their focus sessions.",
      }),
      rules,
      fbInput, // Đưa biến fbInput vào đây thay cho dòng h("input", ...) cũ
      sent,
    ]);

    return [tabh, panel];
  }

  S.buildIntro = buildIntro;
})();
