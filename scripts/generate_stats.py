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

    credito        = ind_data.get("credito", {})

    produtos_json  = json.dumps(produtos,    ensure_ascii=False, separators=(",", ":"))
    municipios_json = json.dumps(municipios, ensure_ascii=False, separators=(",", ":"))
    ind_json       = json.dumps(indicadores, ensure_ascii=False, separators=(",", ":"))
    anos_json      = json.dumps(anos,        separators=(",", ":"))
    credito_json   = json.dumps(credito,     ensure_ascii=False, separators=(",", ":"))

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

    /* TABS */
    .ocas-tabs {{ display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid var(--ocas-border); }}
    .ocas-tab {{
      background: none; border: none; border-bottom: 3px solid transparent;
      margin-bottom: -2px; padding: 10px 22px; cursor: pointer;
      font-family: var(--ocas-font-label); font-size: 11px; letter-spacing: 1px;
      text-transform: uppercase; color: var(--ocas-buriti);
      transition: color .2s, border-color .2s;
    }}
    .ocas-tab:hover {{ color: var(--ocas-mata); }}
    .ocas-tab.active {{ color: var(--ocas-mata); border-bottom-color: var(--ocas-mata); font-weight: 600; }}
    .ocas-tab-badge {{
      display: inline-block; font-size: 8px; padding: 1px 5px;
      border-radius: 8px; margin-left: 6px; vertical-align: middle;
      background: var(--ocas-varzea); color: var(--ocas-igapo); letter-spacing: 0;
    }}
    .ocas-tab-panel {{ display: none; }}
    .ocas-tab-panel.active {{ display: block; animation: fadeTab .18s ease; }}
    @keyframes fadeTab {{ from {{ opacity:.4 }} to {{ opacity:1 }} }}

    /* PLACEHOLDER (tabs em desenvolvimento) */
    .ocas-placeholder {{
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 320px; gap: 16px; text-align: center; padding: 48px 24px;
      background: var(--ocas-bg-card); border: 1px dashed var(--ocas-border-soft);
      border-radius: var(--ocas-radius-md);
    }}
    .ocas-placeholder-icon {{ font-size: 40px; opacity: .5; }}
    .ocas-placeholder-title {{ font-family: var(--ocas-font-titulo); font-size: 17px; color: var(--ocas-floresta); }}
    .ocas-placeholder-desc {{ font-size: 13px; color: var(--ocas-buriti); max-width: 460px; line-height: 1.7; }}
    .ocas-placeholder-list {{
      display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 4px;
    }}
    .ocas-placeholder-chip {{
      font-family: var(--ocas-font-label); font-size: 10px; letter-spacing: .5px;
      padding: 4px 12px; border-radius: 20px;
      background: var(--ocas-varzea); color: var(--ocas-igapo);
      border: 1px solid var(--ocas-border-soft);
    }}
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
  <a href="apl.html"         class="ocas-nav-item">Boletim APL</a>
  <a href="index.html#sobre"       class="ocas-nav-item">O que &eacute;</a>
  <a href="index.html#equipe"      class="ocas-nav-item">Quem somos</a>
  <a href="index.html#metodologia" class="ocas-nav-item">Metodologia</a>
  <a href="index.html#boletins"    class="ocas-nav-item">Boletins</a>
  <a href="index.html#contato"     class="ocas-nav-item">Fale conosco</a>
</nav>

