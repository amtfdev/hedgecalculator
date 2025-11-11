
function fmt(n, dp=2) {
  if (isNaN(n)) return "";
  return Number(n).toLocaleString(undefined, {maximumFractionDigits: dp, minimumFractionDigits: dp});
}

function pct(a) {
  return (a >= 0 ? "+" : "") + fmt(a, 2) + "%";
}

function todayISO() {
  const d = new Date();
  return d.toISOString().slice(0,10);
}

function addOptionRow(values) {
  const container = document.getElementById("options-rows");
  const row = document.createElement("div");
  row.className = "row opt";

  const expiry = document.createElement("input");
  expiry.type = "date";
  expiry.value = (values && values.expiry) || todayISO();

  const strike = document.createElement("input");
  strike.type = "number"; strike.step = "0.01";
  strike.value = (values && values.strike) || "";

  const ask = document.createElement("input");
  ask.type = "number"; ask.step = "0.01";
  ask.value = (values && values.ask) || "";

  const premium = document.createElement("input");
  premium.type = "number"; premium.step = "0.01"; premium.readOnly = true;
  premium.value = "";

  const del = document.createElement("button");
  del.className = "secondary"; del.textContent = "×";
  del.title = "Remove row";
  del.onclick = () => { row.remove(); renderChart([]); document.getElementById('results').style.display='none'; };

  [expiry, strike, ask].forEach(el => el.addEventListener("input", () => {
    const m = Number(document.getElementById("multiplier").value || 0);
    premium.value = (Number(ask.value||0) * m).toFixed(2);
  }));

  // initial premium fill
  setTimeout(()=>{
    const m = Number(document.getElementById("multiplier").value || 0);
    premium.value = (Number(ask.value||0) * m).toFixed(2);
  },0);

  row.appendChild(expiry);
  row.appendChild(strike);
  row.appendChild(ask);
  row.appendChild(premium);
  row.appendChild(del);
  container.appendChild(row);
}

function collectInputs() {
  const currency = document.getElementById("currency").value || "£";
  const index = document.getElementById("index").value || "";
  const multiplier = Number(document.getElementById("multiplier").value || 0);
  const notional = Number(document.getElementById("notional").value || 0);
  const spot = Number(document.getElementById("spot").value || 0);

  const rows = Array.from(document.querySelectorAll("#options-rows .row.opt"));
  const options = rows.map(r => {
    const [e, k, a, p] = r.querySelectorAll("input");
    return {
      expiry: e.value,
      strike: Number(k.value || 0),
      ask: Number(a.value || 0),
      premium: Number(p.value || 0)
    };
  }).filter(o => o.expiry && o.strike>0);

  return { currency, index, multiplier, notional, spot, options };
}

function calcSolutions(inputs) {
  const { multiplier, notional } = inputs;
  return inputs.options.map(o => {
    const perContractNotional = o.strike * multiplier;
    const qty100 = perContractNotional > 0 ? (notional / perContractNotional) : 0;
    const qty50 = qty100 * 0.5;
    const qty10 = qty100 * 0.1;
    const cost100 = o.premium * qty100;
    const cost50 = o.premium * qty50;
    const cost10 = o.premium * qty10;
    const atmPct = ((o.strike - inputs.spot) / inputs.spot) * 100;
    return {
      ...o,
      perContractNotional,
      atmPct,
      qty100, qty50, qty10,
      qty100_floor: Math.floor(qty100),
      qty100_ceil: Math.ceil(qty100),
      cost100, cost50, cost10,
    };
  }).sort((a,b) => new Date(a.expiry) - new Date(b.expiry));
}

