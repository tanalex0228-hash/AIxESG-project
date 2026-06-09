function csvData(canvas) {
  const labels = (canvas.dataset.labels || "").split(",").filter(Boolean);
  const values = (canvas.dataset.values || "").split(",").filter(Boolean).map(Number);
  return { labels, values };
}

function jsonData(id, fallback = {}) {
  const element = document.getElementById(id);
  if (!element) return fallback;
  try {
    return JSON.parse(element.textContent || "{}");
  } catch {
    return fallback;
  }
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

function initIndustryCharts() {
  if (!window.Chart) return;
  const distribution = jsonData("industry-distribution-data", null);
  const trend = jsonData("industry-trend-data", null);
  if (distribution) {
    const rawCanvas = document.getElementById("rawHistogram");
    if (rawCanvas) {
      new Chart(rawCanvas, {
        type: "bar",
        data: { labels: distribution.raw_score.labels, datasets: [{ label: "Raw Score", data: distribution.raw_score.values, backgroundColor: "#2364aa" }] },
        options: { responsive: true, plugins: { legend: { display: false }, title: { display: true, text: "Raw Score Distribution" } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
      });
    }
    const prCanvas = document.getElementById("prHistogram");
    if (prCanvas) {
      new Chart(prCanvas, {
        type: "bar",
        data: { labels: distribution.pr.labels, datasets: [{ label: "PR", data: distribution.pr.values, backgroundColor: "#2f7d57" }] },
        options: { responsive: true, plugins: { legend: { display: false }, title: { display: true, text: "PR Distribution" } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
      });
    }
    const gradeCanvas = document.getElementById("gradeDistribution");
    if (gradeCanvas) {
      new Chart(gradeCanvas, {
        type: "bar",
        data: { labels: distribution.grade.labels, datasets: [{ label: "Grade", data: distribution.grade.values, backgroundColor: "#d9822b" }] },
        options: { responsive: true, plugins: { legend: { display: false }, title: { display: true, text: "Grade Distribution" } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
      });
    }
  }
  const trendCanvas = document.getElementById("industryTrend");
  if (trend && trendCanvas) {
    new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: trend.labels,
        datasets: [
          { label: "平均 Raw Score", data: trend.raw_score, borderColor: "#2364aa", backgroundColor: "rgba(35,100,170,.12)", tension: .25 },
          { label: "平均揭露率", data: trend.disclosure_rate, borderColor: "#2f7d57", backgroundColor: "rgba(47,125,87,.12)", tension: .25 }
        ]
      },
      options: { responsive: true, plugins: { title: { display: true, text: "Industry Trend" } }, scales: { y: { beginAtZero: true, max: 100 } } }
    });
  }
}

function initCompareWorkbench() {
  const workbench = document.querySelector(".compare-workbench");
  const form = document.getElementById("compareForm");
  const list = document.getElementById("compareCandidates");
  if (!workbench || !form || !list) return;
  const endpoint = workbench.dataset.optionsUrl;
  const selectedReportIds = new Set(new URLSearchParams(window.location.search).getAll("report_ids"));
  const selectedIndustryCodes = new Set(new URLSearchParams(window.location.search).getAll("industry_codes"));

  const mode = () => new FormData(form).get("mode") || "company";
  const renderReports = (reports) => {
    if (!reports.length) {
      list.innerHTML = "<p class=\"muted-empty\">沒有符合條件的報告。</p>";
      return;
    }
    list.innerHTML = reports.map((report) => `
      <label class="candidate-row">
        <input type="checkbox" name="report_ids" value="${escapeHtml(report.id)}" ${selectedReportIds.has(String(report.id)) ? "checked" : ""}>
        <span><strong>${escapeHtml(report.company)} ${escapeHtml(report.year)}</strong><small>${escapeHtml(report.industry || "-")} · PR ${escapeHtml(report.pr || "-")} · ${escapeHtml(report.grade || "-")}</small></span>
      </label>
    `).join("");
  };
  const renderIndustries = (industries) => {
    if (!industries.length) {
      list.innerHTML = "<p class=\"muted-empty\">沒有符合條件的產業。</p>";
      return;
    }
    list.innerHTML = industries.map((industry) => `
      <label class="candidate-row">
        <input type="checkbox" name="industry_codes" value="${escapeHtml(industry.code)}" ${selectedIndustryCodes.has(String(industry.code)) ? "checked" : ""}>
        <span><strong>${escapeHtml(industry.code)} ${escapeHtml(industry.name)}</strong><small>${escapeHtml(industry.company_count)} 家公司 · ${escapeHtml(industry.report_count)} 份報告 · 平均 Raw ${escapeHtml(industry.average_raw_score)}</small></span>
      </label>
    `).join("");
  };
  const loadOptions = () => {
    const params = new URLSearchParams(new FormData(form));
    params.delete("report_ids");
    params.delete("industry_codes");
    fetch(`${endpoint}?${params.toString()}`, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((response) => response.json())
      .then((data) => {
        if (data.mode === "industry") {
          renderIndustries(data.industries || []);
        } else {
          renderReports(data.reports || []);
        }
      })
      .catch(() => {
        list.innerHTML = "<p class=\"muted-empty\">候選資料載入失敗。</p>";
      });
  };
  form.querySelectorAll("input, select").forEach((field) => {
    if (field.name === "report_ids" || field.name === "industry_codes") return;
    field.addEventListener(field.type === "text" ? "input" : "change", () => {
      window.clearTimeout(field._compareTimer);
      field._compareTimer = window.setTimeout(loadOptions, 180);
    });
  });
  loadOptions();
}

function initIntroStorytelling() {
  const root = document.querySelector(".intro-story");
  if (!root) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealItems = root.querySelectorAll(".intro-reveal, .story-chip, .metric-tile, .intro-data-card, .process-card, .data-bar");
  const counters = root.querySelectorAll("[data-counter]");
  const parallaxItems = root.querySelectorAll("[data-parallax]");
  const setCounterValue = (element, value) => {
    const suffix = element.dataset.suffix || "";
    element.textContent = `${Math.round(value)}${suffix}`;
  };
  const animateCounter = (element) => {
    if (element.dataset.counted === "true") return;
    element.dataset.counted = "true";
    const target = Number(element.dataset.counter || 0);
    if (reducedMotion) {
      setCounterValue(element, target);
      return;
    }
    const start = performance.now();
    const duration = 1100;
    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCounterValue(element, target * eased);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  };

  if (reducedMotion) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
    counters.forEach(animateCounter);
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      if (entry.target.matches("[data-counter]")) {
        animateCounter(entry.target);
      }
      entry.target.querySelectorAll("[data-counter]").forEach(animateCounter);
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -12% 0px", threshold: 0.16 });

  revealItems.forEach((item) => observer.observe(item));
  counters.forEach((counter) => observer.observe(counter));

  if (parallaxItems.length && window.matchMedia("(min-width: 1024px)").matches) {
    let ticking = false;
    const updateParallax = () => {
      const center = window.innerHeight / 2;
      parallaxItems.forEach((item) => {
        const rect = item.getBoundingClientRect();
        const speed = Number(item.dataset.parallax || 0);
        const offset = (rect.top + rect.height / 2 - center) * speed;
        item.style.transform = `translateY(${Math.max(Math.min(offset, 28), -28)}px)`;
      });
      ticking = false;
    };
    window.addEventListener("scroll", () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateParallax);
    }, { passive: true });
    updateParallax();
  }
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
  initIndustryCharts();
  initCompareWorkbench();
  initIntroStorytelling();
});
