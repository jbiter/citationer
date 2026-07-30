async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function initDashboard() {
  try {
    const status = await fetchJson('/api/data/status');
    document.getElementById('status').textContent = `已导入 ${status.total_records} 条记录`;

    const overview = await fetchJson('/api/stats/overview');
    document.getElementById('overview-grid').innerHTML = `
      <div class="metric"><strong>${overview.total_records}</strong><span>记录数</span></div>
      <div class="metric"><strong>${overview.num_journals}</strong><span>期刊数</span></div>
      <div class="metric"><strong>${overview.num_authors}</strong><span>作者数</span></div>
      <div class="metric"><strong>${overview.h_index}</strong><span>H-index</span></div>
    `;

    const yearly = await fetchJson('/api/stats/yearly');
    const years = Object.keys(yearly.year_counts).map(Number).sort((a, b) => a - b);
    const counts = years.map(y => yearly.year_counts[y]);
    Plotly.newPlot('yearly-chart', [{
      x: years,
      y: counts,
      type: 'scatter',
      mode: 'lines+markers',
      fill: 'tozeroy',
    }], { margin: { t: 20 } });
  } catch (err) {
    document.getElementById('status').textContent = `错误：${err.message}`;
  }
}

initDashboard();
