"""
Análise focada da cadeia soja para artigo científico — Maranhão 1995–2024.

Lacuna 3 — SICOR × LISA: cruza crédito rural soja com clusters HH espaciais
Lacuna 4 — Fases temporais: detecção de breakpoints via RSS mínimo (OLS por segmento)
Lacuna 5 — Concentração: HHI, CR4, CR8, Gini espacial por ano

Entrada:
  data/soja/soja_pam.csv
  data/sicor/custeio_ma_raw.csv
  data/sicor/invest_ma_raw.csv
  data/espacial.json
  data/ipca_deflator.csv

Saída:
  data/soja_artigo.json
"""

import json
import logging
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent
DATA_DIR  = ROOT / "data"
SOJA_CSV  = DATA_DIR / "soja" / "soja_pam.csv"
CUSTEIO   = DATA_DIR / "sicor" / "custeio_ma_raw.csv"
INVEST    = DATA_DIR / "sicor" / "invest_ma_raw.csv"
ESPACIAL  = DATA_DIR / "espacial.json"
DEFLATOR  = DATA_DIR / "ipca_deflator.csv"
OUT_FILE  = DATA_DIR / "soja_artigo.json"

P_THRESH  = 0.05
N_BREAKPOINTS = 3   # divide a série em 4 fases


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _safe(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _norm(s: str) -> str:
    s = s.upper().strip().strip('"')
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def load_deflator() -> dict[int, float]:
    if not DEFLATOR.exists():
        log.warning("ipca_deflator.csv ausente — valores nominais")
        return {}
    df = pd.read_csv(DEFLATOR)
    return dict(zip(df["ano"].astype(int), df["deflator_base2024"].astype(float)))


# ---------------------------------------------------------------------------
# Lacuna 1 residual: carrega soja com produtividade (ton/ha)
# ---------------------------------------------------------------------------

def load_soja(deflator: dict[int, float]) -> pd.DataFrame:
    df = pd.read_csv(SOJA_CSV, dtype={"municipio_id": str})
    df = df[df["quantidade_ton"].notna() & (df["quantidade_ton"] > 0)].copy()

    if deflator:
        df["valor_real2024"] = df.apply(
            lambda r: r["valor_mil_reais"] * deflator.get(int(r["ano"]), 1.0)
            if pd.notna(r.get("valor_mil_reais")) else None,
            axis=1,
        )
    else:
        df["valor_real2024"] = df.get("valor_mil_reais")

    # Produtividade (ton/ha) — só onde há área colhida
    if "area_colhida_ha" in df.columns:
        mask = df["area_colhida_ha"].notna() & (df["area_colhida_ha"] > 0)
        df.loc[mask, "produtividade_ton_ha"] = (
            df.loc[mask, "quantidade_ton"] / df.loc[mask, "area_colhida_ha"]
        )
    return df


# ---------------------------------------------------------------------------
# Lacuna 4 — detecção de fases (breakpoints via RSS mínimo)
# ---------------------------------------------------------------------------

def _rss_linear(y: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y), dtype=float)
    b = np.polyfit(x, y, 1)
    return float(np.sum((y - np.polyval(b, x)) ** 2))


def detect_breakpoints(serie: pd.Series, n_bp: int = N_BREAKPOINTS, min_seg: int = 3) -> list[int]:
    """
    Encontra n_bp breakpoints que minimizam RSS total (OLS linear por segmento).
    Retorna lista de anos (não índices).
    """
    y = np.log1p(serie.values.astype(float))
    n = len(y)
    anos = serie.index.tolist()

    if n_bp == 1:
        best_rss, best_bp = np.inf, None
        for i in range(min_seg, n - min_seg):
            rss = _rss_linear(y[:i]) + _rss_linear(y[i:])
            if rss < best_rss:
                best_rss, best_bp = rss, i
        return [anos[best_bp]]

    if n_bp == 2:
        best_rss, best_bps = np.inf, None
        for i1 in range(min_seg, n - 2 * min_seg):
            for i2 in range(i1 + min_seg, n - min_seg):
                rss = (_rss_linear(y[:i1]) + _rss_linear(y[i1:i2]) + _rss_linear(y[i2:]))
                if rss < best_rss:
                    best_rss, best_bps = rss, (i1, i2)
        return [anos[bp] for bp in best_bps]

    # n_bp == 3
    best_rss, best_bps = np.inf, None
    for i1 in range(min_seg, n - 3 * min_seg):
        for i2 in range(i1 + min_seg, n - 2 * min_seg):
            for i3 in range(i2 + min_seg, n - min_seg):
                rss = (
                    _rss_linear(y[:i1])
                    + _rss_linear(y[i1:i2])
                    + _rss_linear(y[i2:i3])
                    + _rss_linear(y[i3:])
                )
                if rss < best_rss:
                    best_rss, best_bps = rss, (i1, i2, i3)
    return [anos[bp] for bp in best_bps]