<!-- MAIN -->
<main class="ocas-section">
  <h2 class="ocas-section-title">Análise quantitativa das cadeias produtivas</h2>
  <p class="ocas-section-sub">
    Unidade de análise: município do Maranhão &mdash; fontes: IBGE · BCB/SICOR
  </p>

  <!-- BARRA DE TABS -->
  <div class="ocas-tabs" role="tablist">
    <button class="ocas-tab active" role="tab" data-tab="producao"
            onclick="switchTab('producao')" aria-selected="true">
      Produ&ccedil;&atilde;o
      <span class="ocas-tab-badge">QL · PR · TCG · IDM</span>
    </button>
    <button class="ocas-tab" role="tab" data-tab="credito"
            onclick="switchTab('credito')" aria-selected="false">
      Cr&eacute;dito Rural
      <span class="ocas-tab-badge">VCR · Pronaf · ICR</span>
    </button>
    <button class="ocas-tab" role="tab" data-tab="espacial"
            onclick="switchTab('espacial')" aria-selected="false">
      An&aacute;lise Espacial
      <span class="ocas-tab-badge">Moran · LISA</span>
    </button>
  </div>

  <!-- CONTROLES COMPARTILHADOS -->
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

  <!-- ═══════════════════ TAB 1 — PRODUÇÃO ═══════════════════ -->
  <div id="tab-producao" class="ocas-tab-panel active" role="tabpanel">

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

  </div><!-- /tab-producao -->

  <!-- ═══════════════════ TAB 2 — CRÉDITO RURAL ═══════════════════ -->
  <div id="tab-credito" class="ocas-tab-panel" role="tabpanel">

  <!-- CARDS -->
  <div class="ocas-cards-grid">
    <div class="ocas-card">
      <div class="ocas-card-label">VCR total (MA)</div>
      <div class="ocas-card-value" id="card-vcr-total">—</div>
      <div class="ocas-card-desc">custeio + investimento</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">Municípios com crédito</div>
      <div class="ocas-card-value" id="card-vcr-nmun">—</div>
      <div class="ocas-card-desc">com ao menos 1 operação</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">Pronaf share médio</div>
      <div class="ocas-card-value" id="card-pronaf-share">—</div>
      <div class="ocas-card-desc">% do crédito via Pronaf</div>
    </div>
    <div class="ocas-card">
      <div class="ocas-card-label">ICR médio</div>
      <div class="ocas-card-value" id="card-icr">—</div>
      <div class="ocas-card-desc">crédito / valor da produção</div>
    </div>
  </div>

  <!-- GRÁFICOS -->
  <div class="ocas-charts-grid">
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Evolução do VCR — top 10 municípios (R$ mi)</div>
      <div class="ocas-chart-container" id="chart-vcr-serie" style="height:340px"></div>
      <div class="ocas-fonte">SICOR/BCB · custeio + investimento · 2013–2025</div>
    </div>
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Ranking — Quociente Locacional do crédito (QL)</div>
      <div class="ocas-chart-container" id="chart-ql-cred" style="height:340px"></div>
      <div class="ocas-fonte">QL &gt; 1: concentração de crédito acima da média estadual</div>
    </div>
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Pronaf share médio estadual por ano (%)</div>
      <div class="ocas-chart-container" id="chart-pronaf" style="height:300px"></div>
      <div class="ocas-fonte">Média entre os municípios com crédito na cadeia selecionada</div>
    </div>
    <div class="ocas-chart-card">
      <div class="ocas-chart-title">Intensidade de Crédito (ICR) — top municípios</div>
      <div class="ocas-chart-container" id="chart-icr" style="height:300px"></div>
      <div class="ocas-fonte">ICR = VCR / Valor da Produção (adimensional) — cadeias com dados IBGE</div>
    </div>
  </div>

  <!-- NOTA -->
  <div class="ocas-nota">
    <strong>Notas metodológicas — Crédito Rural</strong><br>
    <strong>VCR</strong> (Volume de Crédito Rural): soma de custeio e investimento contratados (SICOR/BCB) para o município e cadeia no ano, em R$.<br>
    <strong>QL do crédito</strong>: razão entre a participação do município no crédito da cadeia e sua participação no crédito agrícola total do estado. QL &gt; 1 indica especialização no acesso a crédito.<br>
    <strong>Pronaf share</strong>: parcela do crédito proveniente do Programa Nacional de Fortalecimento da Agricultura Familiar (cd_programa = 0001), em %.<br>
    <strong>ICR</strong> (Intensidade de Crédito): razão entre o VCR e o valor da produção (IBGE). Disponível apenas para cadeias com valor de produção monetário.
  </div>

  </div><!-- /tab-credito -->

  <!-- ═══════════════════ TAB 3 — ANÁLISE ESPACIAL ═══════════════════ -->
  <div id="tab-espacial" class="ocas-tab-panel" role="tabpanel">

    <!-- CARREGANDO -->
    <div id="esp-loading" class="ocas-placeholder">
      <div class="ocas-placeholder-icon">⏳</div>
      <div class="ocas-placeholder-title">Carregando análise espacial...</div>
      <div class="ocas-placeholder-desc" id="esp-load-msg">
        Buscando dados de autocorrelação (pode levar alguns segundos).
      </div>
    </div>

    <!-- CONTEÚDO (exibido após carga) -->
    <div id="esp-content" style="display:none">

    <!-- CARDS -->
    <div class="ocas-cards-grid">
      <div class="ocas-card">
        <div class="ocas-card-label">I de Moran global</div>
        <div class="ocas-card-value" id="card-moran-i">—</div>
        <div class="ocas-card-desc">autocorrelação espacial do QL</div>
      </div>
      <div class="ocas-card">
        <div class="ocas-card-label">z-score (999 perm.)</div>
        <div class="ocas-card-value" id="card-moran-z">—</div>
        <div class="ocas-card-desc">desvios da distribuição nula</div>
      </div>
      <div class="ocas-card">
        <div class="ocas-card-label">p-valor</div>
        <div class="ocas-card-value" id="card-moran-p">—</div>
        <div class="ocas-card-desc">p &lt; 0,05 = clustering significativo</div>
      </div>
      <div class="ocas-card">
        <div class="ocas-card-label">APL candidatos (HH)</div>
        <div class="ocas-card-value" id="card-hh-count">—</div>
        <div class="ocas-card-desc">municípios HH sig. (p &lt; 0,05)</div>
      </div>
    </div>

    <!-- GRÁFICOS -->
    <div class="ocas-charts-grid">
      <div class="ocas-chart-card">
        <div class="ocas-chart-title">Mapa LISA — clusters espaciais</div>
        <div id="chart-lisa-map" style="height:400px"></div>
        <div class="ocas-fonte">
          <span style="color:#d73027">&#9632;</span> HH &nbsp;
          <span style="color:#fdae61">&#9632;</span> HL &nbsp;
          <span style="color:#74b9e4">&#9632;</span> LH &nbsp;
          <span style="color:#4575b4">&#9632;</span> LL &nbsp;
          <span style="color:#aaa">&#9632;</span> n.s.
        </div>
      </div>
      <div class="ocas-chart-card">
        <div class="ocas-chart-title">Diagrama de dispersão de Moran</div>
        <div id="chart-moran-scatter" style="height:400px"></div>
        <div class="ocas-fonte">Eixo x: QL padronizado · Eixo y: defasagem espacial · linhas: média = 0</div>
      </div>
      <div class="ocas-chart-card">
        <div class="ocas-chart-title">I de Moran global — série histórica</div>
        <div id="chart-moran-serie" style="height:300px"></div>
        <div class="ocas-fonte">Bola verde = sig. (p&lt;0,05) · linha = I=0</div>
      </div>
      <div class="ocas-chart-card">
        <div class="ocas-chart-title">Municípios HH sig. — APL candidatos</div>
        <div id="chart-hh-bar" style="height:300px"></div>
        <div class="ocas-fonte">Ordenado por QL · HH sig. (p&lt;0,05)</div>
      </div>
    </div>

    <!-- NOTA -->
    <div class="ocas-nota">
      <strong>Notas metodológicas — Análise Espacial</strong><br>
      <strong>I de Moran global</strong>: autocorrelação do QL no estado.
      I &gt; 0 = clustering; I &lt; 0 = dispersão. Significância por 999 permutações aleatórias.<br>
      <strong>LISA</strong>: <strong>HH</strong> = alto-alto (candidato a APL);
      <strong>LL</strong> = baixo-baixo; <strong>LH/HL</strong> = outliers espaciais.<br>
      <strong>APL candidato</strong>: LISA HH sig. (p&lt;0,05) + QL &gt; 1 + TCG positivo.<br>
      Pesos: contiguidade Queen, row-standardized. Variável: QL (IBGE PEVS/PAM/PPM).
    </div>

    </div><!-- /esp-content -->
  </div><!-- /tab-espacial -->

