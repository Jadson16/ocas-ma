"""
Calcula indicadores quantitativos de especialização e dinamismo para todas
as cadeias do OCAS-MA e salva data/indicadores.json.

Indicadores:
  QL  — Quociente Locacional (base valor, produtos com valor_mil_reais)
  PR  — Participação Relativa (% do município no total estadual)
  TCG — Taxa de Crescimento Geométrica (janela de TCG_JANELA anos, base valor)
  IDM — Índice de Dinamismo Municipal (TCG_mun / TCG_estado)
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

DEFLATOR_FILE = Path(__file__).parent.parent / "data" / "ipca_deflator.csv"


def load_deflator() -> dict[int, float]:
    """
    Carrega deflator IPCA base 2024.
    Retorna {ano: deflator_base2024} ou {} se arquivo ausente.
    Para deflacionar: valor_real2024 = valor_nominal × deflator[ano]
    """
    if not DEFLATOR_FILE.exists():
        log.warning("ipca_deflator.csv não encontrado — indicadores em valores nominais")
        return {}
    df = pd.read_csv(DEFLATOR_FILE)
    return dict(zip(df["ano"].astype(int), df["deflator_base2024"].astype(float)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

ROOT    = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "indicadores.json"

TCG_JANELA = 10  # anos de lookback para TCG e IDM

# Catálogo de produtos — espelha generate_map.py (apenas os com valor_mil_reais)
PRODUCTS_COM_VALOR: dict[str, tuple[str, str, str]] = {
    # chave: (csv relativo a DATA_DIR, coluna quantidade, grupo)
    "babacu":         ("babacu/babacau_pevs.csv",                  "quantidade_ton",        "PEVS"),
    "acai":           ("acai/acai_pevs.csv",                       "quantidade_ton",        "PEVS"),
    "buriti":         ("buriti/buriti_pevs.csv",                   "quantidade_ton",        "PEVS"),
    "carnauba":       ("carnauba/carnauba_pevs.csv",                "quantidade_ton",        "PEVS"),
    "carnauba_fibra": ("carnauba_fibra/carnauba_fibra_pevs.csv",    "quantidade_ton",        "PEVS"),
    "piacava":        ("piacava/piacava_pevs.csv",                  "quantidade_ton",        "PEVS"),
    "arroz":          ("arroz/arroz_pam.csv",                       "quantidade_ton",        "PAM"),
    "feijao":         ("feijao/feijao_pam.csv",                     "quantidade_ton",        "PAM"),
    "mandioca":       ("mandioca/mandioca_pam.csv",                 "quantidade_ton",        "PAM"),
    "milho":          ("milho/milho_pam.csv",                       "quantidade_ton",        "PAM"),
    "soja":           ("soja/soja_pam.csv",                         "quantidade_ton",        "PAM"),
    "cana":           ("cana/cana_pam.csv",                         "quantidade_ton",        "PAM"),
    "melancia":       ("melancia/melancia_pam.csv",                 "quantidade_ton",        "PAM"),
    "amendoim":       ("amendoim/amendoim_pam.csv",                 "quantidade_ton",        "PAM"),
    "algodao":        ("algodao/algodao_pam.csv",                   "quantidade_ton",        "PAM"),
    "banana":         ("banana/banana_pam.csv",                     "quantidade_ton",        "PAM"),
    "castanha_caju":  ("castanha_caju/castanha_caju_pam.csv",       "quantidade_ton",        "PAM"),
    "coco":           ("coco/coco_pam.csv",                         "quantidade_ton",        "PAM"),
    "laranja":        ("laranja/laranja_pam.csv",                   "quantidade_ton",        "PAM"),
    "acai_cult":      ("acai_cult/acai_cult_pam.csv",               "quantidade_ton",        "PAM"),
    "mamao":          ("mamao/mamao_pam.csv",                       "quantidade_ton",        "PAM"),
    "manga":          ("manga/manga_pam.csv",                       "quantidade_ton",        "PAM"),
    "maracuja":       ("maracuja/maracuja_pam.csv",                 "quantidade_ton",        "PAM"),
    "borracha":       ("borracha/borracha_pam.csv",                 "quantidade_ton",        "PAM"),
    "mel":            ("mel/mel_ppm.csv",                           "quantidade_kg",         "PPM"),
    "leite":          ("leite/leite_ppm.csv",                       "quantidade_mil_litros", "PPM"),
    "ovos":           ("ovos/ovos_ppm.csv",                         "quantidade_mil_duzias", "PPM"),
}

LABELS: dict[str, str] = {
    "babacu": "Babaçu (amêndoa)", "acai": "Açaí (extrativista)", "buriti": "Buriti (fibra)",
    "carnauba": "Carnaúba (cera)", "carnauba_fibra": "Carnaúba (fibra/folha)", "piacava": "Piaçava (fibra)",
    "arroz": "Arroz", "feijao": "Feijão", "mandioca": "Mandioca", "milho": "Milho", "soja": "Soja",
    "cana": "Cana-de-açúcar", "melancia": "Melancia", "amendoim": "Amendoim", "algodao": "Algodão herbáceo",
    "banana": "Banana", "castanha_caju": "Castanha de caju", "coco": "Coco-da-baía", "laranja": "Laranja",
    "acai_cult": "Açaí (cultivado)", "mamao": "Mamão", "manga": "Manga", "maracuja": "Maracujá",
    "borracha": "Borracha (látex)", "mel": "Mel de abelha", "leite": "Leite de vaca", "ovos": "Ovos de galinha",
}


def _safe(v) -> float | None:
    """Converte para float, retorna None se NaN/inf."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def load_data(deflator: dict[int, float]) -> tuple[dict[str, pd.DataFrame], set[str]]:
    """
    Carrega CSVs disponíveis e aplica deflator IPCA base 2024.
    QL e PR são inalterados (mesmo deflator cancela no mesmo ano).
    TCG passa a refletir crescimento real.
    """
    dfs: dict[str, pd.DataFrame] = {}
    all_mids: set[str] = set()
    for key, (csv_rel, qty_col, _) in PRODUCTS_COM_VALOR.items():
        path = DATA_DIR / csv_rel
        if not path.exists():
            log.warning("CSV não encontrado: %s — ignorado", csv_rel)
            continue
        df = pd.read_csv(path, dtype={"municipio_id": str})
        if "valor_mil_reais" not in df.columns:
            log.warning("%s sem coluna valor_mil_reais — ignorado", key)
            continue
        df = df[["municipio_id", "municipio", "ano", "valor_mil_reais"]].copy()
        df = df[df["valor_mil_reais"].notna() & (df["valor_mil_reais"] > 0)]
        # Aplica deflação: valor_real2024 = valor_nominal × deflator[ano]
        if deflator:
            df["valor_mil_reais"] = df.apply(
                lambda r: r["valor_mil_reais"] * deflator.get(int(r["ano"]), 1.0),
                axis=1,
            )
        dfs[key] = df
        all_mids.update(df["municipio_id"].unique())
        log.info("  %-18s %d linhas com valor", key, len(df))
    return dfs, all_mids