function renderTable(inputs, solutions) {
  if (solutions.length === 0) {
    document.getElementById("results").style.display = "none";
    return;
  }
  document.getElementById("results").style.display = "";
  const c = inputs.currency;
  const rows = solutions.map(s => `
    <tr>
      <td>${s.expiry}</td>
      <td style="text-align:right">${fmt(s.strike,2)}</td>
      <td style="text-align:right">${fmt(s.ask,2)}</td>
      <td style="text-align:right">${fmt(s.premium,2)}</td>
      <td style="text-align:right">${fmt(s.perContractNotional,0)}</td>
      <td style="text-align:right">${fmt(s.qty100,3)} <span class="small">(ceil ${s.qty100_ceil}, floor ${s.qty100_floor})</span></td>
      <td style="text-align:right">${fmt(s.qty50,3)}</td>
      <td style="text-align:right">${fmt(s.qty10,3)}</td>
      <td style="text-align:right">${c}${fmt(s.cost100,2)}</td>
      <td style="text-align:right">${c}${fmt(s.cost50,2)}</td>
      <td style="text-align:right">${c}${fmt(s.cost10,2)}</td>
      <td><span class="badge">${pct(s.atmPct)}</span></td>
    </tr>
  `).join("");

  const html = `
    <div class="small" style="margin-bottom:8px;">
      Notional: <b>${c}${fmt(inputs.notional,0)}</b> • Multiplier: <b>${fmt(inputs.multiplier,0)}</b> • Spot: <b>${fmt(inputs.spot,2)}</b>
    </div>
    <table>
      <thead>
        <tr>
          <th>Expiry</th><th>Strike</th><th>Ask</th><th>Premium</th>
          <th>Notional/Contract</th>
          <th>Qty (100%)</th><th>Qty (50%)</th><th>Qty (10%)</th>
          <th>Cost (100%)</th><th>Cost (50%)</th><th>Cost (10%)</th>
          <th>% from Spot</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  document.getElementById("results-table").innerHTML = html;
}

function renderChart(solutions, inputs) {
  const el = document.getElementById("chart");
  if (!inputs) {
    Plotly.purge(el);
    return;
  }

  const x = solutions.map(s => s.expiry);
  const y = solutions.map(s => s.strike);
  const labels = solutions.map(s => `Strike ${fmt(s.strike)} (${pct(s.atmPct)})<br>Ask ${fmt(s.ask)} • Prem ${fmt(s.premium)}<br>Expiry ${s.expiry}`);

  // Scatter points for strike at each expiry
  const points = {
    x, y, type: 'scatter', mode: 'markers+text',
    text: solutions.map(s => fmt(s.strike,0)),
    textposition: 'top center',
    hovertemplate: '%{text}<br>%{x}<extra></extra>',
    name: 'Strikes'
  };

  // Horizontal line at spot
  const spot = (inputs && inputs.spot) || 0;
  const spotLine = {
    x: x.length ? [x[0], x[x.length-1]] : [new Date().toISOString().slice(0,10), new Date().toISOString().slice(0,10)],
    y: [spot, spot],
    mode: 'lines',
    name: 'Spot',
    hoverinfo: 'skip'
  };

  // Vertical shapes at expiry
  const shapes = solutions.map(s => ({
    type: 'line',
    x0: s.expiry,
    x1: s.expiry,
    y0: Math.min(spot, ...y) * 0.8,
    y1: Math.max(spot, ...y) * 1.2,
    line: { dash: 'dot', width: 1 }
  }));

  const annotations = solutions.map(s => ({
    x: s.expiry, y: s.strike,
    text: `${fmt(s.strike)} (${pct(s.atmPct)})`,
    showarrow: true, arrowhead: 2, ax: 0, ay: -30, font: {size: 11}
  }));

  const layout = {
    margin: {l: 60, r: 20, t: 20, b: 60},
    xaxis: { title: 'Expiry', type: 'date' },
    yaxis: { title: 'Index Level', rangemode: 'tozero' },
    shapes,
    annotations,
    hovermode: 'closest',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)'
  };

  Plotly.newPlot(el, [spotLine, points], layout, {displaylogo: false, responsive: true});
}

function calculate() {
  const inputs = collectInputs();
  const solutions = calcSolutions(inputs);
  renderTable(inputs, solutions);
  renderChart(solutions, inputs);
}

function resetAll() {
  document.getElementById("currency").value = "£";
  document.getElementById("index").value = "FTSE 100";
  document.getElementById("multiplier").value = "10";
  document.getElementById("notional").value = "100000";
  document.getElementById("spot").value = "9500";
  document.getElementById("options-rows").innerHTML = "";
  addOptionRow({ expiry: todayISO(), strike: 9000, ask: 20 });
  addOptionRow({ expiry: (new Date(Date.now()+30*24*3600*1000)).toISOString().slice(0,10), strike: 9200, ask: 60 });
  addOptionRow({ expiry: (new Date(Date.now()+60*24*3600*1000)).toISOString().slice(0,10), strike: 9300, ask: 90 });
  document.getElementById('results').style.display = 'none';
  renderChart([], collectInputs());
}

document.getElementById("add-row").addEventListener("click", () => addOptionRow());
document.getElementById("calculate").addEventListener("click", calculate);
document.getElementById("reset").addEventListener("click", resetAll);

// Seed with three example rows
resetAll();
