/* Profil: "Natijalar dinamikasi" grafigi (Chart.js 4) */
(function () {
  "use strict";

  var PASS_LINE = 90; // 20 tadan 18 ta = 90%

  function showEmpty() {
    var box = document.querySelector(".chart-box");
    var empty = document.getElementById("chart-empty");
    if (box) box.hidden = true;
    if (empty) empty.hidden = false;
  }

  function init() {
    var dataEl = document.getElementById("chart-data");
    var canvas = document.getElementById("results-chart");
    if (!dataEl || !canvas) return;

    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { data = null; }
    var labels = (data && Array.isArray(data.labels)) ? data.labels : [];
    var percents = (data && Array.isArray(data.percents)) ? data.percents : [];
    if (!percents.length || typeof window.Chart === "undefined") { showEmpty(); return; }

    var css = getComputedStyle(document.documentElement);
    function token(name, fallback) { return (css.getPropertyValue(name) || "").trim() || fallback; }
    var ink = token("--ink-900", "#0B1B33");
    var muted = token("--ink-500", "#51627E");
    var line = token("--line", "#E6EAF0");
    var accent = token("--accent", "#FFC220");
    var accentInk = token("--accent-ink", "#795900");
    var danger = token("--danger", "#E5383B");
    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var ctx = canvas.getContext("2d");
    var fill = ctx.createLinearGradient(0, 0, 0, canvas.parentNode.clientHeight || 280);
    fill.addColorStop(0, "rgba(11, 27, 51, 0.12)");
    fill.addColorStop(1, "rgba(11, 27, 51, 0)");

    // Bitta nuqta boʻlsa ham chiziq koʻrinsin
    var single = percents.length === 1;

    new window.Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Natija",
            data: percents,
            borderColor: ink,
            borderWidth: 2.5,
            backgroundColor: fill,
            fill: true,
            tension: 0.3,
            pointRadius: single ? 6 : 5,
            pointHoverRadius: 7,
            pointBackgroundColor: percents.map(function (p) { return p >= PASS_LINE ? accent : "#fff"; }),
            pointBorderColor: percents.map(function (p) { return p >= PASS_LINE ? ink : danger; }),
            pointBorderWidth: 2
          },
          {
            label: "Oʻtish chegarasi",
            data: labels.map(function () { return PASS_LINE; }),
            borderColor: accentInk,
            borderWidth: 1.5,
            borderDash: [6, 5],
            pointRadius: 0,
            pointHoverRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: reduceMotion ? false : { duration: 600 },
        interaction: { mode: "index", intersect: false },
        layout: { padding: { top: 8, right: 8 } },
        scales: {
          y: {
            min: 0, max: 100,
            ticks: { stepSize: 25, color: muted, font: { family: "Inter", size: 12 }, callback: function (v) { return v + "%"; } },
            grid: { color: line, drawTicks: false },
            border: { display: false }
          },
          x: {
            ticks: { color: muted, font: { family: "Inter", size: 12 }, maxRotation: 0, autoSkipPadding: 12 },
            grid: { display: false },
            border: { display: false }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: ink,
            titleColor: accent,
            titleFont: { family: "Manrope", weight: "800", size: 11 },
            bodyFont: { family: "Manrope", weight: "700", size: 14 },
            padding: 10,
            cornerRadius: 10,
            displayColors: false,
            filter: function (item) { return item.datasetIndex === 0; },
            callbacks: {
              title: function (items) { return items.length ? items[0].label : ""; },
              label: function (item) {
                var p = item.parsed.y;
                return p + "% — " + (p >= PASS_LINE ? "Oʻtdi" : "Oʻtmadi");
              }
            }
          }
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