def build_pivot_total(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Soma de valor_mil_reais de TODOS os produtos por (municipio_id, ano)."""
    frames = [df[["municipio_id", "ano", "valor_mil_reais"]] for df in dfs.values()]
    combined = pd.concat(frames, ignore_index=True)
    return combined.groupby(["municipio_id", "ano"])["valor_mil_reais"].sum()


def compute_ql(
    df_prod: pd.DataFrame,
    pivot_total: pd.Series,
    anos: list[int],
) -> dict[int, dict[str, float | None]]:
    """QL = (v_ij / v_i) / (v_j / v_total)."""
    result: dict[int, dict] = {}
    for ano in anos:
        sub = df_prod[df_prod["ano"] == ano]
        v_j = sub["valor_mil_reais"].sum()
        v_total_ano = pivot_total.xs(ano, level="ano").sum() if ano in pivot_total.index.get_level_values("ano") else 0
        if v_j == 0 or v_total_ano == 0:
            result[ano] = {}
            continue
        share_j = v_j / v_total_ano
        row: dict[str, float | None] = {}
        for _, r in sub.iterrows():
            mid = r["municipio_id"]
            v_i = pivot_total.get((mid, ano), 0)
            if v_i == 0:
                continue
            ql = (r["valor_mil_reais"] / v_i) / share_j
            row[mid] = _safe(ql)
        result[ano] = row
    return result


def compute_pr(df_prod: pd.DataFrame, anos: list[int]) -> dict[int, dict[str, float | None]]:
    """PR = v_ij / v_j × 100."""
    result: dict[int, dict] = {}
    for ano in anos:
        sub = df_prod[df_prod["ano"] == ano]
        v_j = sub["valor_mil_reais"].sum()
        if v_j == 0:
            result[ano] = {}
            continue
        result[ano] = {r["municipio_id"]: _safe(r["valor_mil_reais"] / v_j * 100) for _, r in sub.iterrows()}
    return result


def compute_tcg_idm(
    df_prod: pd.DataFrame,
    anos: list[int],
    janela: int = TCG_JANELA,
) -> tuple[dict[int, dict[str, float | None]], dict[int, dict[str, float | None]]]:
    """TCG e IDM, janela de `janela` anos."""
    pivot = df_prod.pivot_table(index="municipio_id", columns="ano", values="valor_mil_reais", aggfunc="sum")
    tcg_out: dict[int, dict] = {}
    idm_out: dict[int, dict] = {}

    for ano in anos:
        ano0 = ano - janela
        if ano0 not in pivot.columns or ano not in pivot.columns:
            tcg_out[ano] = {}
            idm_out[ano] = {}
            continue

        # TCG estadual
        est_t  = pivot[ano].sum()
        est_t0 = pivot[ano0].sum()
        tcg_est = ((est_t / est_t0) ** (1 / janela) - 1) if est_t0 > 0 else None

        row_tcg: dict[str, float | None] = {}
        row_idm: dict[str, float | None] = {}
        for mid in pivot.index:
            v_t  = pivot.at[mid, ano]  if ano  in pivot.columns else None
            v_t0 = pivot.at[mid, ano0] if ano0 in pivot.columns else None
            if pd.isna(v_t) or pd.isna(v_t0) or v_t0 == 0 or v_t is None or v_t0 is None:
                continue
            tcg = (v_t / v_t0) ** (1 / janela) - 1
            row_tcg[mid] = _safe(tcg)
            if tcg_est and tcg_est != 0:
                row_idm[mid] = _safe(tcg / tcg_est)

        tcg_out[ano] = row_tcg
        idm_out[ano] = row_idm

    return tcg_out, idm_out


def main() -> None:
    log.info("=== compute_indicators — início ===")

    deflator = load_deflator()
    if deflator:
        log.info("  Deflator IPCA base 2024 carregado (%d anos)", len(deflator))
    else:
        log.warning("  Rodando sem deflação — valores nominais")

    dfs, _ = load_data(deflator)
    if not dfs:
        log.error("Nenhum CSV carregado. Abortando.")
        raise SystemExit(1)

    pivot_total = build_pivot_total(dfs)

    # Anos comuns com dados de valor
    all_anos: set[int] = set()
    for df in dfs.values():
        all_anos.update(df["ano"].unique())
    anos = sorted(int(a) for a in all_anos)

    ind: dict = {"ql": {}, "pr": {}, "tcg": {}, "idm": {}}
    produtos_meta: dict = {}

    for key, df in dfs.items():
        log.info("  calculando %-18s ...", key)
        _, _, grupo = PRODUCTS_COM_VALOR[key]
        produtos_meta[key] = {"label": LABELS.get(key, key), "grupo": grupo}

        anos_prod = sorted(df["ano"].unique())

        ql  = compute_ql(df, pivot_total, anos_prod)
        pr  = compute_pr(df, anos_prod)
        tcg, idm = compute_tcg_idm(df, anos_prod)

        # Serializa anos como strings (JSON keys)
        ind["ql"][key]  = {str(a): v for a, v in ql.items()  if v}
        ind["pr"][key]  = {str(a): v for a, v in pr.items()  if v}
        ind["tcg"][key] = {str(a): v for a, v in tcg.items() if v}
        ind["idm"][key] = {str(a): v for a, v in idm.items() if v}

    # Nomes de municípios (mapa id→nome)
    nomes: dict[str, str] = {}
    for df in dfs.values():
        for _, r in df[["municipio_id", "municipio"]].drop_duplicates().iterrows():
            nomes[r["municipio_id"]] = r["municipio"]

    output = {
        "meta": {
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "anos_disponiveis": anos,
            "tcg_janela_anos": TCG_JANELA,
            "n_produtos": len(dfs),
            "deflacao": "IPCA base 2024 (BCB SGS 433)" if deflator else "nenhuma (valores nominais)",
        },
        "municipios": nomes,
        "produtos": produtos_meta,
        "indicadores": ind,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("=== Salvo em %s (%.0f KB) ===", OUT_FILE, OUT_FILE.stat().st_size / 1024)


if __name__ == "__main__":
    main()
