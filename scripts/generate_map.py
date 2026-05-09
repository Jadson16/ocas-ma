"""
Gera o painel geoespacial do OCAS-MA.
Saída: index.html pronto para GitHub Pages.

Para adicionar uma nova cadeia produtiva, basta incluir uma entrada em PRODUCTS.
"""

import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# ------------------------------------------------------------------
# Catálogo de produtos — adicionar novas cadeias aqui
# ------------------------------------------------------------------
PRODUCTS = {
    "babacu": {
        "label": "Babaçu (amêndoa)",
        "csv": DATA_DIR / "babacu" / "babacau_pevs.csv",
        "qty_col": "quantidade_ton",
        "val_col": "valor_mil_reais",
        "unit": "t",
        "fonte": "PEVS/IBGE",
    },
    "acai": {
        "label": "Açaí (bagas)",
        "csv": DATA_DIR / "acai" / "acai_pevs.csv",
        "qty_col": "quantidade_ton",
        "val_col": "valor_mil_reais",
        "unit": "t",
        "fonte": "PEVS/IBGE",
    },
    "mel": {
        "label": "Mel de abelha",
        "csv": DATA_DIR / "mel" / "mel_ppm.csv",
        "qty_col": "quantidade_kg",
        "val_col": "valor_mil_reais",
        "unit": "kg",
        "fonte": "PPM/IBGE",
    },
}


def load_geodata():
    with open(DATA_DIR / "municipios_ma.geojson", encoding="utf-8") as f:
        geojson = json.load(f)
    with open(DATA_DIR / "maranhao_estado.geojson", encoding="utf-8") as f:
        estado = json.load(f)
    mid_list = [feat["properties"]["id"] for feat in geojson["features"]]
    name_map = {feat["properties"]["id"]: feat["properties"]["name"]
                for feat in geojson["features"]}
    return geojson, estado, mid_list, name_map


def _estado_coords(estado_geojson: dict):
    lats, lons = [], []
    for feat in estado_geojson["features"]:
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for ring in poly:
                lons += [c[0] for c in ring] + [None]
                lats += [c[1] for c in ring] + [None]
    return lats, lons


def load_product(cfg: dict, mid_list: list, name_map: dict):
    """Retorna (years, data_by_year, color_max) para um produto."""
    df = pd.read_csv(cfg["csv"], dtype={"municipio_id": str})
    years = sorted(df["ano"].unique())

    qty_pivot = df.pivot(index="municipio_id", columns="ano", values=cfg["qty_col"])
    val_pivot = df.pivot(index="municipio_id", columns="ano", values=cfg["val_col"])

    data_by_year = {}
    for year in years:
        z, text = [], []
        for mid in mid_list:
            name = name_map[mid]
            has_q = mid in qty_pivot.index and year in qty_pivot.columns
            q = qty_pivot.at[mid, year] if has_q else float("nan")
            has_v = mid in val_pivot.index and year in val_pivot.columns
            v = val_pivot.at[mid, year] if has_v else float("nan")
            if pd.notna(q):
                v_str = f"R$ {v:,.0f} mil" if pd.notna(v) else "—"
                z.append(q)
                text.append(
                    f"<b>{name}</b><br>"
                    f"Produção: {q:,.0f} {cfg['unit']}<br>"
                    f"Valor: {v_str}"
                )
            else:
                z.append(None)
                text.append(f"<b>{name}</b><br>Sem produção registrada")
        data_by_year[year] = (z, text)

    color_max = float(df[cfg["qty_col"]].quantile(0.97))
    return years, data_by_year, color_max


def build_slider(years: list, data_by_year: dict) -> dict:
    steps = [
        dict(
            method="restyle",
            args=[{"z": [data_by_year[y][0]], "text": [data_by_year[y][1]]}],
            label=str(y),
        )
        for y in years
    ]
    return dict(
        active=len(years) - 1,
        steps=steps,
        currentvalue=dict(prefix="Ano: ", visible=True, xanchor="center"),
        pad={"t": 50},
    )


def generate_map(geojson, estado_geojson, mid_list, name_map) -> go.Figure:
    estado_lats, estado_lons = _estado_coords(estado_geojson)

    # Carrega apenas produtos com CSV disponível
    available = {k: v for k, v in PRODUCTS.items() if v["csv"].exists()}
    if not available:
        raise FileNotFoundError("Nenhum CSV de produto encontrado em data/.")
    missing = [k for k in PRODUCTS if k not in available]
    if missing:
        print(f"Produtos sem CSV (ignorados): {missing}")

    # Produto inicial (primeiro disponível)
    first_key = next(iter(available))
    first_cfg = available[first_key]
    years0, data0, cmax0 = load_product(first_cfg, mid_list, name_map)
    latest0 = years0[-1]
    z0, text0 = data0[latest0]

    fig = go.Figure([
        go.Choroplethmap(
            geojson=geojson,
            locations=mid_list,
            featureidkey="properties.id",
            z=z0,
            text=text0,
            hovertemplate="%{text}<extra></extra>",
            colorscale="YlOrRd",
            zmin=0,
            zmax=cmax0,
            marker_opacity=0.7,
            marker_line_width=0.5,
            colorbar=dict(title="Produção<br>(t)", thickness=15, len=0.6),
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

    # Dropdown de produtos (apenas os disponíveis)
    prod_buttons = []
    for cfg in available.values():
        years, data, cmax = load_product(cfg, mid_list, name_map)
        latest = years[-1]
        z_lat, text_lat = data[latest]
        slider = build_slider(years, data)
        prod_buttons.append(dict(
            label=cfg["label"],
            method="update",
            args=[
                {"z": [z_lat, None], "text": [text_lat, None], "zmax": [cmax, None]},
                {"sliders": [slider]},
            ],
        ))

    fig.update_layout(
        map_style="carto-positron",
        map_center={"lat": -5.0, "lon": -44.5},
        map_zoom=5.5,
        title=dict(
            text=(
                "<b>Produção extrativa por município — Maranhão</b>"
                "<br><sup>PEVS/IBGE · 1994–2024 · OCAS-MA / UFMA</sup>"
            ),
            x=0.5,
            xanchor="center",
        ),
        updatemenus=[dict(
            type="dropdown",
            direction="down",
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
            bgcolor="white",
            bordercolor="#cccccc",
            font=dict(size=13),
            buttons=prod_buttons,
            showactive=True,
        )],
        sliders=[build_slider(years0, data0)],
        margin={"r": 0, "t": 80, "l": 0, "b": 60},
        height=700,
    )

    return fig


def main():
    geojson, estado_geojson, mid_list, name_map = load_geodata()
    fig = generate_map(geojson, estado_geojson, mid_list, name_map)

    out = ROOT / "index.html"
    fig.write_html(str(out), full_html=True, include_plotlyjs="cdn")

    size_kb = out.stat().st_size / 1024
    print(f"Mapa salvo  : {out}")
    print(f"Tamanho     : {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")
    print(f"Produtos    : {list(PRODUCTS.keys())}")


if __name__ == "__main__":
    main()