</main>

<script>
const PRODUTOS    = {produtos_json};
const MUNICIPIOS  = {municipios_json};
const IND        = {ind_json};
const ANOS_DISP  = {anos_json};
const TCG_JANELA = {janela};
const CREDITO    = {credito_json};

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

  // Mantém tab ativa sincronizada quando o seletor muda
  const _at = (document.querySelector('.ocas-tab.active')||{{}}).dataset;
  if (_at && _at.tab === 'credito')  updateCredito();
  if (_at && _at.tab === 'espacial') updateEspacial();
}}

// ── CRÉDITO RURAL ─────────────────────────────────────────────────
function fmtBRL(v) {{
  if (v == null || isNaN(v)) return "—";
  if (v >= 1e9) return "R$ " + (v / 1e9).toFixed(1).replace(".", ",") + " bi";
  if (v >= 1e6) return "R$ " + (v / 1e6).toFixed(1).replace(".", ",") + " mi";
  if (v >= 1e3) return "R$ " + (v / 1e3).toFixed(0) + " mil";
  return "R$ " + v.toFixed(0);
}}

function updateCredito() {{
  const prod = getProd();
  const ano  = getAno();
  const anoS = String(ano);
  const cred = CREDITO;

  const vcr_map    = ((cred.vcr          || {{}})[prod] || {{}})[anoS] || {{}};
  const ql_map     = ((cred.ql_cred      || {{}})[prod] || {{}})[anoS] || {{}};
  const pronaf_map = ((cred.pronaf_share || {{}})[prod] || {{}})[anoS] || {{}};
  const icr_map    = ((cred.icr          || {{}})[prod] || {{}})[anoS] || {{}};

  // ─ CARDS ─
  const vcr_total   = Object.values(vcr_map).reduce((a, b) => a + (b || 0), 0);
  const n_mun       = Object.values(vcr_map).filter(v => v > 0).length;
  const pv          = Object.values(pronaf_map).filter(v => v != null);
  const pronaf_med  = pv.length ? pv.reduce((a, b) => a + b, 0) / pv.length * 100 : null;
  const iv          = Object.values(icr_map).filter(v => v != null);
  const icr_med     = iv.length ? iv.reduce((a, b) => a + b, 0) / iv.length : null;

  document.getElementById("card-vcr-total").textContent    = fmtBRL(vcr_total);
  document.getElementById("card-vcr-nmun").textContent     = n_mun || "—";
  document.getElementById("card-pronaf-share").textContent = pronaf_med != null ? fmt(pronaf_med, 1) + "%" : "—";
  document.getElementById("card-icr").textContent          = icr_med  != null ? fmt(icr_med, 2)  : "—";

  // ─ VCR SÉRIE HISTÓRICA — top 10 no ano selecionado ─
  const top10 = Object.entries(vcr_map).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([mid]) => mid);
  const v_anos = Object.keys((cred.vcr || {{}})[prod] || {{}}).map(Number).sort();
  const vcr_traces = top10.map((mid, i) => {{
    const xs = [], ys = [];
    v_anos.forEach(a => {{
      const v = (((cred.vcr || {{}})[prod] || {{}})[String(a)] || {{}})[mid];
      if (v != null) {{ xs.push(a); ys.push(+(v / 1e6).toFixed(3)); }}
    }});
    return {{
      type: "scatter", mode: "lines+markers", name: MUNICIPIOS[mid] || mid,
      x: xs, y: ys, line: {{ color: PALETTE[i % PALETTE.length], width: 1.5 }},
      hovertemplate: "%{{fullData.name}}<br>%{{x}}: R$ %{{y:.2f}} mi<extra></extra>",
    }};
  }});
  Plotly.react("chart-vcr-serie", vcr_traces.length ? vcr_traces : [{{ x: [], y: [], type: "scatter" }}], {{
    margin: {{ l: 60, r: 20, t: 10, b: 30 }},
    xaxis: {{ title: "Ano" }},
    yaxis: {{ title: "VCR (R$ milhões)" }},
    legend: {{ font: {{ size: 9 }} }},
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: {{ family: "system-ui", size: 11 }},
  }}, {{ responsive: true }});

  // ─ RANKING QL_CRED ─
  const ql_ent   = Object.entries(ql_map).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]).slice(0, 15);
  const ql_nomes = ql_ent.map(([mid]) => MUNICIPIOS[mid] || mid);
  const ql_vals  = ql_ent.map(([, v]) => v);
  const ql_clrs  = ql_vals.map(v => v >= 1.25 ? "#2D6A4F" : v >= 1 ? "#52B788" : "#B7E4C7");
  Plotly.react("chart-ql-cred", [{{
    type: "bar", orientation: "h",
    x: ql_vals.slice().reverse(), y: ql_nomes.slice().reverse(),
    marker: {{ color: ql_clrs.slice().reverse() }},
    hovertemplate: "%{{y}}<br>QL crédito: %{{x:.3f}}<extra></extra>",
  }}], {{
    margin: {{ l: 160, r: 20, t: 10, b: 30 }},
    xaxis: {{ title: "QL crédito", zeroline: true, zerolinecolor: "#ccc" }},
    yaxis: {{ automargin: true }},
    shapes: [{{ type: "line", x0: 1, x1: 1, y0: -0.5, y1: Math.max(ql_vals.length - 0.5, 0),
                line: {{ color: "#C9A84C", width: 1.5, dash: "dot" }} }}],
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: {{ family: "system-ui", size: 11 }},
  }}, {{ responsive: true }});

  // ─ PRONAF SHARE — evolução anual (média estadual) ─
  const p_anos = Object.keys(((cred.pronaf_share || {{}})[prod] || {{}})).map(Number).sort();
  const p_meds = p_anos.map(a => {{
    const vals = Object.values((((cred.pronaf_share || {{}})[prod] || {{}})[String(a)] || {{}})).filter(v => v != null);
    return vals.length ? +(vals.reduce((s, v) => s + v, 0) / vals.length * 100).toFixed(2) : null;
  }});
  Plotly.react("chart-pronaf", [{{
    type: "bar", x: p_anos, y: p_meds,
    marker: {{ color: "#40916C" }},
    hovertemplate: "Ano %{{x}}<br>Pronaf: %{{y:.1f}}%<extra></extra>",
  }}], {{
    margin: {{ l: 55, r: 20, t: 10, b: 30 }},
    xaxis: {{ title: "Ano" }},
    yaxis: {{ title: "Pronaf share (%)", range: [0, 100] }},
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: {{ family: "system-ui", size: 11 }},
  }}, {{ responsive: true }});

  // ─ ICR — top municípios ─
  const icr_ent   = Object.entries(icr_map).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]).slice(0, 12);
  const icr_nomes = icr_ent.map(([mid]) => MUNICIPIOS[mid] || mid);
  const icr_vals  = icr_ent.map(([, v]) => v);
  if (icr_ent.length === 0) {{
    Plotly.react("chart-icr", [{{ x: [], y: [], type: "bar", orientation: "h" }}], {{
      margin: {{ l: 160, r: 20, t: 30, b: 30 }},
      annotations: [{{ text: "ICR não disponível para esta cadeia", xref: "paper", yref: "paper",
                       x: 0.5, y: 0.5, showarrow: false, font: {{ color: "#999", size: 13 }} }}],
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    }}, {{ responsive: true }});
  }} else {{
    Plotly.react("chart-icr", [{{
      type: "bar", orientation: "h",
      x: icr_vals.slice().reverse(), y: icr_nomes.slice().reverse(),
      marker: {{ color: "#2C6E8A" }},
      hovertemplate: "%{{y}}<br>ICR: %{{x:.4f}}<extra></extra>",
    }}], {{
      margin: {{ l: 160, r: 20, t: 10, b: 30 }},
      xaxis: {{ title: "ICR" }},
      yaxis: {{ automargin: true }},
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {{ family: "system-ui", size: 11 }},
    }}, {{ responsive: true }});
  }}
}}

