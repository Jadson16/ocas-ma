"""
Gera apl.html — Boletim de Identificação de APLs do OCAS-MA.
Consome data/apl.json + data/indicadores.json (para labels).
"""

import json
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
APL_FILE = DATA_DIR / "apl.json"
IND_FILE = DATA_DIR / "indicadores.json"
OUT_FILE = ROOT / "apl.html"

MESES_PT = ["","Jan.","Fev.","Mar.","Abr.","Mai.","Jun.",
            "Jul.","Ago.","Set.","Out.","Nov.","Dez."]

CAT_LABEL = {
    "consolidado": "Consolidado",
    "emergente":   "Emergente",
    "retracao":    "Em retração",
    "potencial":   "Potencial",
}
CAT_COLOR = {
    "consolidado": "#2D6A4F",
    "emergente":   "#52B788",
    "retracao":    "#C9A84C",
    "potencial":   "#2C6E8A",
}
CAT_BG = {
    "consolidado": "#d8f3dc",
    "emergente":   "#e8f8f0",
    "retracao":    "#fdf3dc",
    "potencial":   "#dceaf0",
}


def build_html(apl: dict, ind: dict) -> str:
    produtos  = ind["produtos"]
    municipios = ind["municipios"]

    meta     = apl["meta"]
    resumo   = apl["resumo"]
    apl_data = apl["apl"]
    mun_idx  = apl.get("mun_index", {})
    stats    = apl.get("stats", {})
    ano_ref  = meta["ano_ref"]

    now = datetime.now()
    update_date = f"{MESES_PT[now.month]} {now.year}"

    # Serializa para JS
    apl_json     = json.dumps(apl_data,   ensure_ascii=False, separators=(",", ":"))
    resumo_json  = json.dumps(resumo,     ensure_ascii=False, separators=(",", ":"))
    produtos_json= json.dumps(produtos,   ensure_ascii=False, separators=(",", ":"))
    mun_json     = json.dumps(municipios, ensure_ascii=False, separators=(",", ":"))
    stats_json   = json.dumps(stats,      ensure_ascii=False, separators=(",", ":"))
    meta_json    = json.dumps(meta,       ensure_ascii=False, separators=(",", ":"))

    # Options do seletor de cadeia
    groups: dict[str, list] = {}
    for k, v in produtos.items():
        groups.setdefault(v["grupo"], []).append((k, v["label"]))
    opts_parts = []
    for g, items in groups.items():
        opts_parts.append(f'<optgroup label="{g}">')
        for k, label in items:
            if any(str(ano_ref) in apl_data.get(k, {}) for k in [k]):
                opts_parts.append(f'  <option value="{k}">{label}</option>')
        opts_parts.append("</optgroup>")
    prod_options = "\n".join(opts_parts)

    # Anos disponíveis com dados APL (pelo menos 1 cadeia)
    anos_disp = sorted({
        int(ano)
        for cadeia in resumo.values()
        for ano, v in cadeia.items()
        if v.get("n", 0) > 0
    })
    anos_json = json.dumps(anos_disp)

    first_cadeia = next(
        (k for k in produtos if str(ano_ref) in apl_data.get(k, {})),
        next(iter(produtos))
    )

    # Top municípios em múltiplas cadeias
    top_muns_raw = stats.get("top_muns_multiplos", [])
    top_muns_html = ""
    for mid, n in top_muns_raw[:10]:
        nome = municipios.get(mid, mid)
        cadeias = mun_idx.get(mid, [])
        cad_labels = ", ".join(produtos.get(c, {}).get("label", c) for c in cadeias[:5])
        top_muns_html += f"""
          <tr>
            <td style="font-weight:500">{nome}</td>
            <td style="text-align:center;font-weight:600;color:#2D6A4F">{n}</td>
            <td style="font-size:11px;color:#666">{cad_labels}</td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCAS-MA — Boletim APL</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cpolygon points='32,4 56,18 56,46 32,60 8,46 8,18' fill='none' stroke='%232D6A4F' stroke-width='2.5'/%3E%3Ccircle cx='32' cy='32' r='7' fill='%2352B788'/%3E%3C/svg%3E">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
    :root {{
      --ocas-floresta:#1B4332; --ocas-mata:#2D6A4F; --ocas-igapo:#40916C;
      --ocas-babacu:#52B788;  --ocas-buriti:#74C69D; --ocas-varzea:#D8F3DC;
      --ocas-bg-page:#F7FAF8; --ocas-bg-header:#fff; --ocas-bg-card:#fff;
      --ocas-border:#ddeee5;  --ocas-border-soft:#c8e0d0;
      --ocas-cerrado:#C9A84C; --ocas-rio:#2C6E8A;
      --ocas-font-titulo:Georgia,'Times New Roman',serif;
      --ocas-font-label:'Courier New',Courier,monospace;
      --ocas-font-dados:system-ui,-apple-system,sans-serif;
      --ocas-radius-sm:6px; --ocas-radius-md:10px;
      --ocas-shadow-card:0 1px 3px rgba(27,67,50,.06);
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--ocas-bg-page);font-family:var(--ocas-font-dados);color:#222}}
    .ocas-header{{background:#fff;border-bottom:1px solid var(--ocas-border);padding:18px 28px}}
    .ocas-header-inner{{display:flex;align-items:center;justify-content:space-between;max-width:1400px;margin:0 auto}}
    .ocas-brand{{display:flex;align-items:center;gap:16px;text-decoration:none}}
    .ocas-brand-text{{display:flex;flex-direction:column;gap:2px}}
    .ocas-sigla{{font-family:var(--ocas-font-titulo);font-size:22px;font-weight:700;color:var(--ocas-floresta);letter-spacing:1px;line-height:1}}
    .ocas-vinculo{{font-family:var(--ocas-font-label);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--ocas-igapo)}}
    .ocas-header-meta{{font-family:var(--ocas-font-label);font-size:10px;color:var(--ocas-igapo);text-align:right;line-height:1.8}}
    .ocas-nav{{background:var(--ocas-bg-page);border-bottom:1px solid var(--ocas-border);display:flex;padding:0 28px;overflow-x:auto}}
    .ocas-nav-item{{padding:10px 16px;font-family:var(--ocas-font-label);font-size:11px;letter-spacing:.5px;color:var(--ocas-igapo);text-decoration:none;border-bottom:2px solid transparent;transition:color .2s,border-color .2s;white-space:nowrap}}
    .ocas-nav-item:hover{{color:var(--ocas-mata)}}
    .ocas-nav-item.active{{color:var(--ocas-mata);border-bottom-color:var(--ocas-mata)}}
    .ocas-section{{max-width:1400px;margin:0 auto;padding:24px 28px}}
    .ocas-section-title{{font-family:var(--ocas-font-titulo);font-size:20px;color:var(--ocas-floresta);margin-bottom:4px}}
    .ocas-section-sub{{font-size:12px;color:var(--ocas-buriti);margin-bottom:22px;font-family:var(--ocas-font-label)}}
    .ocas-controls{{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;margin-bottom:20px;background:#fff;border:.5px solid var(--ocas-border);border-radius:var(--ocas-radius-md);padding:16px 20px;box-shadow:var(--ocas-shadow-card)}}
    .ocas-control-group{{display:flex;flex-direction:column;gap:5px}}
    .ocas-control-label{{font-family:var(--ocas-font-label);font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--ocas-igapo)}}
    .ocas-select{{font-family:var(--ocas-font-dados);font-size:13px;color:var(--ocas-floresta);background:#fff;border:1px solid var(--ocas-border-soft);border-radius:var(--ocas-radius-sm);padding:7px 12px;cursor:pointer;outline:none}}
    .ocas-select:focus{{border-color:var(--ocas-mata)}}
    .ocas-slider-wrap{{flex:1;min-width:200px}}
    .ocas-year-display{{font-family:var(--ocas-font-titulo);font-size:22px;font-weight:500;color:var(--ocas-floresta);margin-bottom:4px}}
    .ocas-slider{{width:100%;accent-color:var(--ocas-mata);cursor:pointer}}
    .ocas-slider-labels{{display:flex;justify-content:space-between;font-family:var(--ocas-font-label);font-size:9px;color:var(--ocas-buriti);margin-top:2px}}
    .ocas-cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}}
    .ocas-card{{background:#fff;border:.5px solid var(--ocas-border);border-radius:var(--ocas-radius-md);border-left:3px solid var(--ocas-mata);padding:16px 18px;box-shadow:var(--ocas-shadow-card)}}
    .ocas-card-label{{font-family:var(--ocas-font-label);font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--ocas-igapo);margin-bottom:6px}}
    .ocas-card-value{{font-family:var(--ocas-font-titulo);font-size:26px;font-weight:500;color:var(--ocas-floresta);line-height:1.1}}
    .ocas-card-desc{{font-size:10px;color:var(--ocas-buriti);margin-top:4px}}
    .ocas-charts-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}}
    @media(max-width:960px){{.ocas-charts-grid{{grid-template-columns:1fr}}}}
    .ocas-chart-card{{background:#fff;border:.5px solid var(--ocas-border);border-radius:var(--ocas-radius-md);padding:16px;box-shadow:var(--ocas-shadow-card)}}
    .ocas-chart-title{{font-family:var(--ocas-font-label);font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--ocas-igapo);margin-bottom:12px}}
    .ocas-fonte{{font-family:var(--ocas-font-label);font-size:9px;color:var(--ocas-buriti);margin-top:8px;text-align:right}}
    .ocas-nota{{background:var(--ocas-varzea);border:1px solid var(--ocas-border);border-radius:var(--ocas-radius-md);padding:14px 18px;font-size:12px;color:#444;line-height:1.7;margin-top:24px}}
    .ocas-nota strong{{color:var(--ocas-floresta)}}

    /* APL TABLE */
    .apl-table-wrap{{background:#fff;border:.5px solid var(--ocas-border);border-radius:var(--ocas-radius-md);padding:16px;box-shadow:var(--ocas-shadow-card);margin-bottom:20px;overflow-x:auto}}
    .apl-table-title{{font-family:var(--ocas-font-label);font-size:10px;letter-spacing:1px;text-transform:uppercase;color:var(--ocas-igapo);margin-bottom:12px}}
    table.apl-table{{width:100%;border-collapse:collapse;font-size:12px}}
    table.apl-table th{{font-family:var(--ocas-font-label);font-size:9px;letter-spacing:.5px;text-transform:uppercase;color:var(--ocas-igapo);padding:6px 10px;border-bottom:1px solid var(--ocas-border);text-align:left;background:#f7faf8}}
    table.apl-table td{{padding:7px 10px;border-bottom:.5px solid var(--ocas-border);vertical-align:middle}}
    table.apl-table tr:last-child td{{border-bottom:none}}
    table.apl-table tr:hover td{{background:#f7faf8}}
    .apl-badge{{display:inline-block;font-family:var(--ocas-font-label);font-size:9px;letter-spacing:.5px;padding:2px 8px;border-radius:10px;font-weight:600}}

    /* TOP MUNS */
    .top-muns-wrap{{background:#fff;border:.5px solid var(--ocas-border);border-radius:var(--ocas-radius-md);padding:16px;box-shadow:var(--ocas-shadow-card);margin-bottom:20px}}
    .top-muns-title{{font-family:var(--ocas-font-titulo);font-size:15px;color:var(--ocas-floresta);margin-bottom:12px}}
    table.top-table{{width:100%;border-collapse:collapse;font-size:12px}}
    table.top-table th{{font-family:var(--ocas-font-label);font-size:9px;letter-spacing:.5px;text-transform:uppercase;color:var(--ocas-igapo);padding:6px 10px;border-bottom:1px solid var(--ocas-border);background:#f7faf8}}
    table.top-table td{{padding:7px 10px;border-bottom:.5px solid var(--ocas-border)}}
    table.top-table tr:last-child td{{border-bottom:none}}
  </style>
</head>
<body>

<header class="ocas-header">
  <div class="ocas-header-inner">
    <a href="index.html" class="ocas-brand">
      <svg width="36" height="36" viewBox="0 0 64 64" fill="none">
        <polygon points="32,4 56,18 56,46 32,60 8,46 8,18" stroke="#2D6A4F" stroke-width="2.5"/>
        <circle cx="32" cy="32" r="7" fill="#52B788"/>
      </svg>
      <div class="ocas-brand-text">
        <span class="ocas-sigla">OCAS-MA</span>
        <span class="ocas-vinculo">GEIA &middot; CECON &middot; UFMA</span>
      </div>
    </a>
    <div class="ocas-header-meta">
      BOLETIM APL — ARRANJOS PRODUTIVOS LOCAIS<br>
      Atualizado: {update_date}
    </div>
  </div>
</header>

<nav class="ocas-nav">
  <a href="index.html"       class="ocas-nav-item">Cadeias</a>
  <a href="indicadores.html" class="ocas-nav-item">Indicadores</a>
  <a href="apl.html"         class="ocas-nav-item active">Boletim APL</a>
  <a href="index.html#sobre"       class="ocas-nav-item">O que &eacute;</a>
  <a href="index.html#equipe"      class="ocas-nav-item">Quem somos</a>
  <a href="index.html#metodologia" class="ocas-nav-item">Metodologia</a>
  <a href="index.html#boletins"    class="ocas-nav-item">Boletins</a>
  <a href="index.html#contato"     class="ocas-nav-item">Fale conosco</a>
</nav>

<main class="ocas-section">
  <h2 class="ocas-section-title">Identificação de Arranjos Produtivos Locais</h2>
  <p class="ocas-section-sub">
    Maranhão · unidade: município · critérios: LISA HH + QL + TCG · fontes: IBGE / SICOR-BCB
  </p>

  <!-- CONTROLES -->
  <div class="ocas-controls">
    <div class="ocas-control-group">
      <span class="ocas-control-label">Cadeia produtiva</span>
      <select id="sel-cadeia" class="ocas-select" onchange="update()">
        {prod_options}
      </select>
    </div>
    <div class="ocas-slider-wrap">
      <span class="ocas-control-label">Ano de referência</span>
      <div class="ocas-year-display" id="year-display">{ano_ref}</div>
      <input type="range" class="ocas-slider" id="year-slider"
             min="{anos_disp[0]}" max="{anos_disp[-1]}" value="{ano_ref}" step="1"
             oninput="document.getElementById('year-display').textContent=this.value; update()">
      <div class="ocas-slider-labels">
        <span>{anos_disp[0]}</span><span>{anos_disp[-1]}</span>
      </div>
    </div>
  </div>

  <!-- CARDS -->
  <div class="ocas-cards-grid">
    <div class="ocas-card" style="border-left-color:#2D6A4F">
      <div class="ocas-card-label">APL consolidados</div>
      <div class="ocas-card-value" id="card-con">—</div>
      <div class="ocas-card-desc">HH sig + QL≥1,25 + TCG>0 + persistente</div>
    </div>
    <div class="ocas-card" style="border-left-color:#52B788">
      <div class="ocas-card-label">APL emergentes</div>
      <div class="ocas-card-value" id="card-eme">—</div>
      <div class="ocas-card-desc">HH sig + QL≥1 + TCG>0</div>
    </div>
    <div class="ocas-card" style="border-left-color:#C9A84C">
      <div class="ocas-card-label">Clusters em retração</div>
      <div class="ocas-card-value" id="card-ret">—</div>
      <div class="ocas-card-desc">HH sig + QL≥1 + TCG≤0</div>
    </div>
    <div class="ocas-card" style="border-left-color:#2C6E8A">
      <div class="ocas-card-label">APL potenciais</div>
      <div class="ocas-card-value" id="card-pot">—</div>
      <div class="ocas-card-desc">QL≥1,25 + TCG>0 (sem cluster LISA)</div>
    </div>
  </div>

  <!-- GRÁFICOS -->
  <div class="ocas-charts-grid">
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Evolução histórica — n.º de APLs por categoria</div>
      <div id="chart-evolucao" style="height:320px"></div>
      <div class="ocas-fonte">Todas as categorias · barra empilhada</div>
    </div>
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">I de Moran × n.º APLs — série histórica</div>
      <div id="chart-moran-apl" style="height:320px"></div>
      <div class="ocas-fonte">Eixo esq.: I de Moran · Eixo dir.: n.º APLs consolidados+emergentes</div>
    </div>
  </div>

  <!-- TABELA APL -->
  <div class="apl-table-wrap">
    <div class="apl-table-title" id="table-title">APLs identificados — {ano_ref}</div>
    <table class="apl-table">
      <thead>
        <tr>
          <th>Município</th>
          <th>Categoria</th>
          <th>QL</th>
          <th>TCG (a.a.)</th>
          <th>Score</th>
          <th>Persist.</th>
          <th>LISA</th>
          <th>p-valor</th>
        </tr>
      </thead>
      <tbody id="apl-tbody"></tbody>
    </table>
  </div>

  <!-- TOP MUNICÍPIOS EM MÚLTIPLAS CADEIAS -->
  <div class="top-muns-wrap">
    <div class="top-muns-title">Municípios com APL em múltiplas cadeias — {ano_ref}</div>
    <table class="top-table">
      <thead><tr><th>Município</th><th>N.º cadeias</th><th>Cadeias</th></tr></thead>
      <tbody>{top_muns_html}</tbody>
    </table>
  </div>

  <!-- NOTA METODOLÓGICA -->
  <div class="ocas-nota">
    <strong>Metodologia de identificação APL — OCAS-MA</strong><br>
    Os APLs são identificados pelo cruzamento de três critérios independentes:<br>
    <strong>(1) Clustering espacial</strong>: município com LISA HH significativo (p&lt;0,05),
    matriz de contiguidade Queen, 999 permutações &mdash; indica que o município e seus
    vizinhos são especializados na mesma cadeia.<br>
    <strong>(2) Especialização local</strong>: QL ≥ 1,0 (básico) ou QL ≥ 1,25 (consolidado)
    &mdash; o município produz a cadeia acima da média estadual.<br>
    <strong>(3) Dinamismo</strong>: TCG > 0 (crescimento positivo na janela de 10 anos)
    &mdash; o cluster está em expansão.<br>
    <strong>Categorias</strong>: <em>Consolidado</em> = os três critérios com persistência ≥3/5 anos;
    <em>Emergente</em> = os três critérios sem persistência; <em>Retração</em> = HH sig + QL≥1 mas TCG≤0;
    <em>Potencial</em> = QL≥1,25 + TCG>0 sem clustering LISA.<br>
    <strong>Score APL</strong> (0–1): combinação ponderada de QL (35%), LISA (25%),
    TCG (20%) e persistência histórica (20%).
    Fontes: IBGE (PEVS/PAM/PPM) para produção; BCB/SICOR para crédito rural.
    Análise espacial: libpysal + esda (PySAL).
  </div>
</main>

<script>
const APL     = {apl_json};
const RESUMO  = {resumo_json};
const PROD    = {produtos_json};
const MUNS    = {mun_json};
const STATS   = {stats_json};
const META    = {meta_json};
const ANOS    = {anos_json};

const CAT_COLOR = {{
  consolidado: '#2D6A4F', emergente: '#52B788',
  retracao:    '#C9A84C', potencial: '#2C6E8A',
}};
const CAT_BG = {{
  consolidado: '#d8f3dc', emergente: '#e8f8f0',
  retracao:    '#fdf3dc', potencial: '#dceaf0',
}};
const CAT_LABEL = {{
  consolidado: 'Consolidado', emergente: 'Emergente',
  retracao: 'Em retração', potencial: 'Potencial',
}};

function getProd() {{ return document.getElementById('sel-cadeia').value; }}
function getAno()  {{ return parseInt(document.getElementById('year-slider').value); }}
function fmt(v, d=2) {{
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(d).replace('.', ',');
}}

function update() {{
  const prod = getProd();
  const ano  = getAno();
  const anoS = String(ano);

  const rec  = (RESUMO[prod] || {{}})[anoS] || {{}};
  document.getElementById('card-con').textContent = rec.n_con ?? '—';
  document.getElementById('card-eme').textContent = rec.n_eme ?? '—';
  document.getElementById('card-ret').textContent = rec.n_ret ?? '—';
  document.getElementById('card-pot').textContent = rec.n_pot ?? '—';

  // ─ Tabela APL ─
  const muns_ano = (APL[prod] || {{}})[anoS] || {{}};
  document.getElementById('table-title').textContent =
    'APLs identificados — ' + (PROD[prod]?.label || prod) + ' · ' + ano;
  const cats_ord = ['consolidado','emergente','retracao','potencial'];
  const rows = Object.entries(muns_ano)
    .sort((a,b) => {{
      const ci = cats_ord.indexOf(a[1].cat) - cats_ord.indexOf(b[1].cat);
      return ci !== 0 ? ci : b[1].score - a[1].score;
    }});
  const tbody = document.getElementById('apl-tbody');
  tbody.innerHTML = rows.map(([mid, d]) => {{
    const nm  = MUNS[mid] || mid;
    const clr = CAT_COLOR[d.cat] || '#888';
    const bg  = CAT_BG[d.cat]   || '#eee';
    const tcg = d.tcg != null ? fmt(d.tcg * 100, 1) + '%' : '—';
    const lp  = d.lisa_p != null ? (d.lisa_p < 0.001 ? '<0,001' : fmt(d.lisa_p, 3)) : '—';
    return `<tr>
      <td style="font-weight:500">${{nm}}</td>
      <td><span class="apl-badge" style="background:${{bg}};color:${{clr}}">${{CAT_LABEL[d.cat]||d.cat}}</span></td>
      <td>${{fmt(d.ql, 2)}}</td>
      <td>${{tcg}}</td>
      <td>${{fmt(d.score, 3)}}</td>
      <td style="text-align:center">${{d.persist ?? '—'}}</td>
      <td style="text-align:center;font-weight:600;color:${{d.lisa_q==='HH'?'#d73027':'#888'}}">${{d.lisa_q||'—'}}</td>
      <td>${{lp}}</td>
    </tr>`;
  }}).join('');

  if (!rows.length) {{
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;padding:24px">Sem APLs identificados neste ano/cadeia</td></tr>';
  }}

  // ─ Evolução empilhada ─
  const cats = ['consolidado','emergente','retracao','potencial'];
  const ev_anos = Object.keys(RESUMO[prod] || {{}}).map(Number).sort();
  const ev_traces = cats.map(cat => {{
    const key = 'n_' + cat.substring(0,3);
    return {{
      type:'bar', name: CAT_LABEL[cat],
      x: ev_anos,
      y: ev_anos.map(a => (RESUMO[prod]?.[String(a)]?.[key] || 0)),
      marker:{{ color: CAT_COLOR[cat] }},
      hovertemplate: '%{{x}}: %{{y}} APLs<extra>' + CAT_LABEL[cat] + '</extra>',
    }};
  }});
  Plotly.react('chart-evolucao', ev_traces, {{
    barmode: 'stack',
    margin:{{l:45,r:20,t:10,b:30}},
    xaxis:{{title:'Ano'}},
    yaxis:{{title:'N.º APLs'}},
    legend:{{font:{{size:9}},orientation:'h',y:-0.15}},
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'system-ui',size:11}},
  }},{{responsive:true}});

  // ─ Moran I × APL count ─
  const m_anos = ev_anos;
  const m_I    = m_anos.map(a => (RESUMO[prod]?.[String(a)]?.I ?? null));
  const m_napl = m_anos.map(a => {{
    const r = RESUMO[prod]?.[String(a)] || {{}};
    return (r.n_con||0) + (r.n_eme||0);
  }});
  Plotly.react('chart-moran-apl', [
    {{
      type:'scatter', mode:'lines+markers', name:'I de Moran',
      x:m_anos, y:m_I, yaxis:'y',
      line:{{color:'#52B788',width:2}},
      marker:{{size:6,color:'#2D6A4F'}},
      hovertemplate:'%{{x}}<br>I: %{{y:.4f}}<extra>Moran</extra>',
    }},
    {{
      type:'bar', name:'APLs (con.+eme.)',
      x:m_anos, y:m_napl, yaxis:'y2',
      marker:{{color:'rgba(45,106,79,.15)',line:{{color:'#2D6A4F',width:1}}}},
      hovertemplate:'%{{x}}: %{{y}} APLs<extra></extra>',
    }},
  ], {{
    margin:{{l:50,r:50,t:10,b:30}},
    xaxis:{{title:'Ano'}},
    yaxis:{{title:'I de Moran',side:'left'}},
    yaxis2:{{title:'N.º APLs',side:'right',overlaying:'y',showgrid:false}},
    legend:{{font:{{size:9}}}},
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'system-ui',size:11}},
  }},{{responsive:true}});
}}

// Init
document.getElementById('sel-cadeia').value = '{first_cadeia}';
update();
</script>
</body>
</html>"""


def main() -> None:
    if not APL_FILE.exists():
        print(f"ERRO: {APL_FILE} não encontrado. Execute compute_indicators_apl.py primeiro.")
        raise SystemExit(1)
    if not IND_FILE.exists():
        print(f"ERRO: {IND_FILE} não encontrado.")
        raise SystemExit(1)

    apl = json.loads(APL_FILE.read_text(encoding="utf-8"))
    ind = json.loads(IND_FILE.read_text(encoding="utf-8"))

    html = build_html(apl, ind)
    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Boletim salvo : {OUT_FILE}")
    print(f"Tamanho       : {OUT_FILE.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
