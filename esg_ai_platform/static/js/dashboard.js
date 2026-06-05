function csvData(canvas) {
  const labels = (canvas.dataset.labels || "").split(",").filter(Boolean);
  const values = (canvas.dataset.values || "").split(",").filter(Boolean).map(Number);
  return { labels, values };
}

document.addEventListener("DOMContentLoaded", () => {
  const scoreCanvas = document.getElementById("scoreChart");
  if (scoreCanvas && window.Chart) {
    const { labels, values } = csvData(scoreCanvas);
    new Chart(scoreCanvas, {
      type: "bar",
      data: { labels, datasets: [{ label: "加權分", data: values, backgroundColor: "#2f7d57" }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 25 } } }
    });
  }

  const weightCanvas = document.getElementById("weightChart");
  if (weightCanvas && window.Chart) {
    const { labels, values } = csvData(weightCanvas);
    new Chart(weightCanvas, {
      type: "doughnut",
      data: { labels, datasets: [{ data: values, backgroundColor: ["#2f7d57", "#2364aa", "#d9822b", "#7a5195", "#bf4342"] }] },
      options: { responsive: true }
    });
  }
});