// ── ANÁLISE ESPACIAL ────────────────────────────────────────────────
const LISA_CLR = {{
  HH:'#d73027', HL:'#fdae61', LH:'#74b9e4', LL:'#4575b4', ns:'#aaaaaa',
}};
const LISA_LBL = {{
  HH:'HH (alto-alto)', HL:'HL (alto-baixo)',
  LH:'LH (baixo-alto)', LL:'LL (baixo-baixo)', ns:'não sig.',
}};
// nd=0, ns=1, LL=2, LH=3, HL=4, HH=5  (zmin=0, zmax=5)
const LISA_ENC = {{ HH:5, HL:4, LH:3, LL:2 }};
const LISA_CSCALE = [
  [0.000,'#eeeeee'],[0.166,'#eeeeee'],
  [0.167,'#aaaaaa'],[0.332,'#aaaaaa'],
  [0.333,'#4575b4'],[0.499,'#4575b4'],
  [0.500,'#74b9e4'],[0.665,'#74b9e4'],
  [0.666,'#fdae61'],[0.832,'#fdae61'],
  [0.833,'#d73027'],[1.000,'#d73027'],
];
let ESPACIAL=null, GEOJSON_MA=null, _espLoading=false, _espReady=false;

async function _loadEspacial() {{
  if (_espLoading || _espReady) return;
  _espLoading = true;
  document.getElementById('esp-load-msg').textContent = 'Buscando dados...';
  try {{
    const [e, g] = await Promise.all([
      fetch('data/espacial.json').then(r => r.json()),
      fetch('data/municipios_ma.geojson').then(r => r.json()),
    ]);
    ESPACIAL = e; GEOJSON_MA = g; _espReady = true;
    document.getElementById('esp-loading').style.display = 'none';
    document.getElementById('esp-content').style.display = '';
    updateEspacial();
  }} catch(err) {{
    _espLoading = false;
    document.getElementById('esp-load-msg').textContent = 'Erro: ' + err.message;
  }}
}}

