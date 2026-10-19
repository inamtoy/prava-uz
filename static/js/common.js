/* Mashq va imtihon ekranlari uchun umumiy yordamchilar. */
(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : null;
  }

  async function postJSON(url, data) {
    const resp = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(data),
    });
    let body = {};
    try { body = await resp.json(); } catch (e) { /* JSON bo'lmagan javob */ }
    return { status: resp.status, ok: resp.ok && body.ok, body: body };
  }

  function showAlert(el, text) {
    if (!el) return;
    el.textContent = text;
    el.classList.remove("d-none");
    clearTimeout(el._timer);
    el._timer = setTimeout(function () { el.classList.add("d-none"); }, 4000);
  }

  // Klaviatura: input/textarea ichida yozilayotganda tutmaslik
  function isTyping(e) {
    const t = e.target;
    return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
  }

  window.PravaQuiz = { getCookie: getCookie, postJSON: postJSON, showAlert: showAlert, isTyping: isTyping };
})();
