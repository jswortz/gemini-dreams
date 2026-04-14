import './style.css'

document.querySelector('#app').innerHTML = `
  <div class="container">
    <header>
      <h1>🌙 Gemini Nightly Dream Dashboard</h1>
      <p>Metrics and epiphanies generated from self-aware agent sessions.</p>
    </header>

    <main>
      <section class="card" id="coverage-section">
        <h2>1. Skill Evaluation Coverage</h2>
        <div id="coverage-content">Loading...</div>
      </section>

      <section class="card" id="dreams-section">
        <h2>2. Dream Epiphanies & Token Waste Analysis</h2>
        <div id="dreams-content">Loading...</div>
      </section>
    </main>
  </div>
`

async function fetchCoverage() {
  try {
    const response = await fetch('http://localhost:8000/api/coverage');
    const data = await response.json();
    renderCoverage(data);
  } catch (error) {
    document.querySelector('#coverage-content').innerHTML = `<p class="error">Failed to load coverage data.</p>`;
  }
}

async function fetchDreams() {
  try {
    const response = await fetch('http://localhost:8000/api/dreams');
    const data = await response.json();
    renderDreams(data);
  } catch (error) {
    document.querySelector('#dreams-content').innerHTML = `<p class="error">Failed to load dream data.</p>`;
  }
}

function renderCoverage(data) {
  if (!data || data.length === 0) {
    document.querySelector('#coverage-content').innerHTML = `<p>No coverage data available.</p>`;
    return;
  }
  
  // Deduplicate to show latest state per skill
  const latest = {};
  data.forEach(row => {
    if (!latest[row.skill_name]) {
      latest[row.skill_name] = row;
    }
  });
  
  const rows = Object.values(latest).map(row => `
    <tr>
      <td>${row.skill_name}</td>
      <td class="${row.has_evals ? 'pass' : 'fail'}">${row.has_evals ? 'Yes' : 'No'}</td>
    </tr>
  `).join('');

  document.querySelector('#coverage-content').innerHTML = `
    <div class="stats">
      <div class="stat-item">
        <span class="stat-value">${Object.keys(latest).length}</span>
        <span class="stat-label">Total Skills</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">${Object.values(latest).filter(r => r.has_evals).length}</span>
        <span class="stat-label">With Evals</span>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Skill Name</th>
          <th>Has Evals</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

function renderDreams(data) {
  if (!data || data.length === 0) {
    document.querySelector('#dreams-content').innerHTML = `<p>No dream sessions logged yet.</p>`;
    return;
  }

  const items = data.map(row => {
    let improvements = '';
    if (row.latency_before && row.latency_after) {
      const latDiff = (row.latency_before - row.latency_after).toFixed(1);
      const tokenDiff = row.tokens_before - row.tokens_after;
      improvements = `
        <div class="improvement-metrics">
          <div class="metric-chip">
            <span class="metric-label">Latency</span>
            <span class="metric-val">${row.latency_before}ms → ${row.latency_after}ms (-${latDiff}ms)</span>
          </div>
          <div class="metric-chip">
            <span class="metric-label">Tokens</span>
            <span class="metric-val">${row.tokens_before} → ${row.tokens_after} (-${tokenDiff})</span>
          </div>
        </div>
      `;
    }

    const skillUpdates = row.skill_updates ? `
      <div class="skill-update-badge">
        🚀 Skill Update: ${row.skill_updates}
      </div>
    ` : '';

    return `
      <div class="dream-item">
        <div class="dream-header">
          <h3>Session: ${row.session_id}</h3>
          <span>Turns: ${row.turn_count}</span>
        </div>
        ${skillUpdates}
        <div class="dream-body">
          <p><strong>Epiphany / Proposed Update:</strong></p>
          <pre>${row.epiphanies}</pre>
        </div>
        ${improvements}
        <div class="dream-footer">
          <small>${new Date(row.timestamp).toLocaleString()}</small>
        </div>
      </div>
    `;
  }).join('');

  document.querySelector('#dreams-content').innerHTML = items;
}

fetchCoverage();
fetchDreams();
