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

  // Javobdan keyin: tanlangan xato — qizil, to'g'ri javob — yashil, izoh chiqadi
  function revealAnswer(card, data) {
    card.dataset.answered = "1";
    card.querySelectorAll(".answer-option").forEach(function (btn) {
      const id = parseInt(btn.dataset.answerId, 10);
      btn.disabled = true;
      btn.classList.toggle("is-selected", id === data.selected_answer_id);
      if (id === data.correct_answer_id) btn.classList.add("is-correct");
      else if (id === data.selected_answer_id) btn.classList.add("is-wrong");
      else btn.classList.add("is-dimmed");
    });
    const box = card.querySelector(".explanation");
    if (!box) return;
    box.classList.remove("d-none", "explain--success", "explain--danger");
    box.classList.add(data.is_correct ? "explain--success" : "explain--danger");
    box.innerHTML = "";
    const icon = document.createElement("i");
    icon.className = "bi " + (data.is_correct ? "bi-check-circle-fill" : "bi-lightbulb-fill");
    icon.setAttribute("aria-hidden", "true");
    const body = document.createElement("div");
    const head = document.createElement("strong");
    head.className = "explain__title";
    head.textContent = data.is_correct ? "Toʻgʻri!" : "Xato — toʻgʻri javob yashil bilan belgilangan";
    body.appendChild(head);
    if (data.explanation) {
      const text = document.createElement("span");
      text.textContent = data.explanation;
      body.appendChild(text);
    }
    box.appendChild(icon);
    box.appendChild(body);
  }

  window.PravaQuiz = { getCookie: getCookie, postJSON: postJSON, showAlert: showAlert, isTyping: isTyping, revealAnswer: revealAnswer };
})();
