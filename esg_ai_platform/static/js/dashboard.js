function csvData(canvas) {
  const labels = (canvas.dataset.labels || "").split(",").filter(Boolean);
  const values = (canvas.dataset.values || "").split(",").filter(Boolean).map(Number);
  return { labels, values };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

function comparisonTooltipMarkup(data) {
  const page = escapeHtml(data.page_number || "-");
  const companies = data.disclosed_companies || [];
  const tags = companies.length
    ? companies.map((company) => `<em>${escapeHtml(company)}</em>`).join("")
    : "<em>目前選取報告中尚無其他公司揭露</em>";
  return `
    <h3>${escapeHtml(data.company)} ${escapeHtml(data.year)} · ${escapeHtml(data.disclosure_code)}</h3>
    <p>${escapeHtml(data.field_label)}</p>
    <div class="tooltip-grid">
      <div><span>揭露狀態</span><strong>${escapeHtml(data.status)}</strong></div>
      <div><span>頁碼</span><strong>${page}</strong></div>
    </div>
    <div class="tooltip-section"><span>指標意義</span><p>${escapeHtml(data.meaning || "此欄位用於衡量報告書揭露完整度與可驗證性。")}</p></div>
    <div class="tooltip-section"><span>同樣有揭露的公司</span><div class="tooltip-tags">${tags}</div></div>
    <div class="tooltip-section"><span>報告書引用</span><p>${escapeHtml(data.evidence_excerpt || "此公司報告未找到該欄位的明確揭露。")}</p></div>
  `;
}

function initComparisonTooltips() {
  const dataElement = document.getElementById("comparison-tooltip-data");
  if (!dataElement) return;
  let payloads = {};
  try {
    payloads = JSON.parse(dataElement.textContent || "{}");
  } catch {
    payloads = {};
  }
  const targets = document.querySelectorAll("[data-comparison-tooltip]");
  if (!targets.length) return;

  const tooltip = document.createElement("div");
  tooltip.className = "comparison-tooltip";
  document.body.appendChild(tooltip);

  const placeTooltip = (event, target = null) => {
    const margin = 14;
    const rect = tooltip.getBoundingClientRect();
    const targetRect = target ? target.getBoundingClientRect() : null;
    const eventX = Number.isFinite(event.clientX) ? event.clientX : (targetRect ? targetRect.left : margin);
    const eventY = Number.isFinite(event.clientY) ? event.clientY : (targetRect ? targetRect.bottom : margin);
    let x = eventX + 16;
    let y = eventY + 16;
    if (x + rect.width + margin > window.innerWidth) {
      x = eventX - rect.width - 16;
    }
    if (y + rect.height + margin > window.innerHeight) {
      y = window.innerHeight - rect.height - margin;
    }
    tooltip.style.transform = `translate3d(${Math.max(margin, x)}px, ${Math.max(margin, y)}px, 0)`;
  };

  const showTooltip = (target, event) => {
    const key = target.dataset.comparisonTooltip;
    const data = payloads[key];
    if (!data) return;
    tooltip.innerHTML = comparisonTooltipMarkup(data);
    tooltip.classList.add("visible");
    placeTooltip(event, target);
  };

  const hideTooltip = () => {
    tooltip.classList.remove("visible");
    tooltip.style.transform = "translate3d(-9999px, -9999px, 0)";
  };

  targets.forEach((target) => {
    target.addEventListener("mouseenter", (event) => showTooltip(target, event));
    target.addEventListener("mousemove", placeTooltip);
    target.addEventListener("mouseleave", hideTooltip);
    target.addEventListener("focus", (event) => showTooltip(target, event));
    target.addEventListener("blur", hideTooltip);
  });
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

  initComparisonTooltips();
});
