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
    fig_json   = json.dumps(fig.to_dict(),  separators=(",", ":"))
    data_json  = json.dumps(js_data,         separators=(",", ":"))
    mid_json   = json.dumps(mid_list,        separators=(",", ":"))
    names_json = json.dumps(name_map,        separators=(",", ":"))

    first_key = available_keys[0]
    n_cadeias = len(available_keys)
    all_years = [y for p in js_data.values() for y in p["anos"]]
    serie     = f"{min(all_years)}–{max(all_years)}"

    meses_pt    = ["","Jan.","Fev.","Mar.","Abr.","Mai.","Jun.","Jul.","Ago.","Set.","Out.","Nov.","Dez."]
    now         = datetime.now()
    update_date = f"{meses_pt[now.month]} {now.year}"

    # Agrupa produtos por grupo preservando ordem de inserção
    groups: dict[str, list] = {}
    for k in available_keys:
        g = PRODUCTS[k]["group"]
        groups.setdefault(g, []).append(k)
    parts = []
    for g, keys in groups.items():
        parts.append(f'          <optgroup label="{g}">'  )
        for k in keys:
            parts.append(f'            <option value="{k}">{js_data[k]["label"]}</option>')
        parts.append( '          </optgroup>')
    prod_options = "\n".join(parts)

    template = (Path(__file__).parent / "templates" / "dashboard.html").read_text(encoding="utf-8")

    return (template
        .replace("__PD_JSON__",      data_json)
        .replace("__MIDS_JSON__",    mid_json)
        .replace("__NMAP_JSON__",    names_json)
        .replace("__FIG_JSON__",     fig_json)
        .replace("__FIRST_KEY__",    first_key)
        .replace("__N_CADEIAS__",    str(n_cadeias))
        .replace("__SERIE__",        serie)
        .replace("__PROD_OPTIONS__", prod_options)
        .replace("__UPDATE_DATE__",  update_date)
    )


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