def build_fases(df: pd.DataFrame, breakpoints: list[int]) -> list[dict]:
    """
    Calcula estatísticas por fase (produção, área, n_municípios, TCG, produtividade).
    """
    estado = (
        df.groupby("ano")
        .agg(
            producao_ton=("quantidade_ton", "sum"),
            n_municipios=("municipio_id", "nunique"),
        )
        .sort_index()
    )
    if "area_colhida_ha" in df.columns:
        area_grp = df[df["area_colhida_ha"].notna()].groupby("ano")["area_colhida_ha"].sum()
        estado = estado.join(area_grp.rename("area_colhida_ha"), how="left")

    # Limites de fase
    anos = sorted(estado.index)
    limites = [anos[0]] + breakpoints + [anos[-1]]

    fases = []
    nomes_padrao = ["Fase Pioneira", "Fase de Consolidação", "Fase de Expansão", "Fase de Boom"]
    for i in range(len(limites) - 1):
        ini, fim = limites[i], limites[i + 1]
        sub = estado.loc[ini:fim]
        if sub.empty:
            continue

        prod_ini = sub["producao_ton"].iloc[0]
        prod_fim = sub["producao_ton"].iloc[-1]
        n_anos = fim - ini
        tcg = (_safe((prod_fim / prod_ini) ** (1 / n_anos) - 1) if prod_ini > 0 and n_anos > 0 else None)

        fase: dict = {
            "id":             i + 1,
            "nome":           nomes_padrao[i] if i < len(nomes_padrao) else f"Fase {i+1}",
            "inicio":         ini,
            "fim":            fim,
            "n_anos":         n_anos,
            "producao_ton_inicio":  _safe(prod_ini),
            "producao_ton_fim":     _safe(prod_fim),
            "tcg_producao":         tcg,
            "n_municipios_medio":   _safe(sub["n_municipios"].mean()),
            "n_municipios_fim":     int(sub["n_municipios"].iloc[-1]),
        }
        if "area_colhida_ha" in sub.columns:
            area_ini = sub["area_colhida_ha"].iloc[0] if pd.notna(sub["area_colhida_ha"].iloc[0]) else None
            area_fim = sub["area_colhida_ha"].iloc[-1] if pd.notna(sub["area_colhida_ha"].iloc[-1]) else None
            fase["area_colhida_ha_inicio"] = _safe(area_ini)
            fase["area_colhida_ha_fim"]    = _safe(area_fim)
        fases.append(fase)

    return fases


# ---------------------------------------------------------------------------
# Lacuna 5 — Concentração espacial (HHI, CR4, CR8, Gini)
# ---------------------------------------------------------------------------

def _gini(shares: np.ndarray) -> float:
    s = np.sort(shares)
    n = len(s)
    if n == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * s) / (n * np.sum(s))) - (n + 1) / n)


def compute_concentracao(df: pd.DataFrame) -> dict[str, dict]:
    result: dict = {}
    for ano, grp in df.groupby("ano"):
        total = grp["quantidade_ton"].sum()
        if total == 0:
            continue
        shares = (grp["quantidade_ton"] / total).values
        shares_sorted = np.sort(shares)[::-1]
        hhi  = float(np.sum(shares ** 2))
        cr4  = float(shares_sorted[:4].sum())
        cr8  = float(shares_sorted[:8].sum())
        gini = _gini(shares)
        # Top 4 municípios
        top4 = (
            grp.nlargest(4, "quantidade_ton")[["municipio", "quantidade_ton"]]
            .assign(share_pct=lambda x: (x["quantidade_ton"] / total * 100).round(2))
            [["municipio", "share_pct"]]
            .to_dict("records")
        )
        result[str(ano)] = {
            "hhi":              round(hhi, 4),
            "cr4":              round(cr4, 4),
            "cr8":              round(cr8, 4),
            "gini":             round(gini, 4),
            "n_municipios":     int(len(grp)),
            "producao_ton_total": _safe(total),
            "top4":             top4,
        }
    return result


