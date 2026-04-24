import './style.css'

const API = '';

// Escape HTML to prevent XSS from BQ data
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}

function setHTML(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

document.querySelector('#app').innerHTML = `
  <div class="container">
    <header>
      <h1>Gemini Dreams Dashboard</h1>
      <p>Eval scores, session analysis, and dream epiphanies over time.</p>
      <div id="stats-bar" class="stats-bar"></div>
    </header>

    <main>
      <section class="card card-wide">
        <h2>Eval Pass Rate Over Time</h2>
        <div class="chart-wrap"><canvas id="eval-chart"></canvas></div>
      </section>

      <section class="card card-wide">
        <h2>Sessions Analyzed Per Day</h2>
        <div class="chart-wrap"><canvas id="sessions-chart"></canvas></div>
      </section>

      <section class="card">
        <h2>Skill Evaluation Coverage</h2>
        <div id="coverage-content">Loading...</div>
      </section>

      <section class="card">
        <h2>Dream Epiphanies</h2>
        <div id="dreams-content">Loading...</div>
      </section>
    </main>
  </div>
`;

// --- Stats ---
async function fetchStats() {
  try {
    const res = await fetch(API + '/api/stats');
    const d = await res.json();
    setHTML('stats-bar', `
      <div class="stat-item"><span class="stat-value">${parseInt(d.total_sessions) || 0}</span><span class="stat-label">Total Logs</span></div>
      <div class="stat-item"><span class="stat-value">${parseInt(d.unique_sessions) || 0}</span><span class="stat-label">Sessions</span></div>
      <div class="stat-item"><span class="stat-value">${parseInt(d.claude_sessions) || 0}</span><span class="stat-label">Claude</span></div>
      <div class="stat-item"><span class="stat-value">${parseInt(d.gemini_sessions) || 0}</span><span class="stat-label">Gemini</span></div>
      <div class="stat-item"><span class="stat-value">${parseInt(d.router_sessions) || 0}</span><span class="stat-label">Router</span></div>
    `);
  } catch { /* ignore */ }
}

// --- Eval Chart ---
async function fetchEvalResults() {
  try {
    const res = await fetch(API + '/api/eval-results');
    const data = await res.json();
    if (!data.length) return;

    const byDate = {};
    data.forEach(r => {
      const day = r.timestamp?.slice(0, 10);
      if (!day) return;
      if (!byDate[day]) byDate[day] = { passed: 0, failed: 0 };
      byDate[day].passed += r.passed || 0;
      byDate[day].failed += r.failed || 0;
    });

    const labels = Object.keys(byDate).sort();
    const passRates = labels.map(d => {
      const t = byDate[d].passed + byDate[d].failed;
      return t > 0 ? Math.round((byDate[d].passed / t) * 100) : 0;
    });
    const passed = labels.map(d => byDate[d].passed);
    const failed = labels.map(d => byDate[d].failed);

    const ctx = document.getElementById('eval-chart');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Pass Rate %',
            data: passRates,
            borderColor: '#4ade80',
            backgroundColor: 'rgba(74, 222, 128, 0.1)',
            fill: true,
            tension: 0.3,
            yAxisID: 'y',
          },
          {
            label: 'Passed',
            data: passed,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            tension: 0.3,
            yAxisID: 'y1',
          },
          {
            label: 'Failed',
            data: failed,
            borderColor: '#f87171',
            backgroundColor: 'rgba(248, 113, 113, 0.1)',
            tension: 0.3,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: '#94a3b8' } },
        },
        scales: {
          x: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y: {
            type: 'linear',
            position: 'left',
            min: 0,
            max: 100,
            title: { display: true, text: 'Pass Rate %', color: '#94a3b8' },
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y1: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'Count', color: '#94a3b8' },
            ticks: { color: '#64748b' },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  } catch (e) {
    console.error('eval chart error', e);
  }
}

// --- Sessions Chart ---
async function fetchSessions() {
  try {
    const res = await fetch(API + '/api/sessions');
    const data = await res.json();
    renderDreams(data);
    if (!data.length) return;

    const byDate = {};
    data.forEach(r => {
      const day = r.timestamp?.slice(0, 10);
      if (!day) return;
      byDate[day] = (byDate[day] || 0) + 1;
    });

    const labels = Object.keys(byDate).sort();
    const counts = labels.map(d => byDate[d]);

    const ctx = document.getElementById('sessions-chart');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Sessions Analyzed',
          data: counts,
          backgroundColor: 'rgba(250, 204, 21, 0.6)',
          borderColor: '#facc15',
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8' } },
        },
        scales: {
          x: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y: {
            beginAtZero: true,
            ticks: { color: '#64748b', stepSize: 1 },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
      },
    });
  } catch (e) {
    console.error('sessions chart error', e);
  }
}

