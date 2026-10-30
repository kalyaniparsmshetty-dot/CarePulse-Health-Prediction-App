document.addEventListener("DOMContentLoaded", function () {
  // Show / hide password
  document.querySelectorAll(".toggle-password").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.getElementById(btn.dataset.target);
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Hide" : "Show";
    });
  });

  // Confirm before delete / deactivate
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  // Mobile sidebar
  var menu = document.getElementById("menu-btn");
  if (menu) menu.addEventListener("click", function () {
    document.getElementById("sidebar").classList.toggle("open");
  });

  // DOB helper: inserts the slashes while typing (server still validates strictly)
  var dob = document.getElementById("dob");
  if (dob) dob.addEventListener("input", function () {
    var d = dob.value.replace(/[^0-9]/g, "").slice(0, 8), out = d.slice(0, 2);
    if (d.length > 2) out += "/" + d.slice(2, 4);
    if (d.length > 4) out += "/" + d.slice(4);
    dob.value = out;
  });

  // Charts (data comes from the database via the server)
  var dataEl = document.getElementById("chart-data");
  if (!dataEl || typeof Chart === "undefined") return;
  var charts = JSON.parse(dataEl.textContent);
  var palette = ["#0e8c87", "#2b6cb0", "#b7791f", "#c0392b", "#6b46c1", "#1f8a5b"];
  var colours = { glucose: "#0e8c87", haemoglobin: "#c0392b", cholesterol: "#2b6cb0", owners: "#0f2a43", signups: "#0e8c87" };
  document.querySelectorAll("canvas[data-chart]").forEach(function (canvas) {
    var c = charts[canvas.dataset.chart];
    if (!c || !c.data.length) {
      var p = document.createElement("p");
      p.className = "empty"; p.textContent = "No data yet.";
      canvas.parentNode.replaceChild(p, canvas); return;
    }
    var pie = c.type === "doughnut";
    new Chart(canvas, {
      type: c.type,
      data: { labels: c.labels, datasets: [{ label: c.label, data: c.data,
        backgroundColor: pie ? palette : colours[canvas.dataset.chart] || palette[0], borderRadius: pie ? 0 : 4 }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: pie, position: "bottom" } },
        scales: pie ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  });
});
