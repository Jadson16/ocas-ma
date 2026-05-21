"""
Gera indicadores.html — painel de análise estatística do OCAS-MA.
Consome data/indicadores.json produzido por compute_indicators.py.
"""

import json
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
IND_FILE = DATA_DIR / "indicadores.json"
OUT_FILE = ROOT / "indicadores.html"

MESES_PT = ["","Jan.","Fev.","Mar.","Abr.","Mai.","Jun.","Jul.","Ago.","Set.","Out.","Nov.","Dez."]


def build_html(ind_data: dict) -> str:
    meta        = ind_data["meta"]
    municipios  = ind_data["municipios"]
    produtos    = ind_data["produtos"]
    indicadores = ind_data["indicadores"]

    anos        = meta["anos_disponiveis"]
    janela      = meta["tcg_janela_anos"]
    now         = datetime.now()
    update_date = f"{MESES_PT[now.month]} {now.year}"

    produtos_json  = json.dumps(produtos,    ensure_ascii=False, separators=(",", ":"))
    municipios_json = json.dumps(municipios, ensure_ascii=False, separators=(",", ":"))
    ind_json       = json.dumps(indicadores, ensure_ascii=False, separators=(",", ":"))
    anos_json      = json.dumps(anos,        separators=(",", ":"))

    # Selectores de cadeia agrupados por grupo
    groups: dict[str, list] = {}
    for k, v in produtos.items():
        groups.setdefault(v["grupo"], []).append((k, v["label"]))
    prod_options_parts = []
    for g, items in groups.items():
        prod_options_parts.append(f'<optgroup label="{g}">')
        for k, label in items:
            prod_options_parts.append(f'  <option value="{k}">{label}</option>')
        prod_options_parts.append('</optgroup>')
    prod_options = "\n".join(prod_options_parts)

    first_key = next(iter(produtos))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCAS-MA — Indicadores</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cpolygon points='32,4 56,18 56,46 32,60 8,46 8,18' fill='none' stroke='%232D6A4F' stroke-width='2.5'/%3E%3Ccircle cx='32' cy='32' r='7' fill='%2352B788'/%3E%3C/svg%3E">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
    :root {{
      --ocas-floresta: #1B4332; --ocas-mata: #2D6A4F; --ocas-igapo: #40916C;
      --ocas-babacu: #52B788; --ocas-buriti: #74C69D; --ocas-varzea: #D8F3DC;
      --ocas-bg-page: #F7FAF8; --ocas-bg-header: #ffffff; --ocas-bg-card: #ffffff;
      --ocas-bg-nav: #F7FAF8; --ocas-border: #ddeee5; --ocas-border-soft: #c8e0d0;
      --ocas-cerrado: #C9A84C; --ocas-rio: #2C6E8A;
      --ocas-font-titulo: Georgia,'Times New Roman',serif;
      --ocas-font-label: 'Courier New',Courier,monospace;
      --ocas-font-dados: system-ui,-apple-system,sans-serif;
      --ocas-radius-sm: 6px; --ocas-radius-md: 10px;
      --ocas-shadow-card: 0 1px 3px rgba(27,67,50,.06);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--ocas-bg-page); font-family: var(--ocas-font-dados); color: #222; }}

    /* HEADER */
    .ocas-header {{ background: var(--ocas-bg-header); border-bottom: 1px solid var(--ocas-border); padding: 18px 28px; }}
    .ocas-header-inner {{ display: flex; align-items: center; justify-content: space-between; max-width: 1400px; margin: 0 auto; }}
    .ocas-brand {{ display: flex; align-items: center; gap: 16px; text-decoration: none; }}
    .ocas-brand-text {{ display: flex; flex-direction: column; gap: 2px; }}
    .ocas-sigla {{ font-family: var(--ocas-font-titulo); font-size: 22px; font-weight: 700; color: var(--ocas-floresta); letter-spacing: 1px; line-height: 1; }}
    .ocas-vinculo {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: var(--ocas-igapo); }}
    .ocas-header-right {{ display: flex; align-items: center; gap: 20px; }}
    .ocas-header-logos {{ display: flex; align-items: center; gap: 14px; padding-right: 20px; border-right: 1px solid var(--ocas-border); }}
    .ocas-header-logos img {{ height: 48px; width: auto; object-fit: contain; opacity: .88; }}
    @media (max-width: 700px) {{ .ocas-header-logos {{ display: none; }} }}
    .ocas-header-meta {{ font-family: var(--ocas-font-label); font-size: 10px; color: var(--ocas-igapo); text-align: right; line-height: 1.8; }}

    /* NAV */
    .ocas-nav {{ background: var(--ocas-bg-nav); border-bottom: 1px solid var(--ocas-border); display: flex; padding: 0 28px; overflow-x: auto; }}
    .ocas-nav-item {{ padding: 10px 16px; font-family: var(--ocas-font-label); font-size: 11px; letter-spacing: .5px; color: var(--ocas-buriti); text-decoration: none; border-bottom: 2px solid transparent; transition: color .2s,border-color .2s; white-space: nowrap; }}
    .ocas-nav-item:hover {{ color: var(--ocas-mata); }}
    .ocas-nav-item.active {{ color: var(--ocas-mata); border-bottom-color: var(--ocas-mata); }}

    /* LAYOUT */
    .ocas-section {{ max-width: 1400px; margin: 0 auto; padding: 24px 28px; }}
    .ocas-section-title {{ font-family: var(--ocas-font-titulo); font-size: 18px; color: var(--ocas-floresta); margin-bottom: 4px; }}
    .ocas-section-sub {{ font-size: 12px; color: var(--ocas-buriti); margin-bottom: 20px; font-family: var(--ocas-font-label); }}

    /* CONTROLS */
    .ocas-controls {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; margin-bottom: 20px; background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); padding: 16px 20px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-control-group {{ display: flex; flex-direction: column; gap: 5px; }}
    .ocas-control-label {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); }}
    .ocas-select {{ font-family: var(--ocas-font-dados); font-size: 13px; color: var(--ocas-floresta); background: var(--ocas-bg-card); border: 1px solid var(--ocas-border-soft); border-radius: var(--ocas-radius-sm); padding: 7px 12px; cursor: pointer; outline: none; }}
    .ocas-select:focus {{ border-color: var(--ocas-mata); }}
    .ocas-slider-wrap {{ flex: 1; min-width: 200px; }}
    .ocas-year-display {{ font-family: var(--ocas-font-titulo); font-size: 22px; font-weight: 500; color: var(--ocas-floresta); margin-bottom: 4px; }}
    .ocas-slider {{ width: 100%; accent-color: var(--ocas-mata); cursor: pointer; }}
    .ocas-slider-labels {{ display: flex; justify-content: space-between; font-family: var(--ocas-font-label); font-size: 9px; color: var(--ocas-buriti); margin-top: 2px; }}

    /* CARDS */
    .ocas-cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 12px; margin-bottom: 20px; }}
    .ocas-card {{ background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); border-left: 3px solid var(--ocas-mata); padding: 16px 18px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-card-label {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); margin-bottom: 6px; }}
    .ocas-card-value {{ font-family: var(--ocas-font-titulo); font-size: 26px; font-weight: 500; color: var(--ocas-floresta); line-height: 1.1; }}
    .ocas-card-desc {{ font-family: var(--ocas-font-dados); font-size: 10px; color: var(--ocas-buriti); margin-top: 4px; }}

    /* CHARTS */
    .ocas-charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 960px) {{ .ocas-charts-grid {{ grid-template-columns: 1fr; }} }}
    .ocas-chart-card {{ background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); padding: 16px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-chart-title {{ font-family: var(--ocas-font-label); font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: var(--ocas-igapo); margin-bottom: 12px; }}
    .ocas-chart-container {{ width: 100%; }}
    .ocas-fonte {{ font-family: var(--ocas-font-label); font-size: 9px; color: var(--ocas-buriti); margin-top: 8px; text-align: right; }}

    /* NOTA */
    .ocas-nota {{ background: var(--ocas-varzea); border: 1px solid var(--ocas-border); border-radius: var(--ocas-radius-md); padding: 14px 18px; font-size: 12px; color: #444; line-height: 1.6; margin-top: 24px; }}
    .ocas-nota strong {{ color: var(--ocas-floresta); }}
  </style>
</head>
<body>

<!-- HEADER -->
<header class="ocas-header">
  <div class="ocas-header-inner">
    <a href="index.html" class="ocas-brand" style="text-decoration:none">
      <svg width="36" height="36" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <polygon points="32,4 56,18 56,46 32,60 8,46 8,18" stroke="#2D6A4F" stroke-width="2.5"/>
        <circle cx="32" cy="32" r="7" fill="#52B788"/>
      </svg>
      <div class="ocas-brand-text">
        <span class="ocas-sigla">OCAS-MA</span>
        <span class="ocas-vinculo">GEIA &middot; CECON &middot; UFMA</span>
      </div>
    </a>
    <div class="ocas-header-right">
      <div class="ocas-header-logos">
        <img src="assets/logo_geia.png" alt="GEIA">
        <img src="assets/logo_ufma.png" alt="UFMA">
      </div>
      <div class="ocas-header-meta">
        INDICADORES QUANTITATIVOS<br>
        Atualizado: {update_date}
      </div>
    </div>
  </div>
</header>

<!-- NAV -->
<nav class="ocas-nav">
  <a href="index.html"       class="ocas-nav-item">Cadeias</a>
  <a href="indicadores.html" class="ocas-nav-item active">Indicadores</a>
  <a href="index.html#sobre"       class="ocas-nav-item">O que &eacute;</a>
  <a href="index.html#equipe"      class="ocas-nav-item">Quem somos</a>
  <a href="index.html#metodologia" class="ocas-nav-item">Metodologia</a>
  <a href="index.html#boletins"    class="ocas-nav-item">Boletins</a>
  <a href="index.html#contato"     class="ocas-nav-item">Fale conosco</a>
</nav>

<!-- MAIN -->
<main class="ocas-section">
  <h2 class="ocas-section-title">Indicadores de especialização e dinamismo</h2>
  <p class="ocas-section-sub">
    QL &middot; PR &middot; TCG &middot; IDM &mdash; unidade de análise: município do Maranhão
  </p>

  <!-- CONTROLES -->
  <div class="ocas-controls">
    <div class="ocas-control-group">
      <span class="ocas-control-label">Cadeia produtiva</span>
      <select id="sel-produto" class="ocas-select" onchange="update()">
        {prod_options}
      </select>
    </div>
    <div class="ocas-slider-wrap">
      <span class="ocas-control-label">Ano de referência</span>
      <div class="ocas-year-display" id="year-display">{anos[-1]}</div>
      <input type="range" class="ocas-slider" id="year-slider"
             min="{anos[0]}" max="{anos[-1]}" value="{anos[-1]}" step="1"
             oninput="document.getElementById('year-display').textContent=this.value; update()">
      <div class="ocas-slider-labels"><span>{anos[0]}</span><span>{anos[-1]}</span></div>
    </div>
  </div>

  <!-- CARDS -->
  <div class="ocas-cards-grid">
    <div class="ocas-card">
      <div class="ocas-card-label">QL máximo</div>
      <div class="ocas-card-value" id="card-ql-max">—</div>
      <div class="ocas-card-desc" id="card-ql-max-mun">município líder</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">Municípios ativos (QL &gt; 1)</div>
      <div class="ocas-card-value" id="card-n-esp">—</div>
      <div class="ocas-card-desc">especializados na cadeia</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">TCG estadual ({janela} anos)</div>
      <div class="ocas-card-value" id="card-tcg-est">—</div>
      <div class="ocas-card-desc">% a.a. — média do MA</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">Municípios dinâmicos (IDM &gt; 1)</div>
      <div class="ocas-card-value" id="card-n-din">—</div>
      <div class="ocas-card-desc">crescem acima da média estadual</div>
    </div>
  </div>

  <!-- GRÁFICOS -->
  <div class="ocas-charts-grid">
    <!-- Ranking QL -->
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Ranking — Quociente Locacional (QL)</div>
      <div class="ocas-chart-container" id="chart-ranking" style="height:340px"></div>
      <div class="ocas-fonte">QL &gt; 1: especializado · QL &gt; 1,25: candidato a APL</div>
    </div>
    <!-- Scatter QL × TCG -->
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Posicionamento — QL × TCG ({janela} anos)</div>
      <div class="ocas-chart-container" id="chart-scatter" style="height:340px"></div>
      <div class="ocas-fonte">Quadrante I: líder consolidado · II: emergente · III: periférico · IV: em retração</div>
    </div>
    <!-- Evolução PR -->
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Participação Relativa (PR) — top 10 municípios</div>
      <div class="ocas-chart-container" id="chart-pr" style="height:300px"></div>
      <div class="ocas-fonte">% da produção estadual (base: valor)</div>
    </div>
    <!-- Evolução TCG -->
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Índice de Dinamismo Municipal (IDM) — top 10</div>
      <div class="ocas-chart-container" id="chart-idm" style="height:300px"></div>
      <div class="ocas-fonte">IDM &gt; 1: cresce acima da média estadual · janela: {janela} anos</div>
    </div>
  </div>

  <!-- NOTA METODOLÓGICA -->
  <div class="ocas-nota">
    <strong>Notas metodológicas</strong><br>
    <strong>QL</strong> (Quociente Locacional): razão entre a participação do município na cadeia e sua participação na produção agrícola total do estado.
    QL &gt; 1 indica especialização; QL &gt; 1,25 é referência para identificação de APLs.<br>
    <strong>PR</strong> (Participação Relativa): fatia do município no valor total estadual da cadeia, em %.<br>
    <strong>TCG</strong> (Taxa de Crescimento Geométrica): taxa anual de crescimento do valor da produção em janela de {janela} anos.<br>
    <strong>IDM</strong> (Índice de Dinamismo Municipal): razão entre o TCG do município e o TCG estadual da mesma cadeia.
    IDM &gt; 1 indica que o município cresce mais rápido que a média do estado.<br>
    Todos os indicadores são calculados com base no <em>valor da produção</em> (mil R$), que permite comparabilidade entre cadeias.
    Rebanhos (sem valor monetário na PPM) são excluídos do QL, PR, TCG e IDM.
  </div>
</main>

<script>
const PRODUTOS    = {produtos_json};
const MUNICIPIOS  = {municipios_json};
const IND        = {ind_json};
const ANOS_DISP  = {anos_json};
const TCG_JANELA = {janela};

const PALETTE = [
  "#2D6A4F","#40916C","#52B788","#C9A84C","#2C6E8A",
  "#74C69D","#1B4332","#B7E4C7","#8B5E3C","#6B9080",
];

function getAno() {{ return parseInt(document.getElementById("year-slider").value); }}
function getProd() {{ return document.getElementById("sel-produto").value; }}

function fmt(v, dec=2) {{
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(dec).replace(".", ",");
}}

function update() {{
  const prod = getProd();
  const ano  = getAno();
  const anoS = String(ano);

  const ql_map  = (IND.ql[prod]  || {{}})[anoS] || {{}};
  const pr_map  = (IND.pr[prod]  || {{}})[anoS] || {{}};
  const tcg_map = (IND.tcg[prod] || {{}})[anoS] || {{}};
  const idm_map = (IND.idm[prod] || {{}})[anoS] || {{}};

  // --- CARDS ---
  const ql_entries = Object.entries(ql_map).filter(([,v]) => v != null);
  if (ql_entries.length) {{
    const [top_mid, top_ql] = ql_entries.reduce((a,b) => b[1]>a[1] ? b : a);
    document.getElementById("card-ql-max").textContent = fmt(top_ql);
    document.getElementById("card-ql-max-mun").textContent = MUNICIPIOS[top_mid] || top_mid;
  }} else {{
    document.getElementById("card-ql-max").textContent = "—";
    document.getElementById("card-ql-max-mun").textContent = "sem dados";
  }}

  const n_esp = ql_entries.filter(([,v]) => v > 1).length;
  document.getElementById("card-n-esp").textContent = n_esp;

  // TCG estadual: mediana dos TCGs municipais como proxy
  const tcg_vals = Object.values(tcg_map).filter(v => v != null);
  const tcg_est  = tcg_vals.length
    ? tcg_vals.reduce((a,b)=>a+b,0) / tcg_vals.length
    : null;
  document.getElementById("card-tcg-est").textContent =
    tcg_est != null ? fmt(tcg_est * 100, 1) + "%" : "—";

  const n_din = Object.values(idm_map).filter(v => v != null && v > 1).length;
  document.getElementById("card-n-din").textContent = n_din;

  // --- RANKING QL ---
  const ql_sorted = ql_entries.sort((a,b) => b[1]-a[1]).slice(0,15);
  const ql_nomes  = ql_sorted.map(([mid]) => MUNICIPIOS[mid] || mid);
  const ql_vals   = ql_sorted.map(([,v]) => v);
  const ql_colors = ql_vals.map(v => v >= 1.25 ? "#2D6A4F" : v >= 1 ? "#52B788" : "#B7E4C7");

  Plotly.react("chart-ranking", [{{
    type: "bar", orientation: "h",
    x: ql_vals.slice().reverse(), y: ql_nomes.slice().reverse(),
    marker: {{ color: ql_colors.slice().reverse() }},
    hovertemplate: "%{{y}}<br>QL: %{{x:.3f}}<extra></extra>",
  }}], {{
    margin: {{ l: 160, r: 20, t: 10, b: 30 }},
    xaxis: {{ title: "QL", zeroline: true, zerolinecolor:"#ccc" }},
    yaxis: {{ automargin: true }},
    shapes: [
      {{ type:"line", x0:1, x1:1, y0:-0.5, y1:ql_vals.length-0.5,
         line:{{ color:"#C9A84C", width:1.5, dash:"dot" }} }},
      {{ type:"line", x0:1.25, x1:1.25, y0:-0.5, y1:ql_vals.length-0.5,
         line:{{ color:"#2D6A4F", width:1.5, dash:"dash" }} }},
    ],
    paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font: {{ family:"system-ui", size:11 }},
  }}, {{responsive:true}});

  // --- SCATTER QL × TCG ---
  const scatter_mids = Object.keys(ql_map).filter(mid => tcg_map[mid] != null);
  const sx = scatter_mids.map(mid => ql_map[mid]);
  const sy = scatter_mids.map(mid => tcg_map[mid] * 100);
  const sn = scatter_mids.map(mid => MUNICIPIOS[mid] || mid);
  const sc = scatter_mids.map(mid => {{
    const q = ql_map[mid] >= 1, d = tcg_map[mid] >= 0;
    return q && d ? "#2D6A4F" : !q && d ? "#C9A84C" : q && !d ? "#2C6E8A" : "#aaa";
  }});

  const ql_med  = sx.length ? sx.reduce((a,b)=>a+b,0)/sx.length : 1;
  const tcg_med = sy.length ? sy.reduce((a,b)=>a+b,0)/sy.length : 0;

  Plotly.react("chart-scatter", [{{
    type:"scatter", mode:"markers",
    x: sx, y: sy, text: sn,
    marker: {{ color: sc, size: 7, opacity: 0.8 }},
    hovertemplate: "%{{text}}<br>QL: %{{x:.3f}}<br>TCG: %{{y:.1f}}%<extra></extra>",
  }}], {{
    margin: {{ l:50, r:20, t:10, b:40 }},
    xaxis: {{ title:"QL", zeroline:false }},
    yaxis: {{ title:"TCG (% a.a.)", zeroline:true, zerolinecolor:"#ddd" }},
    shapes: [
      {{ type:"line", x0:1, x1:1, y0:0, y1:1, yref:"paper",
         line:{{ color:"#C9A84C", width:1, dash:"dot"}} }},
      {{ type:"line", x0:0, x1:1, xref:"paper", y0:tcg_med, y1:tcg_med,
         line:{{ color:"#2C6E8A", width:1, dash:"dot"}} }},
    ],
    paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font: {{ family:"system-ui", size:11 }},
  }}, {{responsive:true}});

  // --- PR evolução série histórica top 10 ---
  const pr_anos_disp = Object.keys(IND.pr[prod] || {{}}).map(Number).sort();
  // Top 10 municípios pelo PR no ano selecionado
  const pr_cur = (IND.pr[prod] || {{}})[anoS] || {{}};
  const top10  = Object.entries(pr_cur).sort((a,b)=>b[1]-a[1]).slice(0,10).map(([mid])=>mid);
  const pr_traces = top10.map((mid, i) => {{
    const xs = [], ys = [];
    pr_anos_disp.forEach(a => {{
      const v = ((IND.pr[prod] || {{}})[String(a)] || {{}})[mid];
      if (v != null) {{ xs.push(a); ys.push(v); }}
    }});
    return {{ type:"scatter", mode:"lines", name: MUNICIPIOS[mid]||mid,
              x:xs, y:ys, line:{{ color:PALETTE[i%PALETTE.length], width:1.5 }},
              hovertemplate:"%{{fullData.name}}<br>%{{x}}: %{{y:.2f}}%<extra></extra>" }};
  }});
  Plotly.react("chart-pr", pr_traces, {{
    margin:{{l:50,r:20,t:10,b:30}},
    xaxis:{{ title:"Ano" }},
    yaxis:{{ title:"PR (%)" }},
    legend:{{ font:{{size:9}}, orientation:"v" }},
    paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{{ family:"system-ui", size:11 }},
  }}, {{responsive:true}});

  // --- IDM top 10 ---
  const idm_entries = Object.entries(idm_map).filter(([,v]) => v != null).sort((a,b)=>b[1]-a[1]).slice(0,12);
  const idm_nomes   = idm_entries.map(([mid])=> MUNICIPIOS[mid]||mid);
  const idm_vals    = idm_entries.map(([,v])=>v);
  const idm_colors  = idm_vals.map(v => v>=1 ? "#2D6A4F" : "#2C6E8A");

  Plotly.react("chart-idm", [{{
    type:"bar", orientation:"h",
    x: idm_vals.slice().reverse(), y: idm_nomes.slice().reverse(),
    marker:{{ color: idm_colors.slice().reverse() }},
    hovertemplate:"%{{y}}<br>IDM: %{{x:.3f}}<extra></extra>",
  }}], {{
    margin:{{l:160,r:20,t:10,b:30}},
    xaxis:{{ title:"IDM", zeroline:true }},
    yaxis:{{ automargin:true }},
    shapes:[{{ type:"line", x0:1, x1:1, y0:-0.5, y1:idm_vals.length-0.5,
               line:{{ color:"#C9A84C", width:1.5, dash:"dot"}} }}],
    paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{{ family:"system-ui", size:11 }},
  }}, {{responsive:true}});
}}

// inicializa
document.getElementById("sel-produto").value = "{first_key}";
update();
</script>
</body>
</html>"""


def main() -> None:
    if not IND_FILE.exists():
        print(f"ERRO: {IND_FILE} não encontrado. Execute compute_indicators.py primeiro.")
        raise SystemExit(1)

    ind_data = json.loads(IND_FILE.read_text(encoding="utf-8"))
    html = build_html(ind_data)
    OUT_FILE.write_text(html, encoding="utf-8")
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"Painel salvo : {OUT_FILE}")
    print(f"Tamanho      : {size_kb:.0f} KB")
    print(f"Produtos     : {len(ind_data['produtos'])}")


if __name__ == "__main__":
    main()
