/* Imtihon ekrani: navigatsiya, taymer, javob saqlash (to'g'ri/xato darrov), yakunlash modali. */
(function () {
  "use strict";

  const root = document.getElementById("exam");
  if (!root) return;

  const Q = window.PravaQuiz;
  const cards = Array.from(root.querySelectorAll(".question-card"));
  const navBtns = Array.from(root.querySelectorAll(".nav-num"));
  const total = cards.length;
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const numberEl = document.getElementById("current-number");
  const timerEl = document.getElementById("timer");
  const alertBox = document.getElementById("ajax-alert");
  const finishForm = document.getElementById("finish-form");
  const unansweredText = document.getElementById("unanswered-text");
  const modalEl = document.getElementById("finishModal");
  const timerValue = document.getElementById("timer-value") || timerEl;
  const modalTime = document.getElementById("modal-time");
  const answeredCount = document.getElementById("answered-count");
  const navStrip = document.getElementById("q-nav");
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let current = parseInt(root.dataset.start, 10) || 0;
  let deadline = Date.now() + (parseInt(root.dataset.timeLeft, 10) || 0) * 1000;
  let submitting = false;
  let timerId = null;

  /* ---- UI yordamchilari ---- */
  function answeredTotal() {
    return cards.filter(function (c) { return c.dataset.answered; }).length;
  }

  function updateCounter() {
    if (answeredCount) answeredCount.textContent = answeredTotal();
  }

  // Telefondagi gorizontal lentada joriy katakni ko'rinadigan joyga surish (sahifani vertikal siljitmaydi)
  function revealNav(btn) {
    if (!navStrip || !btn || navStrip.scrollWidth <= navStrip.clientWidth) return;
    const left = btn.offsetLeft - (navStrip.clientWidth - btn.offsetWidth) / 2;
    if (navStrip.scrollTo) navStrip.scrollTo({ left: left, behavior: reduceMotion ? "auto" : "smooth" });
    else navStrip.scrollLeft = left;
  }

  /* ---- Navigatsiya ---- */
  function go(index) {
    if (index < 0 || index >= total) return;
    current = index;
    cards.forEach(function (c, i) { c.classList.toggle("d-none", i !== current); });
    navBtns.forEach(function (b, i) {
      b.classList.toggle("current", i === current);
      if (i === current) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    });
    numberEl.textContent = current + 1;
    revealNav(navBtns[current]);
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;
  }

  /* ---- Javob saqlash ---- */
  async function choose(card, btn) {
    if (submitting || card.dataset.answered || card.dataset.busy) return;
    const index = parseInt(card.dataset.index, 10);
    const previous = card.querySelector(".answer-option.is-selected");
    card.dataset.busy = "1";

    card.querySelectorAll(".answer-option").forEach(function (b) { b.classList.toggle("is-selected", b === btn); });
    btn.classList.add("is-saving");
    try {
      const res = await Q.postJSON(root.dataset.answerUrl, {
        question_id: parseInt(card.dataset.questionId, 10),
        answer_id: parseInt(btn.dataset.answerId, 10),
      });
      if (res.body && res.body.expired) {
        submitting = true;
        window.location.href = res.body.redirect;
        return;
      }
      if (!res.ok) throw new Error(res.body.error || "");
      Q.revealAnswer(card, res.body);
      navBtns[index].classList.add("answered", res.body.is_correct ? "is-ok" : "is-bad");
      updateCounter();
      if (typeof res.body.time_left === "number") deadline = Date.now() + res.body.time_left * 1000;
    } catch (e) {
      // Holatni qaytarish: avvalgi tanlov saqlanib qolgan
      card.querySelectorAll(".answer-option").forEach(function (b) { b.classList.toggle("is-selected", b === previous); });
      Q.showAlert(alertBox, (e && e.message) || "Javob saqlanmadi. Internetni tekshirib, qayta bosing.");
    } finally {
      btn.classList.remove("is-saving");
      delete card.dataset.busy;
    }
  }

  /* ---- Taymer ---- */
  function format(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function tick() {
    const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    timerValue.textContent = format(left);
    if (modalTime) modalTime.textContent = format(left);
    timerEl.classList.toggle("is-warning", left <= 300 && left > 60);
    timerEl.classList.toggle("is-danger", left <= 60);
    if (left <= 0) {
      clearInterval(timerId);
      submitFinish();
    }
  }

  function submitFinish() {
    if (submitting) return;
    submitting = true;
    finishForm.submit();
  }

  /* ---- Hodisalar ---- */
  root.addEventListener("click", function (e) {
    const btn = e.target.closest(".answer-option");
    if (btn) { choose(btn.closest(".question-card"), btn); return; }
    const nav = e.target.closest(".nav-num");
    if (nav) go(parseInt(nav.dataset.goto, 10));
  });
  prevBtn.addEventListener("click", function () { go(current - 1); });
  nextBtn.addEventListener("click", function () { go(current + 1); });

  document.addEventListener("keydown", function (e) {
    if (Q.isTyping(e) || e.ctrlKey || e.altKey || e.metaKey) return;
    if (modalEl.classList.contains("show")) return;
    if (e.key >= "1" && e.key <= "4") {
      const btn = cards[current].querySelectorAll(".answer-option")[parseInt(e.key, 10) - 1];
      if (btn) choose(cards[current], btn);
    } else if (e.key === "ArrowRight") {
      go(current + 1);
    } else if (e.key === "ArrowLeft") {
      go(current - 1);
    }
  });

  modalEl.addEventListener("show.bs.modal", function () {
    const left = total - answeredTotal();
    // DOM API bilan quriladi (innerHTML ishlatilmaydi)
    unansweredText.textContent = "";
    if (left) {
      const strong = document.createElement("strong");
      strong.className = "text-danger";
      strong.textContent = left + " ta savolga";
      unansweredText.append("Sizda hali vaqt bor, biroq ", strong, " javob berilmagan. Ular xato hisoblanadi.");
    } else {
      unansweredText.textContent = "Barcha savollarga javob berdingiz. Yakunlagach natijani koʻrasiz.";
    }
    if (modalTime) modalTime.textContent = timerValue.textContent;
  });

  finishForm.addEventListener("submit", function () { submitting = true; });

  window.addEventListener("beforeunload", function (e) {
    if (submitting) return;
    e.preventDefault();
    e.returnValue = "";
  });

  go(current);
  updateCounter();
  tick();
  timerId = setInterval(tick, 1000);
})();