// --- Coverage ---
async function fetchCoverage() {
  try {
    const res = await fetch(API + '/api/coverage');
    const data = await res.json();
    renderCoverage(data);
  } catch {
    setHTML('coverage-content', '<p class="error">Failed to load coverage data.</p>');
  }
}

function renderCoverage(data) {
  if (!data?.length) {
    setHTML('coverage-content', '<p>No coverage data available.</p>');
    return;
  }
  const latest = {};
  data.forEach(row => { if (!latest[row.skill_name]) latest[row.skill_name] = row; });

  const skills = Object.values(latest);
  const withEvals = skills.filter(r => r.has_evals).length;

  const rows = skills.map(row => `
    <tr>
      <td>${esc(row.skill_name)}</td>
      <td class="${row.has_evals ? 'pass' : 'fail'}">${row.has_evals ? 'Yes' : 'No'}</td>
    </tr>
  `).join('');

  setHTML('coverage-content', `
    <div class="stats">
      <div class="stat-item">
        <span class="stat-value">${skills.length}</span>
        <span class="stat-label">Total Skills</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">${withEvals}</span>
        <span class="stat-label">With Evals</span>
      </div>
    </div>
    <table>
      <thead><tr><th>Skill Name</th><th>Has Evals</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `);
}

// --- Dreams / Epiphanies ---
function extractSkillFromEpiphany(text) {
  if (!text) return null;
  const match = text.match(/"new_skill_name"\s*:\s*"([^"]+)"/);
  return match ? match[1] : null;
}

function extractInsights(text) {
  if (!text) return [];
  const insights = [];
  const patterns = [
    { re: /EPIPHANY:?\s*(.+?)(?=\n|TOKEN|$)/gi, type: 'epiphany' },
    { re: /TOKEN\s*WASTE:?\s*(.+?)(?=\n|EPIPHANY|$)/gi, type: 'waste' },
  ];
  for (const { re, type } of patterns) {
    let m;
    while ((m = re.exec(text)) !== null) {
      insights.push({ type, text: m[1].trim() });
    }
  }
  return insights;
}

function renderDreams(data) {
  if (!data?.length) {
    setHTML('dreams-content', '<p>No dream sessions logged yet.</p>');
    return;
  }

  const skillCreations = data.filter(r => extractSkillFromEpiphany(r.epiphanies));
  let summaryHTML = '';
  if (skillCreations.length) {
    const skillNames = skillCreations.map(r => extractSkillFromEpiphany(r.epiphanies));
    summaryHTML = `
      <div class="skill-summary">
        <h3>Skills Created from Epiphanies</h3>
        <div class="skill-tags">
          ${skillNames.map(s => `<span class="skill-tag">${esc(s)}</span>`).join('')}
        </div>
        <p class="skill-summary-note">${skillNames.length} skill(s) auto-generated from dream analysis</p>
      </div>
    `;
  }

  const items = data.slice(0, 20).map(row => {
    const skillName = extractSkillFromEpiphany(row.epiphanies);
    const insights = extractInsights(row.epiphanies);
    const epiphanyText = esc(row.epiphanies || 'No epiphany recorded');

    const skillBadge = skillName
      ? `<div class="skill-update-badge">New Skill Created: ${esc(skillName)}</div>`
      : '';

    let insightsHTML = '';
    if (insights.length) {
      insightsHTML = `<div class="insights-list">${insights.map(i => `
        <div class="insight-chip ${i.type}">
          <span class="insight-icon">${i.type === 'epiphany' ? '\u{1F4A1}' : '\u{26A0}\u{FE0F}'}</span>
          <span>${esc(i.text.slice(0, 200))}</span>
        </div>
      `).join('')}</div>`;
    }

    const statusBadge = row.review_status
      ? `<span class="review-badge ${row.review_status === 'Pending Review' ? 'pending' : 'reviewed'}">${esc(row.review_status)}</span>`
      : '';

    return `
      <div class="dream-item ${skillName ? 'has-skill' : ''}">
        <div class="dream-header">
          <h3>${esc(row.session_id)}</h3>
          <div class="dream-meta">
            ${statusBadge}
            <span class="turn-badge">${parseInt(row.turn_count) || '?'} turns</span>
          </div>
        </div>
        ${skillBadge}
        ${insightsHTML}
        <details class="epiphany-details">
          <summary>Full Analysis</summary>
          <pre>${epiphanyText}</pre>
        </details>
        <div class="dream-footer"><small>${esc(new Date(row.timestamp).toLocaleString())}</small></div>
      </div>
    `;
  }).join('');

  setHTML('dreams-content', summaryHTML + items);
}

// Boot
fetchStats();
fetchEvalResults();
fetchSessions();
fetchCoverage();
