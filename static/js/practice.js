/* Mashq ekrani: javob bosilganda darhol to'g'ri/xato va izoh ko'rsatiladi. */
(function () {
  "use strict";

  const root = document.getElementById("practice");
  if (!root) return;

  const Q = window.PravaQuiz;
  const cards = Array.from(root.querySelectorAll(".question-card"));
  const total = cards.length;
  const summary = document.getElementById("practice-summary");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const alertBox = document.getElementById("ajax-alert");
  const answeredEl = document.getElementById("answered-count");
  const correctEl = document.getElementById("correct-count");
  const progressEl = document.getElementById("practice-progress");
  const positionEl = document.getElementById("practice-position");
  const wrongEl = document.getElementById("wrong-count");
  const scoreRing = document.getElementById("score-ring");
  const scoreRingValue = document.getElementById("score-ring-value");
  const summaryRing = document.getElementById("summary-ring");
  const summaryPercent = document.getElementById("summary-percent");
  const toast = document.getElementById("practice-toast");
  let toastTimer = null;

  let answered = parseInt(root.dataset.answered, 10) || 0;
  let correct = parseInt(root.dataset.correct, 10) || 0;
  let current = parseInt(root.dataset.start, 10) || 0;
  let busy = false;

  function allAnswered() {
    return answered >= total;
  }

  function render() {
    const onSummary = current >= total;
    cards.forEach(function (card, i) { card.classList.toggle("d-none", i !== current); });
    summary.classList.toggle("d-none", !onSummary);
    if (onSummary) {
      document.getElementById("summary-score").textContent = correct;
      const sp = total ? Math.round((correct * 100) / total) : 0;
      setRing(summaryRing, summaryPercent, sp);
      summaryRing.classList.toggle("progress-ring--success", sp >= 90);
      summaryRing.classList.toggle("progress-ring--danger", sp < 70);
    }

    prevBtn.disabled = current === 0;
    const card = cards[current];
    const isLast = current === total - 1;
    nextBtn.classList.toggle("d-none", onSummary);
    nextBtn.innerHTML = (isLast && allAnswered() ? "Yakunlash" : "Keyingi savol") +
      ' <i class="bi bi-arrow-right" aria-hidden="true"></i>';
    nextBtn.classList.toggle("btn-accent", !!(card && card.dataset.answered));
    nextBtn.classList.toggle("btn-ghost", !(card && card.dataset.answered));
    root.classList.toggle("is-summary", onSummary);
    if (positionEl) {
      positionEl.textContent = onSummary ? "Yakunlandi" : "Savol " + (current + 1) + " / " + total;
    }

    answeredEl.textContent = answered;
    correctEl.textContent = correct;
    progressEl.style.width = Math.round((answered * 100) / total) + "%";
    if (wrongEl) wrongEl.textContent = answered - correct;
    setRing(scoreRing, scoreRingValue, answered ? Math.round((correct * 100) / answered) : 0);
  }

  function setRing(ring, valueEl, percent) {
    if (!ring) return;
    ring.style.setProperty("--p", percent);
    if (valueEl) valueEl.textContent = percent + "%";
  }

  function showToast() {
    if (!toast) return;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("is-visible"); }, 1600);
  }

  function go(index) {
    if (index < 0) return;
    if (index >= total) index = allAnswered() ? total : findUnanswered(total - 1);
    current = index;
    render();
    window.scrollTo({ top: root.offsetTop - 16, behavior: "smooth" });
  }

  function findUnanswered(fallback) {
    const i = cards.findIndex(function (c) { return !c.dataset.answered; });
    return i === -1 ? fallback : i;
  }

  function showResult(card, data) {
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

  async function choose(card, btn) {
    if (busy || card.dataset.answered) return;
    busy = true;
    btn.classList.add("is-selected");
    try {
      const res = await Q.postJSON(root.dataset.answerUrl, {
        question_id: parseInt(card.dataset.questionId, 10),
        answer_id: parseInt(btn.dataset.answerId, 10),
      });
      if (!res.ok) {
        btn.classList.remove("is-selected");
        Q.showAlert(alertBox, res.body.error || "Javob saqlanmadi. Qayta urinib ko'ring.");
        return;
      }
      answered += 1;
      if (res.body.is_correct) correct += 1;
      showResult(card, res.body);
      if (res.body.is_correct) showToast();
      render();
    } catch (e) {
      btn.classList.remove("is-selected");
      Q.showAlert(alertBox, "Internet aloqasi bilan muammo. Qayta urinib ko'ring.");
    } finally {
      busy = false;
    }
  }

  root.addEventListener("click", function (e) {
    const btn = e.target.closest(".answer-option");
    if (!btn) return;
    choose(btn.closest(".question-card"), btn);
  });
  prevBtn.addEventListener("click", function () { go(current - 1); });
  nextBtn.addEventListener("click", function () { go(current + 1); });

  document.addEventListener("keydown", function (e) {
    if (Q.isTyping(e) || e.ctrlKey || e.altKey || e.metaKey) return;
    const card = cards[current];
    if (card && e.key >= "1" && e.key <= "4") {
      const btn = card.querySelectorAll(".answer-option")[parseInt(e.key, 10) - 1];
      if (btn) choose(card, btn);
    } else if (e.key === "ArrowRight" || (e.key === "Enter" && card && card.dataset.answered)) {
      e.preventDefault();
      go(current + 1);
    } else if (e.key === "ArrowLeft") {
      go(current - 1);
    }
  });

  if (allAnswered()) current = total;
  render();
})();