# ---------------------------------------------------------------------------
# Lacuna 3 — SICOR × LISA
# ---------------------------------------------------------------------------

def load_sicor_soja() -> pd.DataFrame:
    """Carrega custeio + investimento SICOR filtrados para soja."""
    frames = []
    for fpath, col_val in [(CUSTEIO, "vl_custeio"), (INVEST, "vl_invest")]:
        if not fpath.exists():
            log.warning("  %s não encontrado", fpath.name)
            continue
        usecols_base = ["municipio", "produto", "ano", col_val]
        has_ibge = "cod_ibge" in pd.read_csv(fpath, nrows=0).columns
        if has_ibge:
            usecols_base = ["cod_ibge"] + usecols_base
        df = pd.read_csv(fpath, usecols=usecols_base, dtype={"cod_ibge": str})
        df = df.rename(columns={col_val: "vl_credito"})
        df["produto_norm"] = df["produto"].apply(_norm)
        df = df[df["produto_norm"].str.contains("SOJA", na=False)].copy()
        if "cod_ibge" in df.columns:
            df["cod_ibge"] = df["cod_ibge"].str.zfill(7)
        frames.append(df)
        log.info("  %s: %d operações soja", fpath.name, len(df))

    if not frames:
        return pd.DataFrame()
    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all[df_all["vl_credito"].notna() & (df_all["vl_credito"] > 0)]
    return df_all


def load_lisa_soja() -> dict[str, dict[str, dict]]:
    """Retorna {ano_str: {cod_ibge: {q, p}}} para soja."""
    if not ESPACIAL.exists():
        log.warning("espacial.json não encontrado")
        return {}
    data = json.loads(ESPACIAL.read_text(encoding="utf-8"))
    return data.get("lisa", {}).get("soja", {})


def compute_sicor_lisa(df_sicor: pd.DataFrame, lisa: dict) -> dict:
    """
    Por ano: cruza municípios com crédito soja vs. municípios HH significativos.
    Retorna estrutura anual com cobertura de crédito nos clusters.
    """
    if df_sicor.empty or not lisa:
        return {}

    # Agrega crédito por município × ano
    group_cols = ["cod_ibge", "ano"] if "cod_ibge" in df_sicor.columns else ["municipio", "ano"]
    vcr_agg = (
        df_sicor.groupby(group_cols)["vl_credito"]
        .sum()
        .reset_index()
        .rename(columns={"vl_credito": "vcr"})
    )

    anos_sicor = sorted(vcr_agg["ano"].unique().astype(int))
    resultado: dict = {}

    for ano in anos_sicor:
        ano_s = str(ano)
        lisa_ano = lisa.get(ano_s, {})

        # Municípios HH significativos
        hh_sig = {mid for mid, v in lisa_ano.items() if v["q"] == "HH" and v["p"] < P_THRESH}

        vcr_ano = vcr_agg[vcr_agg["ano"] == ano].copy()
        vcr_total = float(vcr_ano["vcr"].sum())

        muns_credito = set()
        if "cod_ibge" in vcr_ano.columns:
            muns_credito = set(vcr_ano["cod_ibge"].astype(str))

        hh_com_credito  = hh_sig & muns_credito
        vcr_em_hh = float(
            vcr_ano[vcr_ano.get("cod_ibge", vcr_ano.get("municipio")).astype(str).isin(hh_sig)]["vcr"].sum()
        ) if not vcr_ano.empty else 0.0

        resultado[ano_s] = {
            "n_hh_sig":           len(hh_sig),
            "n_muns_com_credito": len(muns_credito),
            "n_hh_com_credito":   len(hh_com_credito),
            "cobertura_credito_hh_pct": round(len(hh_com_credito) / len(hh_sig) * 100, 1) if hh_sig else None,
            "vcr_total_r":        round(vcr_total, 0),
            "vcr_em_hh_r":        round(vcr_em_hh, 0),
            "share_vcr_hh_pct":   round(vcr_em_hh / vcr_total * 100, 1) if vcr_total > 0 else None,
        }

    return resultado


