/**
 * DistrictDesk — Chart.js dashboard (Phase 6).
 * Reads JSON from <script type="application/json" id="dashboard-data">.
 */
(function () {
  'use strict';

  var el = document.getElementById('dashboard-data');
  if (!el || typeof Chart === 'undefined') {
    return;
  }

  var payload;
  try {
    payload = JSON.parse(el.textContent);
  } catch (e) {
    return;
  }

  var cd = payload.chart_data || {};
  var accent = getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() || '#1e5a8a';
  var muted = '#5c6370';
  var border = '#e2e5eb';

  function barChart(canvasId, labels, data, opts) {
    var ctx = document.getElementById(canvasId);
    if (!ctx || !labels || !data) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: opts && opts.label ? opts.label : 'Count',
            data: data,
            backgroundColor: accent + '99',
            borderColor: accent,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
            grid: { color: border },
          },
          x: {
            grid: { display: false },
            ticks: { maxRotation: 45, minRotation: 0 },
          },
        },
      },
    });
  }

  function lineChart(canvasId, labels, data) {
    var ctx = document.getElementById(canvasId);
    if (!ctx || !labels || !data) return;
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'New tickets',
            data: data,
            fill: true,
            backgroundColor: accent + '33',
            borderColor: accent,
            tension: 0.2,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
            grid: { color: border },
          },
          x: {
            grid: { color: border },
          },
        },
      },
    });
  }

  function doughnutChart(canvasId, labels, data) {
    var ctx = document.getElementById(canvasId);
    if (!ctx || !labels || !data) return;
    var palette = [
      accent,
      '#2d6a4f',
      '#bc6c25',
      '#6c757d',
      '#457b9d',
      '#7b2cbf',
      '#e63946',
    ];
    var colors = labels.map(function (_, i) {
      return palette[i % palette.length];
    });
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: colors.map(function (c) {
              return c + 'cc';
            }),
            borderColor: colors,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: muted, boxWidth: 12 },
          },
        },
      },
    });
  }

  var ts = cd.tickets_by_status || {};
  barChart('chart-tickets-status', ts.labels, ts.counts, { label: 'Tickets' });

  var tc = cd.tickets_by_category || {};
  barChart('chart-tickets-category', tc.labels, tc.counts, { label: 'Tickets' });

  var tr = cd.tickets_trend || {};
  lineChart('chart-tickets-trend', tr.labels, tr.counts);

  var dt = cd.devices_by_type || {};
  doughnutChart('chart-devices-type', dt.labels, dt.counts);

  var ds = cd.devices_by_status || {};
  doughnutChart('chart-devices-status', ds.labels, ds.counts);
})();