function updateEspacial() {{
  if (!_espReady) {{ _loadEspacial(); return; }}

  const prod = getProd();
  const anoS = String(getAno());
  const P    = 0.05;

  const mrec  = ((ESPACIAL.moran||{{}})[prod]||{{}})[anoS] || null;
  const lisa  = ((ESPACIAL.lisa ||{{}})[prod]||{{}})[anoS] || {{}};
  const mall  = (ESPACIAL.moran ||{{}})[prod] || {{}};

  // ─ CARDS ─
  document.getElementById('card-moran-i').textContent =
    mrec ? fmt(mrec.I, 4) : '—';
  document.getElementById('card-moran-z').textContent =
    mrec ? fmt(mrec.z, 2) : '—';
  document.getElementById('card-moran-p').textContent =
    mrec ? (mrec.p < 0.001 ? '<0,001' : fmt(mrec.p, 3)) : '—';
  const nhh = Object.values(lisa).filter(v => v.q==='HH' && v.p<P).length;
  document.getElementById('card-hh-count').textContent = nhh || '—';

  // ─ MAPA LISA ─
  if (GEOJSON_MA) {{
    const mids = GEOJSON_MA.features.map(f => f.properties.id);
    const zArr = mids.map(mid => {{
      const v = lisa[mid];
      return (!v) ? 0 : (v.p < P ? (LISA_ENC[v.q]||1) : 1);
    }});
    const hArr = mids.map(mid => {{
      const v = lisa[mid]; const nm = MUNICIPIOS[mid]||mid;
      if (!v) return nm + ': sem dados';
      const cat = v.p < P ? v.q : 'ns';
      return nm+'<br>'+(LISA_LBL[cat]||cat)+
             '<br>QL z: '+v.z.toFixed(2)+' | lag: '+v.lz.toFixed(2)+
             '<br>p: '+v.p.toFixed(3);
    }});
    Plotly.react('chart-lisa-map', [{{
      type:'choropleth', geojson:GEOJSON_MA, locations:mids, z:zArr,
      featureidkey:'properties.id', text:hArr,
      hovertemplate:'%{{text}}<extra></extra>',
      colorscale:LISA_CSCALE, zmin:0, zmax:5, showscale:false,
      marker:{{ line:{{ color:'#fff', width:0.4 }} }},
    }}], {{
      geo:{{
        showframe:false, showcoastlines:false,
        showland:true, landcolor:'#f7faf8', showlakes:false,
        fitbounds:'locations', projection:{{ type:'mercator' }},
      }},
      margin:{{ l:0, r:0, t:0, b:0 }},
      paper_bgcolor:'rgba(0,0,0,0)',
    }}, {{responsive:true}});
  }}

  // ─ DISPERSÃO DE MORAN ─
  const sc_traces = ['HH','HL','LH','LL','ns'].map(cat => {{
    const pts = Object.entries(lisa).filter(([,v]) =>
      cat==='ns' ? v.p>=P : (v.q===cat && v.p<P));
    return {{
      type:'scatter', mode:'markers', name:LISA_LBL[cat]||cat,
      x:pts.map(([,v])=>v.z), y:pts.map(([,v])=>v.lz),
      text:pts.map(([mid])=>MUNICIPIOS[mid]||mid),
      marker:{{ color:LISA_CLR[cat]||'#ccc', size:6, opacity:.8,
                line:{{ color:'#fff', width:.5 }} }},
      hovertemplate:'%{{text}}<br>z: %{{x:.2f}} | lag: %{{y:.2f}}<extra></extra>',
    }};
  }}).filter(t => t.x.length>0);
  Plotly.react('chart-moran-scatter',
    sc_traces.length ? sc_traces : [{{x:[],y:[],type:'scatter'}}],
  {{
    margin:{{l:55,r:20,t:10,b:40}},
    xaxis:{{title:'QL padronizado (z)',zeroline:true,zerolinecolor:'#bbb',zerolinewidth:1.5}},
    yaxis:{{title:'Defasagem espacial (lag z)',zeroline:true,zerolinecolor:'#bbb',zerolinewidth:1.5}},
    legend:{{font:{{size:9}}}},
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'system-ui',size:11}},
  }},{{responsive:true}});

  // ─ SÉRIE HISTÓRICA MORAN I ─
  const m_anos = Object.keys(mall).map(Number).sort();
  const m_I    = m_anos.map(a=>(mall[String(a)]||{{}}).I);
  const m_clr  = m_anos.map(a=>((mall[String(a)]||{{}}).p<P?'#2D6A4F':'#B7E4C7'));
  Plotly.react('chart-moran-serie',[{{
    type:'scatter', mode:'lines+markers', name:'I de Moran',
    x:m_anos, y:m_I,
    line:{{color:'#52B788',width:1.5}},
    marker:{{color:m_clr,size:8,line:{{color:'#fff',width:1}}}},
    hovertemplate:'%{{x}}<br>I: %{{y:.4f}}<extra></extra>',
  }}],{{
    margin:{{l:55,r:20,t:10,b:30}},
    xaxis:{{title:'Ano'}},
    yaxis:{{title:'I de Moran',zeroline:true,zerolinecolor:'#C9A84C',zerolinewidth:1.5}},
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'system-ui',size:11}},
  }},{{responsive:true}});

  // ─ RANKING HH — APL CANDIDATOS ─
  const ql_ano = (IND.ql[prod]||{{}})[anoS] || {{}};
  const hh_ent = Object.entries(lisa)
    .filter(([,v])=>v.q==='HH'&&v.p<P)
    .map(([mid])=>([mid, ql_ano[mid]]))
    .filter(([,q])=>q!=null)
    .sort((a,b)=>b[1]-a[1]).slice(0,15);
  if (!hh_ent.length) {{
    Plotly.react('chart-hh-bar',[{{x:[],y:[],type:'bar',orientation:'h'}}],{{
      margin:{{l:160,r:20,t:30,b:30}},
      annotations:[{{text:'Sem municípios HH sig. neste ano/cadeia',
                     xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false,
                     font:{{color:'#999',size:13}}}}],
      paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    }},{{responsive:true}});
  }} else {{
    const hh_nomes=hh_ent.map(([mid])=>MUNICIPIOS[mid]||mid);
    const hh_vals =hh_ent.map(([,q])=>q);
    Plotly.react('chart-hh-bar',[{{
      type:'bar',orientation:'h',
      x:hh_vals.slice().reverse(), y:hh_nomes.slice().reverse(),
      marker:{{color:'#d73027'}},
      hovertemplate:'%{{y}}<br>QL: %{{x:.3f}}<extra></extra>',
    }}],{{
      margin:{{l:160,r:20,t:10,b:30}},
      xaxis:{{title:'QL',zeroline:true,zerolinecolor:'#ccc'}},
      yaxis:{{automargin:true}},
      shapes:[{{type:'line',x0:1,x1:1,y0:-0.5,y1:hh_vals.length-0.5,
                line:{{color:'#C9A84C',width:1.5,dash:'dot'}}}}],
      paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
      font:{{family:'system-ui',size:11}},
    }},{{responsive:true}});
  }}
}}

// ── TABS ──────────────────────────────────────────────────────────
function switchTab(tabId) {{
  document.querySelectorAll('.ocas-tab').forEach(t => {{
    const isActive = t.dataset.tab === tabId;
    t.classList.toggle('active', isActive);
    t.setAttribute('aria-selected', isActive);
  }});
  document.querySelectorAll('.ocas-tab-panel').forEach(p => {{
    p.classList.toggle('active', p.id === 'tab-' + tabId);
  }});
  // Redesenha gráficos Plotly ao tornar a tab ativa
  window.dispatchEvent(new Event('resize'));
  if (tabId === 'producao') update();
  else if (tabId === 'credito')  updateCredito();
  else if (tabId === 'espacial') updateEspacial();
}}

// ── INICIALIZAÇÃO ─────────────────────────────────────────────────
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