# ---------------------------------------------------------------------------
# Série estadual anual
# ---------------------------------------------------------------------------

def build_serie_estadual(df: pd.DataFrame, deflator: dict[int, float]) -> dict:
    grp = df.groupby("ano")
    producao    = grp["quantidade_ton"].sum()
    n_muns      = grp["municipio_id"].nunique()
    valor_nom   = grp["valor_mil_reais"].sum() if "valor_mil_reais" in df.columns else None
    valor_real  = grp["valor_real2024"].sum()  if "valor_real2024"  in df.columns else None

    anos = sorted(producao.index.tolist())
    taxa_cresc = {}
    for i in range(1, len(anos)):
        a_ant = anos[i - 1]
        a_at  = anos[i]
        v_ant = producao[a_ant]
        v_at  = producao[a_at]
        if v_ant > 0:
            taxa_cresc[a_at] = round((v_at / v_ant - 1) * 100, 2)

    result: dict = {
        "anos":        anos,
        "producao_ton": {str(a): _safe(producao[a]) for a in anos},
        "n_municipios": {str(a): int(n_muns[a]) for a in anos},
        "taxa_cresc_pct": {str(a): taxa_cresc.get(a) for a in anos if a in taxa_cresc},
    }
    if valor_nom is not None:
        result["valor_nominal_mil_reais"] = {str(a): _safe(valor_nom.get(a)) for a in anos}
    if valor_real is not None:
        result["valor_real2024_mil_reais"] = {str(a): _safe(valor_real.get(a)) for a in anos}

    # Área colhida estadual
    if "area_colhida_ha" in df.columns:
        area = df[df["area_colhida_ha"].notna()].groupby("ano")["area_colhida_ha"].sum()
        result["area_colhida_ha"] = {str(a): _safe(area.get(a)) for a in anos}

    return result


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_soja_article — início ===")

    deflator = load_deflator()
    df = load_soja(deflator)
    log.info("  Soja: %d registros, %d municípios, anos %d–%d",
             len(df), df["municipio_id"].nunique(),
             df["ano"].min(), df["ano"].max())

    # --- Série estadual ---
    log.info("[1/4] Série estadual...")
    serie = build_serie_estadual(df, deflator)

    # --- Lacuna 5: Concentração ---
    log.info("[2/4] Lacuna 5 — Concentração (HHI, CR4, CR8, Gini)...")
    concentracao = compute_concentracao(df)

    # --- Lacuna 4: Fases ---
    log.info("[3/4] Lacuna 4 — Detecção de fases (breakpoints)...")
    producao_estadual = df.groupby("ano")["quantidade_ton"].sum().sort_index()
    breakpoints = detect_breakpoints(producao_estadual, n_bp=N_BREAKPOINTS)
    log.info("  Breakpoints detectados: %s", breakpoints)
    fases = build_fases(df, breakpoints)

    # --- Lacuna 3: SICOR × LISA ---
    log.info("[4/4] Lacuna 3 — SICOR × LISA soja...")
    df_sicor = load_sicor_soja()
    lisa_soja = load_lisa_soja()
    sicor_lisa = compute_sicor_lisa(df_sicor, lisa_soja)

    # --- Salva ---
    output = {
        "meta": {
            "gerado_em":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "descricao":      "Análise soja Maranhão para artigo científico",
            "periodo":        f"{df['ano'].min()}–{df['ano'].max()}",
            "n_municipios":   int(df["municipio_id"].nunique()),
            "n_registros":    int(len(df)),
            "deflacao":       "IPCA base 2024 (BCB SGS 433)" if deflator else "nenhuma",
            "breakpoints":    breakpoints,
            "p_threshold_lisa": P_THRESH,
        },
        "serie_estadual":  serie,
        "concentracao":    concentracao,
        "fases":           fases,
        "sicor_lisa":      sicor_lisa,
    }

    OUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info("=== Salvo em %s (%.0f KB) ===", OUT_FILE, OUT_FILE.stat().st_size / 1024)


if __name__ == "__main__":
    main()
