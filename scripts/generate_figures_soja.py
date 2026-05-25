"""
Gera figuras e tabelas publicáveis para o artigo sobre soja no Maranhão (1995–2024).

Saídas em paper/figuras_artigo/:
  figura1_serie_estadual.png/.svg  — produção + área com fases demarcadas
  figura2_shift_share.png/.svg     — decomposição anual empilhada (área/yield/interação)
  figura3_lisa_mapas.png/.svg      — mapas LISA HH (2005, 2016, 2019, 2024) em 2×2
  figura4_concentracao.png/.svg    — HHI e CR4 ao longo do tempo
  tabela1_fases.csv                — estatísticas por fase
  tabela2_apl_soja.csv             — municípios APL consolidados/emergentes 2024
  tabela3_sicor_lisa.csv           — cobertura SICOR nos clusters HH por ano
"""

import csv
import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR  = ROOT / "paper" / "figuras_artigo"

# Paleta por fase (Pioneer → Boom)
FASE_CORES = ["#4E9AF1", "#F4A261", "#2A9D8F", "#E76F51"]
FASE_ALPHA = 0.13

# Cores shift-share
COR_AREA  = "#2196F3"
COR_YIELD = "#4CAF50"
COR_INTER = "#FF9800"

DPI = 300


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _salva(fig: plt.Figure, nome: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        path = OUT_DIR / f"{nome}.{ext}"
        fig.savefig(path, dpi=DPI, bbox_inches="tight")
        log.info("  salvo: %s", path.relative_to(ROOT))
    plt.close(fig)


def _formata_mil(x, _=None) -> str:
    if abs(x) >= 1e6:
        return f"{x/1e6:.1f} M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.0f} k"
    return f"{x:.0f}"


def _desenha_fases(ax: plt.Axes, fases: list[dict], ymin: float, ymax: float) -> None:
    """Sombreamento de fases + rótulo no topo."""
    for i, fase in enumerate(fases):
        ax.axvspan(fase["inicio"], fase["fim"], alpha=FASE_ALPHA, color=FASE_CORES[i], zorder=0)
        mid_x = (fase["inicio"] + fase["fim"]) / 2
        ax.text(mid_x, ymax * 0.97, fase["nome"].replace("Fase ", ""),
                ha="center", va="top", fontsize=7, color=FASE_CORES[i],
                fontweight="bold", alpha=0.85)


# ---------------------------------------------------------------------------
# Figura 1 — Série estadual com eixo duplo
# ---------------------------------------------------------------------------

def figura1_serie(sa: dict, ss: dict) -> None:
    log.info("[Figura 1] Série estadual com eixo duplo ...")

    se = sa["serie_estadual"]
    anos_raw = se["anos"]
    prod = {int(k): v for k, v in se["producao_ton"].items()}
    area = {int(k): v for k, v in se["area_colhida_ha"].items()}
    fases = sa["fases"]

    anos = sorted(prod.keys())
    y_prod = [prod[a] / 1e6 for a in anos]        # milhões ton
    y_area = [area.get(a, float("nan")) / 1e6 for a in anos]  # milhões ha

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    _desenha_fases(ax1, fases, 0, max(y_prod) * 1.15)

    ax1.fill_between(anos, y_prod, alpha=0.18, color="#1565C0")
    l1, = ax1.plot(anos, y_prod, color="#1565C0", lw=2, label="Produção (Mt)")
    ax1.set_ylabel("Produção (milhões de toneladas)", color="#1565C0", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax1.set_ylim(0, max(y_prod) * 1.2)

    l2, = ax2.plot(anos, y_area, color="#C62828", lw=1.8, ls="--", label="Área colhida (Mha)")
    ax2.set_ylabel("Área colhida (milhões de hectares)", color="#C62828", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#C62828")
    ax2.set_ylim(0, max(a for a in y_area if not np.isnan(a)) * 1.35)

    ax1.set_xlabel("Ano", fontsize=10)
    ax1.set_title("Soja no Maranhão (1995–2024): produção e área colhida por fase", fontsize=11)
    ax1.legend([l1, l2], ["Produção (Mt)", "Área colhida (Mha)"],
               loc="upper left", fontsize=9)

    # Linhas de quebra de fase
    for fase in fases[1:]:
        ax1.axvline(fase["inicio"], color="gray", lw=0.8, ls=":")

    ax1.set_xlim(anos[0], anos[-1])
    ax1.xaxis.set_major_locator(mticker.MultipleLocator(5))
    fig.tight_layout()
    _salva(fig, "figura1_serie_estadual")


# ---------------------------------------------------------------------------
# Figura 2 — Decomposição shift-share anual (barras empilhadas)
# ---------------------------------------------------------------------------

def figura2_shift_share(ss: dict) -> None:
    log.info("[Figura 2] Decomposição shift-share anual ...")

    ss_anual = ss["estadual_ano_a_ano"]
    anos = sorted(int(a) for a in ss_anual)
    fases = ss["por_fase"]

    ef_area  = [ss_anual[str(a)].get("ef_area",  0) / 1e6 for a in anos]
    ef_yield = [ss_anual[str(a)].get("ef_yield", 0) / 1e6 for a in anos]
    ef_inter = [ss_anual[str(a)].get("ef_inter", 0) / 1e6 for a in anos]

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.bar(anos, ef_area,  color=COR_AREA,  label="Efeito área",        alpha=0.85)
    ax.bar(anos, ef_yield, color=COR_YIELD, label="Efeito produtividade", alpha=0.85,
           bottom=ef_area)
    # interação: empilha sobre a soma anterior
    bottoms = [a + y for a, y in zip(ef_area, ef_yield)]
    ax.bar(anos, ef_inter, color=COR_INTER, label="Efeito interação",   alpha=0.75,
           bottom=bottoms)

    ax.axhline(0, color="black", lw=0.6)

    # Linha de quebra de fase
    for fase in fases[1:]:
        ax.axvline(fase["inicio"] - 0.5, color="gray", lw=0.9, ls=":", zorder=5)
        ax.text(fase["inicio"] - 0.3, ax.get_ylim()[0] * 0.9,
                str(fase["inicio"]), ha="left", fontsize=7.5, color="gray")

    ax.set_xlabel("Ano", fontsize=10)
    ax.set_ylabel("ΔProdução (milhões de toneladas)", fontsize=10)
    ax.set_title("Decomposição shift-share da produção de soja no Maranhão", fontsize=11)
    ax.legend(fontsize=9)
    ax.set_xlim(anos[0] - 0.8, anos[-1] + 0.8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_formata_mil))
    fig.tight_layout()
    _salva(fig, "figura2_shift_share")


# ---------------------------------------------------------------------------
# Figura 3 — Mapas LISA HH (2×2 painéis)
# ---------------------------------------------------------------------------

def _carrega_geojson() -> dict[str, list]:
    """Retorna {municipio_id: [[x, y], ...]} com coords do anel externo."""
    with open(DATA_DIR / "municipios_ma.geojson", encoding="utf-8") as f:
        geo = json.load(f)
    coords: dict[str, list] = {}
    for feat in geo["features"]:
        mid = str(feat["properties"]["id"])
        ring = feat["geometry"]["coordinates"][0]
        coords[mid] = ring
    return coords


def _bbox(coords_dict: dict) -> tuple[float, float, float, float]:
    all_x = [pt[0] for ring in coords_dict.values() for pt in ring]
    all_y = [pt[1] for ring in coords_dict.values() for pt in ring]
    return min(all_x), max(all_x), min(all_y), max(all_y)


def _desenha_mapa(
    ax: plt.Axes,
    coords: dict[str, list],
    hh_sig: set[str],
    bbox: tuple,
    titulo: str,
) -> None:
    xmin, xmax, ymin, ymax = bbox

    for mid, ring in coords.items():
        xs = [pt[0] for pt in ring]
        ys = [pt[1] for pt in ring]
        verts = list(zip(xs, ys))
        if mid in hh_sig:
            cor, ec, lw = "#D32F2F", "#8B0000", 0.4
        else:
            cor, ec, lw = "#E0E0E0", "#9E9E9E", 0.2
        poly = mpatches.Polygon(verts, closed=True, facecolor=cor, edgecolor=ec, lw=lw)
        ax.add_patch(poly)

    ax.set_xlim(xmin - 0.2, xmax + 0.2)
    ax.set_ylim(ymin - 0.2, ymax + 0.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(titulo, fontsize=9, pad=4)

    n_hh = len(hh_sig)
    ax.text(0.02, 0.04, f"n HH = {n_hh}", transform=ax.transAxes,
            fontsize=7.5, va="bottom", color="#B71C1C")


def figura3_lisa(esp: dict) -> None:
    log.info("[Figura 3] Mapas LISA HH (2005, 2016, 2019, 2024) ...")

    coords = _carrega_geojson()
    bbox   = _bbox(coords)
    lisa_soja = esp["lisa"]["soja"]
    anos_chave = [2005, 2016, 2019, 2024]

    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    fig.suptitle("Clusters HH significativos (LISA Moran Local, p < 0,05) — Soja MA",
                 fontsize=11, y=1.01)

    for ax, ano in zip(axes.flat, anos_chave):
        dados_ano = lisa_soja.get(str(ano), {})
        hh_sig = {
            mid for mid, v in dados_ano.items()
            if v.get("q") == "HH" and v.get("p", 1.0) < 0.05
        }
        _desenha_mapa(ax, coords, hh_sig, bbox, f"{ano}")

    # Legenda compartilhada
    leg_hh = mpatches.Patch(color="#D32F2F", label="Cluster HH significativo (p<0,05)")
    leg_no = mpatches.Patch(color="#E0E0E0", label="Não significativo / outro quadrante")
    fig.legend(handles=[leg_hh, leg_no], loc="lower center", ncol=2,
               fontsize=9, bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout()
    _salva(fig, "figura3_lisa_mapas")


# ---------------------------------------------------------------------------
# Figura 4 — Evolução HHI e CR4
# ---------------------------------------------------------------------------

def figura4_concentracao(sa: dict) -> None:
    log.info("[Figura 4] Evolução HHI e CR4 ...")

    conc = sa["concentracao"]
    fases = sa["fases"]
    anos = sorted(int(a) for a in conc)
    hhi  = [conc[str(a)].get("hhi", float("nan")) for a in anos]
    cr4  = [conc[str(a)].get("cr4", float("nan")) / 100 for a in anos]  # → fração

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    _desenha_fases(ax1, fases, 0, max(h for h in hhi if not np.isnan(h)) * 1.2)

    l1, = ax1.plot(anos, hhi, color="#1565C0", lw=2, marker="o", ms=3.5,
                   label="HHI (Herfindahl-Hirschman)")
    ax1.set_ylabel("HHI", color="#1565C0", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax1.set_ylim(0, max(h for h in hhi if not np.isnan(h)) * 1.3)

    l2, = ax2.plot(anos, cr4, color="#C62828", lw=1.8, ls="--", marker="s", ms=3,
                   label="CR4 (razão de concentração 4 maiores)")
    ax2.set_ylabel("CR4 (proporção)", color="#C62828", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#C62828")
    ax2.set_ylim(0, 1.0)
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))

    for fase in fases[1:]:
        ax1.axvline(fase["inicio"], color="gray", lw=0.8, ls=":")

    ax1.set_xlabel("Ano", fontsize=10)
    ax1.set_title("Concentração espacial da produção de soja no Maranhão (HHI e CR4)",
                  fontsize=11)
    ax1.legend([l1, l2], ["HHI", "CR4"], loc="upper right", fontsize=9)
    ax1.set_xlim(anos[0], anos[-1])
    ax1.xaxis.set_major_locator(mticker.MultipleLocator(5))
    fig.tight_layout()
    _salva(fig, "figura4_concentracao")


# ---------------------------------------------------------------------------
# Tabela 1 — Estatísticas por fase
# ---------------------------------------------------------------------------

def tabela1_fases(sa: dict, ss: dict) -> None:
    log.info("[Tabela 1] Estatísticas por fase ...")

    ss_fases = {f["nome"]: f for f in ss["por_fase"]}

    rows = []
    for fase in sa["fases"]:
        nome  = fase["nome"]
        ini   = fase["inicio"]
        fim   = fase["fim"]
        dur   = fim - ini
        p0    = fase.get("producao_ton_inicio", 0)
        p1    = fase.get("producao_ton_fim", 0)
        a0    = fase.get("area_colhida_ha_inicio", 0)
        a1    = fase.get("area_colhida_ha_fim", 0)
        tcg   = fase.get("tcg_producao", float("nan"))
        n_mun = fase.get("n_municipios_fim", "–")

        y0 = p0 / a0 if a0 else float("nan")
        y1 = p1 / a1 if a1 else float("nan")

        ssf = ss_fases.get(nome, {})
        ef_a = ssf.get("ef_area_pct", float("nan"))
        ef_y = ssf.get("ef_yield_pct", float("nan"))
        ef_i = ssf.get("ef_inter_pct", float("nan"))

        rows.append({
            "Fase": nome,
            "Período": f"{ini}–{fim}",
            "Duração (anos)": dur,
            "Produção início (Mt)": f"{p0/1e6:.2f}",
            "Produção fim (Mt)": f"{p1/1e6:.2f}",
            "TCG produção (% a.a.)": f"{tcg*100:.1f}" if not np.isnan(tcg) else "–",
            "Área início (Mha)": f"{a0/1e6:.3f}" if a0 else "–",
            "Área fim (Mha)": f"{a1/1e6:.3f}" if a1 else "–",
            "Produtividade início (t/ha)": f"{y0:.2f}" if not np.isnan(y0) else "–",
            "Produtividade fim (t/ha)": f"{y1:.2f}" if not np.isnan(y1) else "–",
            "N munícipios fim": n_mun,
            "Shift-share: efeito área (%)": f"{ef_a:.1f}" if not np.isnan(ef_a) else "–",
            "Shift-share: efeito yield (%)": f"{ef_y:.1f}" if not np.isnan(ef_y) else "–",
            "Shift-share: interação (%)": f"{ef_i:.1f}" if not np.isnan(ef_i) else "–",
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "tabela1_fases.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("  salvo: %s", path.relative_to(ROOT))


# ---------------------------------------------------------------------------
# Tabela 2 — Municípios APL soja consolidados + emergentes (2024)
# ---------------------------------------------------------------------------

def tabela2_apl(apl: dict) -> None:
    log.info("[Tabela 2] APL soja consolidados + emergentes 2024 ...")

    soja_anos = apl["apl"]["soja"]
    # Usa o ano mais recente disponível
    ano_ref = str(max(int(a) for a in soja_anos))
    dados = soja_anos[ano_ref]

    # Nomes: carrega do CSV de soja
    import csv as _csv
    nomes: dict[str, str] = {}
    soja_csv = DATA_DIR / "soja" / "soja_pam.csv"
    with open(soja_csv, encoding="utf-8-sig") as f:
        for row in _csv.DictReader(f):
            nomes[row["municipio_id"]] = row["municipio"]

    cats_alvo = {"consolidado", "emergente"}
    rows = []
    for mid, v in dados.items():
        if v.get("cat") not in cats_alvo:
            continue
        rows.append({
            "Código IBGE": mid,
            "Município": nomes.get(mid, mid),
            "Categoria APL": v.get("cat", "–"),
            "QL": f"{v.get('ql', float('nan')):.3f}",
            "Score APL": f"{v.get('score', float('nan')):.4f}",
            "Persistência (anos)": v.get("persist", "–"),
            "TCG valor (a.a.)": f"{v.get('tcg', float('nan')):.4f}" if v.get("tcg") is not None else "–",
            "LISA p-valor": f"{v.get('lisa_p', float('nan')):.3f}",
            "LISA quadrante": v.get("lisa_q", "–"),
        })

    # Ordena: consolidados primeiro, depois por score
    rows.sort(key=lambda r: (0 if r["Categoria APL"] == "consolidado" else 1,
                              -float(r["Score APL"])))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "tabela2_apl_soja.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("  salvo: %s (%d municípios, ano ref=%s)", path.relative_to(ROOT), len(rows), ano_ref)


# ---------------------------------------------------------------------------
# Figura 5 — Lag crédito → produção
# ---------------------------------------------------------------------------

def figura5_lag_credito(lag_data: dict) -> None:
    log.info("[Figura 5] Lag crédito → produção ...")

    serie = lag_data["estadual"]["serie"]
    corrs = lag_data["estadual"]["correlacoes_por_lag"]

    vcr_by_ano  = {int(a): v["vcr_real2024"]  for a, v in serie.items() if v.get("vcr_real2024")}
    prod_by_ano = {int(a): v["producao_ton"]   for a, v in serie.items() if v.get("producao_ton")}

    pares = [(vcr_by_ano[a], prod_by_ano[a + 1], a)
             for a in sorted(vcr_by_ano) if (a + 1) in prod_by_ano]
    xs = np.array([p[0] / 1e9 for p in pares])
    ys = np.array([p[1] / 1e6 for p in pares])
    anos_par = [p[2] for p in pares]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Painel A — scatter VCR(t) × Prod(t+1)
    ax = axes[0]
    slope, intercept, r_lin, p_lin, _ = stats.linregress(xs, ys)
    x_line = np.linspace(xs.min(), xs.max(), 100)
    ax.scatter(xs, ys, color="#1565C0", s=60, zorder=5, alpha=0.85)
    for x, y, ano in zip(xs, ys, anos_par):
        ax.annotate(str(ano), (x, y), textcoords="offset points",
                    xytext=(4, 3), fontsize=7, color="#333333")
    ax.plot(x_line, slope * x_line + intercept, color="#C62828", lw=1.8, ls="--")
    ax.set_xlabel("VCR custeio soja em t (R$ bilhões, IPCA 2024)", fontsize=10)
    ax.set_ylabel("Produção soja em t+1 (Mt)", fontsize=10)
    ax.set_title(f"A)  VCR(t) × Produção(t+1)  |  r = {r_lin:.3f}  p = {p_lin:.4f}", fontsize=10)
    ax.grid(True, alpha=0.25)

    # Painel B — barras r por lag
    ax2 = axes[1]
    lags_k = ["0", "1", "2"]
    rs     = [corrs[k]["r"]       for k in lags_k if k in corrs]
    ic_lo  = [corrs[k]["ic95_lo"] for k in lags_k if k in corrs]
    ic_hi  = [corrs[k]["ic95_hi"] for k in lags_k if k in corrs]
    xerr_lo = [r - lo for r, lo in zip(rs, ic_lo)]
    xerr_hi = [hi - r for r, hi in zip(rs, ic_hi)]
    cores = ["#2196F3", "#1565C0", "#90CAF9"]

    ax2.bar(lags_k[:len(rs)], rs, color=cores[:len(rs)], alpha=0.85, width=0.5, zorder=3)
    ax2.errorbar(lags_k[:len(rs)], rs, yerr=[xerr_lo, xerr_hi],
                 fmt="none", color="black", capsize=5, lw=1.5, zorder=5)
    for lag_k, r_v in zip(lags_k, rs):
        sig = corrs[lag_k].get("sig_05")
        ax2.text(lag_k, r_v + 0.02, f"r={r_v:.3f}" + (" *" if sig else ""),
                 ha="center", fontsize=9)
    ax2.axhline(0, color="black", lw=0.5)
    ax2.set_ylim(0, 1.05)
    ax2.set_xlabel("Lag (anos)", fontsize=10)
    ax2.set_ylabel("r de Pearson", fontsize=10)
    ax2.set_title("B)  Correlação VCR(t) × Produção(t+lag)\n(nível estadual, * p<0,05)", fontsize=10)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("Relação entre crédito rural (SICOR custeio soja) e produção (PAM) no Maranhão",
                 fontsize=11, y=1.01)
    fig.tight_layout()
    _salva(fig, "figura5_lag_credito")


# ---------------------------------------------------------------------------
# Tabela 3 — SICOR × LISA cobertura por ano
# ---------------------------------------------------------------------------

def tabela3_sicor_lisa(sa: dict) -> None:
    log.info("[Tabela 3] SICOR × LISA cobertura por ano ...")

    sl = sa["sicor_lisa"]
    rows = []
    for ano in sorted(sl.keys(), key=int):
        v = sl[ano]
        rows.append({
            "Ano": ano,
            "Clusters HH sig. (n)": v.get("n_hh_sig", "–"),
            "Municípios com crédito (n)": v.get("n_muns_com_credito", "–"),
            "HH com crédito (n)": v.get("n_hh_com_credito", "–"),
            "Cobertura crédito em HH (%)": f"{v['cobertura_credito_hh_pct']:.1f}" if v.get('cobertura_credito_hh_pct') is not None else "–",
            "VCR total (R$ mi)": f"{v.get('vcr_total_r', 0)/1e6:.1f}",
            "VCR em HH (R$ mi)": f"{v.get('vcr_em_hh_r', 0)/1e6:.1f}",
            "Share VCR em HH (%)": f"{v['share_vcr_hh_pct']:.1f}" if v.get('share_vcr_hh_pct') is not None else "–",
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "tabela3_sicor_lisa.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("  salvo: %s (%d anos)", path.relative_to(ROOT), len(rows))


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== generate_figures_soja — início ===")
    log.info("  saídas em: %s", OUT_DIR.relative_to(ROOT))

    with open(DATA_DIR / "soja_artigo.json",    encoding="utf-8") as f:
        sa = json.load(f)
    with open(DATA_DIR / "shift_share_soja.json", encoding="utf-8") as f:
        ss = json.load(f)
    with open(DATA_DIR / "espacial.json",         encoding="utf-8") as f:
        esp = json.load(f)
    with open(DATA_DIR / "apl.json",              encoding="utf-8") as f:
        apl = json.load(f)

    lag_path = DATA_DIR / "lag_credito_soja.json"
    lag_data = json.loads(lag_path.read_text(encoding="utf-8")) if lag_path.exists() else None

    figura1_serie(sa, ss)
    figura2_shift_share(ss)
    figura3_lisa(esp)
    figura4_concentracao(sa)
    if lag_data:
        figura5_lag_credito(lag_data)
    else:
        log.warning("lag_credito_soja.json ausente — Figura 5 ignorada. Rode compute_lag_credito.py primeiro.")
    tabela1_fases(sa, ss)
    tabela2_apl(apl)
    tabela3_sicor_lisa(sa)

    n_saidas = (5 if lag_data else 4) * 2 + 3
    log.info("=== Concluído. %d arquivos em %s ===", n_saidas, OUT_DIR.relative_to(ROOT))


if __name__ == "__main__":
    main()
