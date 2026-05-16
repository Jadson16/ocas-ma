"""
Gera o painel geoespacial do OCAS-MA como site institucional completo.
Saída: index.html pronto para GitHub Pages.
"""

import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# ------------------------------------------------------------------
# Catálogo de produtos — adicionar novas cadeias aqui
# ------------------------------------------------------------------
def _p(group, label, csv_rel, qty_col, val_col, unit_qty, unit_val, fonte):
    return {"group": group, "label": label, "csv": DATA_DIR / csv_rel,
            "qty_col": qty_col, "val_col": val_col,
            "unit_qty": unit_qty, "unit_val": unit_val, "fonte": fonte}

_EVS = "PEVS — Extrativismo Vegetal"
_PAT = "PAM — Lavouras Temporárias"
_PAP = "PAM — Lavouras Permanentes"
_PPP = "PPM — Produção Animal"
_PPR = "PPM — Rebanhos"

PRODUCTS = {
    # --- PEVS ---
    "babacu":        _p(_EVS, "Babaçu (amêndoa)",        "babacu/babacau_pevs.csv",             "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    "acai":          _p(_EVS, "Açaí (extrativista)",      "acai/acai_pevs.csv",                  "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    "buriti":        _p(_EVS, "Buriti (fibra)",           "buriti/buriti_pevs.csv",              "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    "carnauba":      _p(_EVS, "Carnaúba (cera)",          "carnauba/carnauba_pevs.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    "carnauba_fibra":_p(_EVS, "Carnaúba (fibra/folha)",  "carnauba_fibra/carnauba_fibra_pevs.csv","quantidade_ton",       "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    "piacava":       _p(_EVS, "Piaçava (fibra)",          "piacava/piacava_pevs.csv",             "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PEVS/IBGE"),
    # --- PAM temporárias ---
    "arroz":         _p(_PAT, "Arroz (em casca)",         "arroz/arroz_pam.csv",                 "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "feijao":        _p(_PAT, "Feijão (em grão)",         "feijao/feijao_pam.csv",               "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "mandioca":      _p(_PAT, "Mandioca",                 "mandioca/mandioca_pam.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "milho":         _p(_PAT, "Milho (em grão)",          "milho/milho_pam.csv",                 "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "soja":          _p(_PAT, "Soja (em grão)",           "soja/soja_pam.csv",                   "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "cana":          _p(_PAT, "Cana-de-açúcar",           "cana/cana_pam.csv",                   "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "melancia":      _p(_PAT, "Melancia",                 "melancia/melancia_pam.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "amendoim":      _p(_PAT, "Amendoim (em casca)",      "amendoim/amendoim_pam.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "algodao":       _p(_PAT, "Algodão herbáceo",         "algodao/algodao_pam.csv",             "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    # --- PAM permanentes ---
    "banana":        _p(_PAP, "Banana (cacho)",           "banana/banana_pam.csv",               "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "castanha_caju": _p(_PAP, "Castanha de caju",         "castanha_caju/castanha_caju_pam.csv", "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "coco":          _p(_PAP, "Coco-da-baía",             "coco/coco_pam.csv",                   "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "laranja":       _p(_PAP, "Laranja",                  "laranja/laranja_pam.csv",             "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "acai_cult":     _p(_PAP, "Açaí (cultivado)",         "acai_cult/acai_cult_pam.csv",         "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "mamao":         _p(_PAP, "Mamão",                    "mamao/mamao_pam.csv",                 "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "manga":         _p(_PAP, "Manga",                    "manga/manga_pam.csv",                 "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "maracuja":      _p(_PAP, "Maracujá",                 "maracuja/maracuja_pam.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    "borracha":      _p(_PAP, "Borracha (látex)",         "borracha/borracha_pam.csv",           "quantidade_ton",        "valor_mil_reais", "t",       "mil R$", "PAM/IBGE"),
    # --- PPM produção ---
    "mel":           _p(_PPP, "Mel de abelha",            "mel/mel_ppm.csv",                     "quantidade_kg",         "valor_mil_reais", "kg",      "mil R$", "PPM/IBGE"),
    "leite":         _p(_PPP, "Leite de vaca",            "leite/leite_ppm.csv",                 "quantidade_mil_litros", "valor_mil_reais", "mil l",   "mil R$", "PPM/IBGE"),
    "ovos":          _p(_PPP, "Ovos de galinha",          "ovos/ovos_ppm.csv",                   "quantidade_mil_duzias", "valor_mil_reais", "mil dz",  "mil R$", "PPM/IBGE"),
    # --- PPM rebanhos (sem valor) ---
    "bovino":    _p(_PPR, "Bovino",    "bovino/bovino_ppm.csv",       "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "bubalino":  _p(_PPR, "Bubalino", "bubalino/bubalino_ppm.csv",   "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "equino":    _p(_PPR, "Equino",   "equino/equino_ppm.csv",       "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "suino":     _p(_PPR, "Suíno",    "suino/suino_ppm.csv",         "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "caprino":   _p(_PPR, "Caprino",  "caprino/caprino_ppm.csv",     "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "ovino":     _p(_PPR, "Ovino",    "ovino/ovino_ppm.csv",         "efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
    "galinaceo": _p(_PPR, "Galináceos","galinaceo/galinaceo_ppm.csv","efetivo_cabecas", None, "cabeças", None, "PPM/IBGE"),
}


# ------------------------------------------------------------------
# GEO
# ------------------------------------------------------------------
def load_geodata():
    with open(DATA_DIR / "municipios_ma.geojson", encoding="utf-8") as f:
        geojson = json.load(f)
    with open(DATA_DIR / "maranhao_estado.geojson", encoding="utf-8") as f:
        estado = json.load(f)
    mid_list = [feat["properties"]["id"] for feat in geojson["features"]]
    name_map = {feat["properties"]["id"]: feat["properties"]["name"]
                for feat in geojson["features"]}
    return geojson, estado, mid_list, name_map


def _estado_coords(estado_geojson):
    lats, lons = [], []
    for feat in estado_geojson["features"]:
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                lons += [c[0] for c in ring] + [None]
                lats += [c[1] for c in ring] + [None]
    return lats, lons


# ------------------------------------------------------------------
# DATA
# ------------------------------------------------------------------
def load_all_products(mid_list, name_map):
    """Carrega todos os produtos disponíveis e retorna estrutura para o JS."""
    available = {k: v for k, v in PRODUCTS.items() if v["csv"].exists()}
    missing = [k for k in PRODUCTS if k not in available]
    if missing:
        print(f"Produtos sem CSV (ignorados): {missing}")

    js_data = {}
    for key, cfg in available.items():
        df = pd.read_csv(cfg["csv"], dtype={"municipio_id": str})
        years = sorted(int(y) for y in df["ano"].unique())

        has_val   = cfg["val_col"] is not None
        qty_pivot = df.pivot(index="municipio_id", columns="ano", values=cfg["qty_col"])
        val_pivot = df.pivot(index="municipio_id", columns="ano", values=cfg["val_col"]) if has_val else None

        qty_by_year, val_by_year = {}, {}
        rank_qty, rank_val = {}, {}

        for year in years:
            qz, vz, rq, rv = [], [], [], []
            for mid in mid_list:
                has_q = mid in qty_pivot.index and year in qty_pivot.columns
                q = qty_pivot.at[mid, year] if has_q else None
                q = None if (q is not None and pd.isna(q)) else q
                qz.append(q)
                if q is not None:
                    rq.append({"mun": name_map[mid], "val": q})

                if has_val:
                    has_v = mid in val_pivot.index and year in val_pivot.columns
                    v = val_pivot.at[mid, year] if has_v else None
                    v = None if (v is not None and pd.isna(v)) else v
                    vz.append(v)
                    if v is not None:
                        rv.append({"mun": name_map[mid], "val": v})
                else:
                    vz.append(None)

            qty_by_year[year] = qz
            val_by_year[year] = vz
            rank_qty[year] = sorted(rq, key=lambda x: x["val"], reverse=True)[:10]
            rank_val[year] = sorted(rv, key=lambda x: x["val"], reverse=True)[:10]

        all_q = [v for z in qty_by_year.values() for v in z if v is not None]
        all_v = [v for z in val_by_year.values() for v in z if v is not None]

        js_data[key] = {
            "label":         cfg["label"],
            "fonte":         cfg["fonte"],
            "unit_qty":      cfg["unit_qty"],
            "unit_val":      cfg["unit_val"],
            "has_val":       has_val,
            "anos":          years,
            "qty":           qty_by_year,
            "val":           val_by_year,
            "color_max_qty": float(pd.Series(all_q).quantile(0.97)),
            "color_max_val": float(pd.Series(all_v).quantile(0.97)) if all_v else 0,
            "ranking_qty":   rank_qty,
            "ranking_val":   rank_val,
        }

    return js_data, list(available.keys())


# ------------------------------------------------------------------
# PLOTLY FIGURE (mapa base sem controles)
# ------------------------------------------------------------------
def build_fig(geojson, estado_geojson, mid_list, js_data, first_key):
    estado_lats, estado_lons = _estado_coords(estado_geojson)
    prod = js_data[first_key]
    latest = prod["anos"][-1]
    z0 = prod["qty"][latest]

    fig = go.Figure([
        go.Choroplethmap(
            geojson=geojson,
            locations=mid_list,
            featureidkey="properties.id",
            z=z0,
            colorscale="YlOrRd",
            zmin=0,
            zmax=prod["color_max_qty"],
            marker_opacity=0.7,
            marker_line_width=0.5,
            hoverinfo="none",
            colorbar=dict(
                title=dict(text="Quantidade<br>(t)"),
                thickness=12,
                len=0.5,
                x=0.01,
                xanchor="left",
            ),
        ),
        go.Scattermap(
            lat=estado_lats,
            lon=estado_lons,
            mode="lines",
            line=dict(color="#1a1a1a", width=0.8),
            hoverinfo="skip",
            showlegend=False,
        ),
    ])

    fig.update_layout(
        map_style="carto-positron",
        map_center={"lat": -5.0, "lon": -44.5},
        map_zoom=5.5,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ------------------------------------------------------------------
# HTML
# ------------------------------------------------------------------
def build_html(fig, js_data, available_keys, mid_list, name_map):
    fig_json     = json.dumps(fig.to_dict(),   separators=(",", ":"))
    data_json    = json.dumps(js_data,          separators=(",", ":"))
    mid_json     = json.dumps(mid_list,         separators=(",", ":"))
    names_json   = json.dumps(name_map,         separators=(",", ":"))

    first_key   = available_keys[0]
    n_cadeias   = len(available_keys)
    all_years   = [y for p in js_data.values() for y in p["anos"]]
    serie       = f"{min(all_years)}–{max(all_years)}"
    update_date = datetime.now().strftime("%b. %Y")

    # Agrupa produtos por grupo preservando ordem de inserção
    groups: dict[str, list] = {}
    for k in available_keys:
        g = PRODUCTS[k]["group"]
        groups.setdefault(g, []).append(k)
    parts = []
    for g, keys in groups.items():
        parts.append(f'          <optgroup label="{g}">')
        for k in keys:
            parts.append(f'            <option value="{k}">{js_data[k]["label"]}</option>')
        parts.append(f'          </optgroup>')
    prod_options = "\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCAS-MA — Observatório de Cadeias, Arranjos e Sustentabilidade do Maranhão</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cpolygon points='32,4 56,18 56,46 32,60 8,46 8,18' fill='none' stroke='%232D6A4F' stroke-width='2.5'/%3E%3Ccircle cx='32' cy='32' r='7' fill='%2352B788'/%3E%3C/svg%3E">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
    :root {{
      --ocas-floresta:    #1B4332;
      --ocas-mata:        #2D6A4F;
      --ocas-igapo:       #40916C;
      --ocas-babacu:      #52B788;
      --ocas-buriti:      #74C69D;
      --ocas-varzea:      #D8F3DC;
      --ocas-bg-page:     #F7FAF8;
      --ocas-bg-header:   #ffffff;
      --ocas-bg-card:     #ffffff;
      --ocas-bg-nav:      #F7FAF8;
      --ocas-border:      #ddeee5;
      --ocas-border-soft: #c8e0d0;
      --ocas-cerrado:     #C9A84C;
      --ocas-rio:         #2C6E8A;
      --ocas-font-titulo: Georgia, 'Times New Roman', serif;
      --ocas-font-label:  'Courier New', Courier, monospace;
      --ocas-font-dados:  system-ui, -apple-system, sans-serif;
      --ocas-radius-sm:   6px;
      --ocas-radius-md:   10px;
      --ocas-shadow-card: 0 1px 3px rgba(27,67,50,.06);
    }}
    *  {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--ocas-bg-page); font-family: var(--ocas-font-dados); color: #222; }}

    /* HEADER */
    .ocas-header {{ background: var(--ocas-bg-header); border-bottom: 1px solid var(--ocas-border); padding: 18px 28px; }}
    .ocas-header-inner {{ display: flex; align-items: center; justify-content: space-between; max-width: 1400px; margin: 0 auto; }}
    .ocas-brand {{ display: flex; align-items: center; gap: 16px; }}
    .ocas-brand-text {{ display: flex; flex-direction: column; gap: 2px; }}
    .ocas-sigla {{ font-family: var(--ocas-font-titulo); font-size: 22px; font-weight: 700; color: var(--ocas-floresta); letter-spacing: 1px; line-height: 1; }}
    .ocas-vinculo {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: var(--ocas-igapo); }}
    .ocas-header-meta {{ font-family: var(--ocas-font-label); font-size: 10px; color: var(--ocas-igapo); text-align: right; line-height: 1.8; }}
    .ocas-status {{ color: var(--ocas-babacu); margin-left: 6px; }}

    /* NAV */
    .ocas-nav {{ background: var(--ocas-bg-nav); border-bottom: 1px solid var(--ocas-border); display: flex; padding: 0 28px; overflow-x: auto; }}
    .ocas-nav-item {{ padding: 10px 16px; font-family: var(--ocas-font-label); font-size: 11px; letter-spacing: .5px; color: var(--ocas-buriti); text-decoration: none; border-bottom: 2px solid transparent; transition: color .2s, border-color .2s; white-space: nowrap; }}
    .ocas-nav-item:hover {{ color: var(--ocas-mata); }}
    .ocas-nav-item.active {{ color: var(--ocas-mata); border-bottom-color: var(--ocas-mata); }}

    /* CARDS */
    .ocas-cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 12px; padding: 20px 28px; max-width: 1400px; margin: 0 auto; }}
    .ocas-card {{ background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); border-left: 2px solid var(--ocas-mata); padding: 16px 18px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-card--cerrado {{ border-left-color: var(--ocas-cerrado); }}
    .ocas-card--rio     {{ border-left-color: var(--ocas-rio); }}
    .ocas-card-label {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); margin-bottom: 6px; }}
    .ocas-card--cerrado .ocas-card-label {{ color: var(--ocas-cerrado); }}
    .ocas-card--rio     .ocas-card-label {{ color: var(--ocas-rio); }}
    .ocas-card-value {{ font-family: var(--ocas-font-titulo); font-size: 26px; font-weight: 500; color: var(--ocas-floresta); line-height: 1.1; }}
    .ocas-card-desc  {{ font-family: var(--ocas-font-dados); font-size: 10px; color: var(--ocas-buriti); margin-top: 4px; }}

    /* SECTION */
    .ocas-section {{ max-width: 1400px; margin: 0 auto; padding: 24px 28px; }}
    .ocas-section-title {{ font-family: var(--ocas-font-titulo); font-size: 18px; color: var(--ocas-floresta); margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--ocas-border); }}
    .ocas-section-text {{ max-width: 820px; line-height: 1.7; font-size: 14px; color: #333; }}
    .ocas-section-text p {{ margin-bottom: 12px; }}
    .ocas-section--alt {{ background: var(--ocas-varzea); border-top: 1px solid var(--ocas-border); border-bottom: 1px solid var(--ocas-border); }}

    /* CONTROLS */
    .ocas-controls {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; margin-bottom: 16px; }}
    .ocas-control-group {{ display: flex; flex-direction: column; gap: 5px; }}
    .ocas-control-label {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); }}
    .ocas-select {{ font-family: var(--ocas-font-dados); font-size: 13px; color: var(--ocas-floresta); background: var(--ocas-bg-card); border: 1px solid var(--ocas-border-soft); border-radius: var(--ocas-radius-sm); padding: 7px 12px; cursor: pointer; outline: none; }}
    .ocas-select:focus {{ border-color: var(--ocas-mata); }}
    .ocas-toggle {{ display: flex; border: 1px solid var(--ocas-border-soft); border-radius: var(--ocas-radius-sm); overflow: hidden; }}
    .ocas-toggle-btn {{ padding: 7px 16px; font-family: var(--ocas-font-label); font-size: 10px; letter-spacing: .5px; background: var(--ocas-bg-card); color: var(--ocas-igapo); border: none; cursor: pointer; transition: background .15s, color .15s; }}
    .ocas-toggle-btn.active {{ background: var(--ocas-mata); color: #fff; }}
    .ocas-toggle-btn:hover:not(.active) {{ background: var(--ocas-varzea); }}
    .ocas-slider-wrap {{ flex: 1; min-width: 200px; }}
    .ocas-year-display {{ font-family: var(--ocas-font-titulo); font-size: 22px; font-weight: 500; color: var(--ocas-floresta); margin-bottom: 4px; }}
    .ocas-slider {{ width: 100%; accent-color: var(--ocas-mata); cursor: pointer; }}
    .ocas-slider-labels {{ display: flex; justify-content: space-between; font-family: var(--ocas-font-label); font-size: 9px; color: var(--ocas-buriti); margin-top: 2px; }}

    /* MAP + RANKING */
    .ocas-map-wrap {{ display: grid; grid-template-columns: 1fr 280px; gap: 16px; align-items: start; }}
    @media (max-width: 900px) {{ .ocas-map-wrap {{ grid-template-columns: 1fr; }} }}
    #map-container {{ width: 100%; height: 580px; border-radius: var(--ocas-radius-md); overflow: hidden; border: .5px solid var(--ocas-border); }}
    .ocas-fonte {{ font-family: var(--ocas-font-label); font-size: 9px; color: var(--ocas-buriti); margin-top: 6px; text-align: right; }}

    /* RANKING */
    .ocas-ranking {{ background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); padding: 16px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-ranking-title {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); margin-bottom: 12px; }}
    .ocas-ranking table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    .ocas-ranking th {{ font-family: var(--ocas-font-label); font-size: 8px; letter-spacing: 1px; text-transform: uppercase; color: var(--ocas-buriti); padding: 4px 6px; text-align: left; border-bottom: 1px solid var(--ocas-border); }}
    .ocas-ranking td {{ padding: 6px 6px; color: var(--ocas-floresta); border-bottom: .5px solid var(--ocas-border); font-size: 11px; }}
    .ocas-ranking td:last-child {{ text-align: right; font-family: var(--ocas-font-label); font-size: 10px; color: var(--ocas-mata); }}
    .ocas-ranking tr:last-child td {{ border-bottom: none; }}
    .rank-pos {{ color: var(--ocas-buriti); font-size: 9px; width: 18px; }}

    /* DOWNLOAD */
    .ocas-btn-download {{ font-family: var(--ocas-font-label); font-size: 10px; letter-spacing: .5px; padding: 7px 14px; background: var(--ocas-bg-card); color: var(--ocas-mata); border: 1px solid var(--ocas-border-soft); border-radius: var(--ocas-radius-sm); cursor: pointer; transition: background .15s; white-space: nowrap; }}
    .ocas-btn-download:hover {{ background: var(--ocas-varzea); }}

    /* TIME SERIES */
    .ocas-ts-wrap {{ margin-top: 20px; background: var(--ocas-bg-card); border: .5px solid var(--ocas-border); border-radius: var(--ocas-radius-md); padding: 16px 18px; box-shadow: var(--ocas-shadow-card); }}
    .ocas-ts-title {{ font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--ocas-igapo); margin-bottom: 8px; }}
    #ts-container {{ width: 100%; height: 220px; }}

    /* FOOTER */
    .ocas-footer {{ padding: 16px 28px; font-family: var(--ocas-font-label); font-size: 9px; letter-spacing: 1px; color: var(--ocas-buriti); border-top: .5px solid var(--ocas-border); background: var(--ocas-bg-page); text-align: center; margin-top: 8px; }}
  </style>
</head>
<body>

<!-- HEADER -->
<header class="ocas-header">
  <div class="ocas-header-inner">
    <div class="ocas-brand">
      <svg width="48" height="48" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="OCAS-MA">
        <polygon points="32,4 56,18 56,46 32,60 8,46 8,18" fill="none" stroke="#2D6A4F" stroke-width="2" stroke-linejoin="round"/>
        <circle cx="32" cy="4"  r="3.5" fill="#2D6A4F"/>
        <circle cx="56" cy="18" r="3.5" fill="#2D6A4F"/>
        <circle cx="56" cy="46" r="3.5" fill="#2D6A4F"/>
        <circle cx="32" cy="60" r="3.5" fill="#2D6A4F"/>
        <circle cx="8"  cy="46" r="3.5" fill="#2D6A4F"/>
        <circle cx="8"  cy="18" r="3.5" fill="#2D6A4F"/>
        <circle cx="32" cy="32" r="6"   fill="#52B788"/>
        <line x1="32" y1="26" x2="32" y2="7"  stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
        <line x1="37" y1="29" x2="53" y2="21" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
        <line x1="37" y1="35" x2="53" y2="43" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
        <line x1="32" y1="38" x2="32" y2="57" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
        <line x1="27" y1="35" x2="11" y2="43" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
        <line x1="27" y1="29" x2="11" y2="21" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
      </svg>
      <div class="ocas-brand-text">
        <span class="ocas-sigla">OCAS-MA</span>
        <span class="ocas-vinculo">GEIA &middot; CECON &middot; UFMA</span>
      </div>
    </div>
    <div class="ocas-header-meta">
      Atualiza&ccedil;&atilde;o: {update_date}
      <span class="ocas-status">&#9679; online</span>
    </div>
  </div>
</header>

<!-- NAV -->
<nav class="ocas-nav">
  <a href="#cadeias"     class="ocas-nav-item active">Cadeias</a>
  <a href="#sobre"       class="ocas-nav-item">O que &eacute;</a>
  <a href="#equipe"      class="ocas-nav-item">Quem somos</a>
  <a href="#metodologia" class="ocas-nav-item">Metodologia</a>
  <a href="#boletins"    class="ocas-nav-item">Boletins</a>
</nav>

<!-- STAT CARDS -->
<div class="ocas-cards-grid">
  <div class="ocas-card">
    <div class="ocas-card-label">Munic&iacute;pios</div>
    <div class="ocas-card-value">217</div>
    <div class="ocas-card-desc">cobertura estadual</div>
  </div>
  <div class="ocas-card">
    <div class="ocas-card-label">Cadeias</div>
    <div class="ocas-card-value">{n_cadeias}</div>
    <div class="ocas-card-desc">monitoradas</div>
  </div>
  <div class="ocas-card ocas-card--cerrado">
    <div class="ocas-card-label">Per&iacute;odo</div>
    <div class="ocas-card-value" style="font-size:20px">{serie}</div>
    <div class="ocas-card-desc">s&eacute;rie hist&oacute;rica</div>
  </div>
  <div class="ocas-card ocas-card--rio">
    <div class="ocas-card-label">Fonte</div>
    <div class="ocas-card-value" style="font-size:18px">IBGE</div>
    <div class="ocas-card-desc">PEVS &middot; PAM &middot; PPM</div>
  </div>
</div>

<!-- CADEIAS -->
<section id="cadeias">
  <div class="ocas-section">
    <h2 class="ocas-section-title">Produ&ccedil;&atilde;o por munic&iacute;pio</h2>

    <div class="ocas-controls">
      <div class="ocas-control-group">
        <span class="ocas-control-label">Cadeia produtiva</span>
        <select class="ocas-select" id="prod-select">
{prod_options}
        </select>
      </div>
      <div class="ocas-control-group">
        <span class="ocas-control-label">Vari&aacute;vel</span>
        <div class="ocas-toggle">
          <button class="ocas-toggle-btn active" id="btn-qty" onclick="setVar('qty')">Quantidade</button>
          <button class="ocas-toggle-btn"        id="btn-val" onclick="setVar('val')">Valor (R$)</button>
        </div>
      </div>
      <div class="ocas-control-group ocas-slider-wrap">
        <span class="ocas-control-label">Ano</span>
        <div class="ocas-year-display" id="year-display"></div>
        <input type="range" class="ocas-slider" id="year-slider"
               min="0" max="0" value="0" oninput="onYearChange(this.value)">
        <div class="ocas-slider-labels">
          <span id="slider-min"></span>
          <span id="slider-max"></span>
        </div>
      </div>
      <div class="ocas-control-group" style="justify-content:flex-end;align-self:flex-end">
        <button class="ocas-btn-download" onclick="downloadCSV()">&#8595; Baixar CSV</button>
      </div>
    </div>

    <div class="ocas-map-wrap">
      <div>
        <div id="map-container"></div>
        <div class="ocas-fonte" id="fonte-badge"></div>
      </div>
      <div class="ocas-ranking">
        <div class="ocas-ranking-title" id="ranking-title">Top 10 &middot; Quantidade</div>
        <table>
          <thead><tr><th class="rank-pos">#</th><th>Munic&iacute;pio</th><th>Valor</th></tr></thead>
          <tbody id="ranking-body"></tbody>
        </table>
      </div>
    </div>

    <div class="ocas-ts-wrap">
      <div class="ocas-ts-title" id="ts-title">Evolu&ccedil;&atilde;o estadual &mdash; Quantidade</div>
      <div id="ts-container"></div>
    </div>
  </div>
</section>

<!-- O QUE E -->
<div class="ocas-section--alt" id="sobre">
  <div class="ocas-section">
    <h2 class="ocas-section-title">O que &eacute; o OCAS-MA</h2>
    <div class="ocas-section-text">
      <p>O <strong>Observat&oacute;rio de Cadeias, Arranjos e Sustentabilidade do Maranh&atilde;o (OCAS-MA)</strong> &eacute; uma iniciativa do Grupo de Estudos em Inova&ccedil;&atilde;o e Agroneg&oacute;cio (GEIA), vinculado ao Centro de Ci&ecirc;ncias Econ&ocirc;micas e Administrativas (CECON) da Universidade Federal do Maranh&atilde;o (UFMA).</p>
      <p>Seu objeto de an&aacute;lise s&atilde;o as <strong>cadeias produtivas e arranjos produtivos locais (APLs)</strong> com express&atilde;o territorial no Maranh&atilde;o, monitorados na unidade de an&aacute;lise municipal com cobertura estadual completa.</p>
      <p>O observat&oacute;rio integra, de forma progressiva, dados das dimens&otilde;es <strong>produtiva, socioambiental, de trabalho e de cr&eacute;dito</strong>, a partir de fontes p&uacute;blicas nacionais como IBGE (PEVS, PPM, Censo Agropecu&aacute;rio), CONAB, MapBiomas, RAIS/CAGED e Banco Central do Brasil.</p>
    </div>
  </div>
</div>

<!-- QUEM SOMOS -->
<section id="equipe">
  <div class="ocas-section">
    <h2 class="ocas-section-title">Quem somos</h2>
    <div class="ocas-section-text">
      <p><strong>Coordena&ccedil;&atilde;o:</strong> Prof. Dr. Jadson Pessoa da Silva &mdash; GEIA / CECON / UFMA</p>
      <p>O OCAS-MA &eacute; desenvolvido por pesquisadores e estudantes do GEIA (Grupo de Estudos em Inova&ccedil;&atilde;o e Agroneg&oacute;cio), com apoio institucional do CECON e da UFMA.</p>
    </div>
  </div>
</section>

<!-- METODOLOGIA -->
<div class="ocas-section--alt" id="metodologia">
  <div class="ocas-section">
    <h2 class="ocas-section-title">Metodologia</h2>
    <div class="ocas-section-text">
      <p>Os dados s&atilde;o coletados automaticamente via APIs p&uacute;blicas do IBGE. A s&eacute;rie hist&oacute;rica tem in&iacute;cio em <strong>1995</strong> (primeiro ano completo do Plano Real), evitando incompatibilidades de deflacionamento entre moedas anteriores ao Real.</p>
      <p>Extrativismo vegetal (baba&ccedil;u, a&ccedil;a&iacute;, buriti e outros): <strong>PEVS/IBGE</strong>, tabela 289. Lavouras tempor&aacute;rias e permanentes (arroz, milho, soja, mandioca, banana e outras): <strong>PAM/IBGE</strong>, tabelas 1612 e 1613. Produ&ccedil;&atilde;o animal e rebanhos (leite, ovos, bovinos e outros): <strong>PPM/IBGE</strong>, tabelas 74 e 3939.</p>
      <p>A atualiza&ccedil;&atilde;o do painel &eacute; autom&aacute;tica via GitHub Actions, com execu&ccedil;&atilde;o mensal. O c&oacute;digo-fonte est&aacute; dispon&iacute;vel em <a href="https://github.com/Jadson16/ocas-ma" target="_blank" style="color:var(--ocas-mata)">github.com/Jadson16/ocas-ma</a>.</p>
    </div>
  </div>
</div>

<!-- BOLETINS -->
<section id="boletins">
  <div class="ocas-section">
    <h2 class="ocas-section-title">Boletins</h2>
    <div class="ocas-section-text">
      <p>Os boletins semestrais do OCAS-MA apresentam an&aacute;lises narrativas dos dados do painel geoespacial, com densidade anal&iacute;tica voltada para pesquisadores, gestores p&uacute;blicos, parceiros institucionais e sociedade civil.</p>
      <p style="color:var(--ocas-buriti);font-style:italic">Primeiro boletim em prepara&ccedil;&atilde;o.</p>
    </div>
  </div>
</section>

<!-- FOOTER -->
<footer class="ocas-footer">
  OCAS-MA &middot; Observat&oacute;rio de Cadeias, Arranjos e Sustentabilidade do Maranh&atilde;o &middot; GEIA &mdash; CECON &mdash; UFMA
</footer>

<script>
const PD   = {data_json};
const MIDS = {mid_json};
const NMAP = {names_json};
const FIG  = {fig_json};

let curProd    = "{first_key}";
let curVar     = "qty";
let curYearIdx = 0;

// --- init Plotly ---
Plotly.newPlot("map-container", FIG.data, FIG.layout, {{
  responsive: true, displaylogo: false,
  modeBarButtonsToRemove: ["toImage","sendDataToCloud","lasso2d","select2d"],
}});

// --- helpers ---
function anos()   {{ return PD[curProd].anos; }}
function curYear(){{ return anos()[curYearIdx]; }}

function initControls() {{
  const a = anos();
  const sl = document.getElementById("year-slider");
  sl.min = 0; sl.max = a.length - 1; sl.value = a.length - 1;
  curYearIdx = a.length - 1;
  document.getElementById("slider-min").textContent  = a[0];
  document.getElementById("slider-max").textContent  = a[a.length-1];
  document.getElementById("year-display").textContent = a[curYearIdx];
  document.getElementById("fonte-badge").textContent =
    "Fonte: " + PD[curProd].fonte + " · dados por município";
}}

function updateMap() {{
  const p    = PD[curProd];
  const yr   = curYear();
  const zd   = p[curVar][yr];
  const isQ  = curVar === "qty";
  const unit = isQ ? p.unit_qty : p.unit_val;
  const cmax = isQ ? p.color_max_qty : p.color_max_val;
  const lbl  = isQ ? "Produção" : "Valor";

  const text = MIDS.map((mid, i) => {{
    const nm = NMAP[mid];
    const v  = zd[i];
    if (v === null || v === undefined)
      return "<b>" + nm + "</b><br>Sem dados registrados";
    return "<b>" + nm + "</b><br>" + lbl + ": " +
           v.toLocaleString("pt-BR", {{maximumFractionDigits: 0}}) + " " + unit;
  }});

  Plotly.restyle("map-container", {{
    z:                   [zd],
    text:                [text],
    hovertemplate:       "%{{text}}<extra></extra>",
    zmax:                cmax,
    "colorbar.title.text": lbl + "<br>(" + unit + ")",
  }}, [0]);
}}

function updateRanking() {{
  const p    = PD[curProd];
  const yr   = curYear();
  const key  = "ranking_" + curVar;
  const rows = p[key][yr] || [];
  const unit = curVar === "qty" ? p.unit_qty : p.unit_val;
  const lbl  = curVar === "qty" ? "Quantidade" : "Valor";

  document.getElementById("ranking-title").textContent =
    "Top 10 · " + lbl + " · " + yr;

  document.getElementById("ranking-body").innerHTML = rows.map((r, i) => {{
    const fmt = r.val.toLocaleString("pt-BR", {{maximumFractionDigits: 0}});
    const nm  = r.mun.replace(" - MA", "");
    return `<tr><td class="rank-pos">${{i+1}}</td><td>${{nm}}</td><td>${{fmt}} ${{unit}}</td></tr>`;
  }}).join("");
}}

function updateTimeseries() {{
  const p    = PD[curProd];
  const isQ  = curVar === "qty";
  const unit = isQ ? p.unit_qty : p.unit_val;
  const lbl  = isQ ? "Quantidade" : "Valor";
  const anos = p.anos;

  const totals = anos.map(yr => {{
    const zd = p[curVar][yr];
    return zd.reduce((s, v) => s + (v != null ? v : 0), 0);
  }});

  document.getElementById("ts-title").textContent =
    "Evolução estadual — " + lbl + " (" + unit + ")";

  Plotly.react("ts-container", [{{
    x: anos, y: totals, type: "scatter", mode: "lines+markers",
    line:   {{ color: "#2D6A4F", width: 2 }},
    marker: {{ color: "#52B788", size: 5 }},
    hovertemplate: "<b>%{{x}}</b><br>" + lbl + ": %{{y:,.0f}} " + unit + "<extra></extra>",
  }}], {{
    margin: {{ t: 8, r: 16, b: 36, l: 72 }},
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor:  "#F7FAF8",
    xaxis: {{ showgrid: false, tickfont: {{ size: 10 }} }},
    yaxis: {{ tickfont: {{ size: 10 }}, tickformat: ",.0f" }},
    height: 220,
    shapes: [{{
      type: "line", xref: "x", yref: "paper",
      x0: curYear(), x1: curYear(), y0: 0, y1: 1,
      line: {{ color: "#C9A84C", width: 1.5, dash: "dot" }},
    }}],
  }}, {{ responsive: true, displaylogo: false, staticPlot: false,
         modeBarButtonsToRemove: ["toImage","lasso2d","select2d"] }});
}}

function downloadCSV() {{
  const p   = PD[curProd];
  const isQ = curVar === "qty";
  const col = isQ ? "quantidade_" + p.unit_qty.replace(" ","_") : "valor_mil_reais";
  const rows = [["municipio_id","municipio","ano", col]];
  p.anos.forEach(yr => {{
    const zd = p[curVar][yr];
    MIDS.forEach((mid, i) => {{
      if (zd[i] != null)
        rows.push([mid, NMAP[mid].replace(" - MA",""), yr, zd[i]]);
    }});
  }});
  const csv  = rows.map(r => r.join(",")).join("\\r\\n");
  const blob = new Blob(["\\ufeff" + csv], {{ type: "text/csv;charset=utf-8;" }});
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement("a"),
                 {{ href: url, download: "ocas-ma_" + curProd + ".csv" }});
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}}

function update() {{ updateMap(); updateRanking(); updateTimeseries(); }}

function onYearChange(idx) {{
  curYearIdx = parseInt(idx);
  document.getElementById("year-display").textContent = curYear();
  update();
}}

function syncValBtn() {{
  const hv = PD[curProd].has_val;
  const btn = document.getElementById("btn-val");
  btn.disabled = !hv;
  btn.style.opacity = hv ? "1" : "0.35";
  btn.style.cursor  = hv ? "pointer" : "not-allowed";
  if (!hv && curVar === "val") {{ curVar = "qty"; }}
  document.getElementById("btn-qty").classList.toggle("active", curVar === "qty");
  document.getElementById("btn-val").classList.toggle("active", curVar === "val");
}}

function setVar(v) {{
  if (!PD[curProd].has_val && v === "val") return;
  curVar = v;
  syncValBtn();
  update();
}}

document.getElementById("prod-select").addEventListener("change", function() {{
  curProd = this.value;
  curVar  = "qty";
  syncValBtn();
  initControls();
  update();
}});

// nav active on scroll
const secs = document.querySelectorAll("section[id], div[id]");
const navs = document.querySelectorAll(".ocas-nav-item");
window.addEventListener("scroll", () => {{
  let cur = "";
  secs.forEach(s => {{ if (window.scrollY >= s.offsetTop - 80) cur = s.id; }});
  navs.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + cur));
}});

syncValBtn();
initControls();
update();
</script>
</body>
</html>"""


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    geojson, estado_geojson, mid_list, name_map = load_geodata()
    js_data, available_keys = load_all_products(mid_list, name_map)

    fig  = build_fig(geojson, estado_geojson, mid_list, js_data, available_keys[0])
    html = build_html(fig, js_data, available_keys, mid_list, name_map)

    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")

    size_kb = out.stat().st_size / 1024
    print(f"Site salvo  : {out}")
    print(f"Tamanho     : {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")
    print(f"Produtos    : {available_keys}")


if __name__ == "__main__":
    main()
