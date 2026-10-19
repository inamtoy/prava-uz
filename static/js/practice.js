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
    if (onSummary) document.getElementById("summary-score").textContent = correct;

    prevBtn.disabled = current === 0;
    const card = cards[current];
    const isLast = current === total - 1;
    nextBtn.classList.toggle("d-none", onSummary);
    nextBtn.innerHTML = isLast && allAnswered() ? "Yakunlash &rsaquo;" : "Keyingi savol &rsaquo;";
    nextBtn.classList.toggle("btn-primary", !!(card && card.dataset.answered));
    nextBtn.classList.toggle("btn-outline-primary", !(card && card.dataset.answered));

    answeredEl.textContent = answered;
    correctEl.textContent = correct;
    progressEl.style.width = Math.round((answered * 100) / total) + "%";
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
    card.querySelectorAll(".answer-btn").forEach(function (btn) {
      const id = parseInt(btn.dataset.answerId, 10);
      btn.disabled = true;
      btn.classList.toggle("selected", id === data.selected_answer_id);
      if (id === data.correct_answer_id) btn.classList.add("correct");
      else if (id === data.selected_answer_id) btn.classList.add("wrong");
    });
    const box = card.querySelector(".explanation");
    box.classList.remove("d-none", "alert-success", "alert-danger");
    box.classList.add(data.is_correct ? "alert-success" : "alert-danger");
    box.innerHTML = "";
    const head = document.createElement("strong");
    head.textContent = data.is_correct ? "To'g'ri!" : "Xato.";
    box.appendChild(head);
    if (data.explanation) {
      const text = document.createElement("div");
      text.className = "mt-1";
      text.textContent = data.explanation;
      box.appendChild(text);
    }
  }

  async function choose(card, btn) {
    if (busy || card.dataset.answered) return;
    busy = true;
    btn.classList.add("selected");
    try {
      const res = await Q.postJSON(root.dataset.answerUrl, {
        question_id: parseInt(card.dataset.questionId, 10),
        answer_id: parseInt(btn.dataset.answerId, 10),
      });
      if (!res.ok) {
        btn.classList.remove("selected");
        Q.showAlert(alertBox, res.body.error || "Javob saqlanmadi. Qayta urinib ko'ring.");
        return;
      }
      answered += 1;
      if (res.body.is_correct) correct += 1;
      showResult(card, res.body);
      render();
    } catch (e) {
      btn.classList.remove("selected");
      Q.showAlert(alertBox, "Internet aloqasi bilan muammo. Qayta urinib ko'ring.");
    } finally {
      busy = false;
    }
  }

  root.addEventListener("click", function (e) {
    const btn = e.target.closest(".answer-btn");
    if (!btn) return;
    choose(btn.closest(".question-card"), btn);
  });
  prevBtn.addEventListener("click", function () { go(current - 1); });
  nextBtn.addEventListener("click", function () { go(current + 1); });

  document.addEventListener("keydown", function (e) {
    if (Q.isTyping(e) || e.ctrlKey || e.altKey || e.metaKey) return;
    const card = cards[current];
    if (card && e.key >= "1" && e.key <= "4") {
      const btn = card.querySelectorAll(".answer-btn")[parseInt(e.key, 10) - 1];
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
