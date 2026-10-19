/* Imtihon ekrani: navigatsiya, taymer, javob saqlash, yakunlash modali. */
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

  let current = parseInt(root.dataset.start, 10) || 0;
  let deadline = Date.now() + (parseInt(root.dataset.timeLeft, 10) || 0) * 1000;
  let submitting = false;
  let timerId = null;

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
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;
  }

  /* ---- Javob saqlash ---- */
  async function choose(card, btn) {
    if (submitting) return;
    const index = parseInt(card.dataset.index, 10);
    const previous = card.querySelector(".answer-btn.selected");
    if (previous === btn) return;

    card.querySelectorAll(".answer-btn").forEach(function (b) { b.classList.toggle("selected", b === btn); });
    btn.classList.add("saving");
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
      card.dataset.answered = "1";
      navBtns[index].classList.add("answered");
      if (typeof res.body.time_left === "number") deadline = Date.now() + res.body.time_left * 1000;
    } catch (e) {
      // Holatni qaytarish: avvalgi tanlov saqlanib qolgan
      card.querySelectorAll(".answer-btn").forEach(function (b) { b.classList.toggle("selected", b === previous); });
      Q.showAlert(alertBox, (e && e.message) || "Javob saqlanmadi. Internetni tekshirib, qayta bosing.");
    } finally {
      btn.classList.remove("saving");
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
    timerEl.textContent = format(left);
    timerEl.classList.toggle("timer-warn", left <= 300 && left > 60);
    timerEl.classList.toggle("timer-danger", left <= 60);
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
    const btn = e.target.closest(".answer-btn");
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
      const btn = cards[current].querySelectorAll(".answer-btn")[parseInt(e.key, 10) - 1];
      if (btn) choose(cards[current], btn);
    } else if (e.key === "ArrowRight") {
      go(current + 1);
    } else if (e.key === "ArrowLeft") {
      go(current - 1);
    }
  });

  modalEl.addEventListener("show.bs.modal", function () {
    const left = cards.filter(function (c) { return !c.dataset.answered; }).length;
    unansweredText.textContent = left
      ? "Javob berilmagan savollar: " + left + " ta. Ular xato hisoblanadi."
      : "Barcha savollarga javob berdingiz.";
  });

  finishForm.addEventListener("submit", function () { submitting = true; });

  window.addEventListener("beforeunload", function (e) {
    if (submitting) return;
    e.preventDefault();
    e.returnValue = "";
  });

  go(current);
  tick();
  timerId = setInterval(tick, 1000);
})();
