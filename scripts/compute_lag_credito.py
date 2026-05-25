"""
Análise de lag: crédito rural SICOR soja(t) → produção PAM(t+1).

Testa a hipótese de que o crédito de custeio precede e prediz a expansão
da produção de soja no Maranhão (Lacuna 3 aprofundamento).

Correlação de Pearson com lags 0, 1 e 2 anos:
  - Nível estadual  (n ≈ 10 pares, 2013–2024)
  - Nível municipal (mínimo MIN_OBS pares por município)

Deflação: VCR deflacionado pelo IPCA base 2024.

Saída: data/lag_credito_soja.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "lag_credito_soja.json"

MIN_OBS = 5   # mínimo de pares (t, t+lag) por município para correlação
LAGS    = [0, 1, 2]


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


def _pearson(x: np.ndarray, y: np.ndarray) -> dict:
    """Retorna r, p-value, n, IC95% (Fisher z)."""
    n = len(x)
    if n < 3:
        return {}
    r, p = stats.pearsonr(x, y)
    # IC 95% via transformada de Fisher
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    lo = np.tanh(z - 1.96 * se)
    hi = np.tanh(z + 1.96 * se)
    return {
        "r":      _safe(r),
        "p":      _safe(p),
        "n":      n,
        "ic95_lo": _safe(lo),
        "ic95_hi": _safe(hi),
        "sig_05": bool(p < 0.05),
        "sig_10": bool(p < 0.10),
    }


# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

def load_deflator() -> dict[int, float]:
    path = DATA_DIR / "ipca_deflator.csv"
    if not path.exists():
        log.warning("ipca_deflator.csv não encontrado — VCR em valores nominais")
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["ano"].astype(int), df["deflator_base2024"].astype(float)))


def load_vcr(deflator: dict[int, float]) -> pd.DataFrame:
    """
    Agrega VCR de custeio soja por (cod_ibge, ano).
    Retorna DataFrame com colunas: cod_ibge, municipio, ano, vcr_real2024.
    """
    df = pd.read_csv(DATA_DIR / "sicor" / "custeio_ma_raw.csv")
    soja = df[df["produto"].str.upper().str.contains("SOJA", na=False)].copy()

    # Deflaciona
    if deflator:
        soja["vcr_real"] = soja.apply(
            lambda r: r["vl_custeio"] * deflator.get(int(r["ano"]), 1.0), axis=1
        )
    else:
        soja["vcr_real"] = soja["vl_custeio"]

    agg = (
        soja.groupby(["cod_ibge", "municipio", "ano"])["vcr_real"]
        .sum()
        .reset_index()
        .rename(columns={"vcr_real": "vcr_real2024", "cod_ibge": "municipio_id"})
    )
    agg["municipio_id"] = agg["municipio_id"].astype(str)
    return agg


def load_producao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "soja" / "soja_pam.csv",
                     dtype={"municipio_id": str}, encoding="utf-8-sig")
    df = df[df["quantidade_ton"].notna() & (df["quantidade_ton"] > 0)].copy()
    return df[["municipio_id", "municipio", "ano", "quantidade_ton"]]


# ---------------------------------------------------------------------------
# Nível estadual — série anual + correlações com vários lags
# ---------------------------------------------------------------------------

def analise_estadual(vcr: pd.DataFrame, prod: pd.DataFrame) -> dict:
    vcr_est = vcr.groupby("ano")["vcr_real2024"].sum()
    prod_est = prod.groupby("ano")["quantidade_ton"].sum()

    anos_vcr  = sorted(vcr_est.index)
    anos_prod = sorted(prod_est.index)

    # Série histórica para contextualização
    serie = {}
    for ano in sorted(set(anos_vcr) | set(anos_prod)):
        serie[str(ano)] = {
            "vcr_real2024":   _safe(vcr_est.get(ano)),
            "producao_ton":   _safe(prod_est.get(ano)),
        }

    # Correlações por lag
    corr_lags = {}
    for lag in LAGS:
        pares = []
        for ano_t in anos_vcr:
            ano_t1 = ano_t + lag
            if ano_t1 in prod_est.index:
                pares.append((vcr_est[ano_t], prod_est[ano_t1]))
        if len(pares) >= 3:
            xs = np.array([p[0] for p in pares])
            ys = np.array([p[1] for p in pares])
            res = _pearson(xs, ys)
            res["anos_t"] = [p[0] for p in [(ano_t, ano_t + lag)
                             for ano_t in anos_vcr if (ano_t + lag) in prod_est.index]]
            corr_lags[str(lag)] = res

    return {"serie": serie, "correlacoes_por_lag": corr_lags}


# ---------------------------------------------------------------------------
# Nível municipal — correlação VCR(t) → prod(t+lag) por município
# ---------------------------------------------------------------------------

def analise_municipal(vcr: pd.DataFrame, prod: pd.DataFrame, lag: int) -> list[dict]:
    vcr_piv  = vcr.pivot_table(index="municipio_id", columns="ano", values="vcr_real2024", aggfunc="sum")
    prod_piv = prod.pivot_table(index="municipio_id", columns="ano", values="quantidade_ton", aggfunc="sum")

    resultados = []
    mids = vcr_piv.index.union(prod_piv.index)

    for mid in mids:
        xs, ys, anos_t = [], [], []
        for ano_t in sorted(vcr_piv.columns):
            ano_t1 = ano_t + lag
            if mid not in vcr_piv.index:
                continue
            if ano_t1 not in prod_piv.columns or mid not in prod_piv.index:
                continue
            v_vcr  = vcr_piv.at[mid, ano_t]
            v_prod = prod_piv.at[mid, ano_t1]
            if pd.notna(v_vcr) and pd.notna(v_prod) and v_vcr > 0 and v_prod > 0:
                xs.append(float(v_vcr))
                ys.append(float(v_prod))
                anos_t.append(int(ano_t))

        if len(xs) < MIN_OBS:
            continue

        nome = (
            vcr.loc[vcr["municipio_id"] == mid, "municipio"].iloc[0]
            if not vcr.loc[vcr["municipio_id"] == mid].empty
            else prod.loc[prod["municipio_id"] == mid, "municipio"].iloc[0]
            if not prod.loc[prod["municipio_id"] == mid].empty
            else mid
        )

        res = _pearson(np.array(xs), np.array(ys))
        resultados.append({
            "municipio_id": mid,
            "municipio":    nome,
            "n_pares":      len(xs),
            **res,
        })

    # Ordena por |r| decrescente
    resultados.sort(key=lambda x: abs(x.get("r") or 0), reverse=True)
    return resultados


# ---------------------------------------------------------------------------
# Sumário interpretativo
# ---------------------------------------------------------------------------

def _sumario_lag(corr_lags: dict) -> dict:
    """Identifica lag de maior correlação e resume resultados."""
    best_lag = max(
        corr_lags,
        key=lambda k: abs(corr_lags[k].get("r") or 0),
        default=None,
    )
    return {
        "melhor_lag":      int(best_lag) if best_lag else None,
        "r_melhor_lag":    corr_lags[best_lag]["r"] if best_lag else None,
        "p_melhor_lag":    corr_lags[best_lag]["p"] if best_lag else None,
        "sig_05_melhor":   corr_lags[best_lag].get("sig_05") if best_lag else None,
        "interpretacao": (
            "crédito precede produção"         if best_lag and int(best_lag) > 0
            else "correlação contemporânea"    if best_lag and int(best_lag) == 0
            else "dados insuficientes"
        ),
    }


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_lag_credito — início ===")

    deflator = load_deflator()
    log.info("  Deflator %s", "carregado" if deflator else "ausente (nominal)")

    vcr  = load_vcr(deflator)
    prod = load_producao()

    log.info("  VCR  soja: %d mun × anos %d–%d",
             vcr["municipio_id"].nunique(), vcr["ano"].min(), vcr["ano"].max())
    log.info("  Prod soja: %d mun × anos %d–%d",
             prod["municipio_id"].nunique(), prod["ano"].min(), prod["ano"].max())

    log.info("[1/3] Análise estadual ...")
    est = analise_estadual(vcr, prod)
    for lag_k, res in est["correlacoes_por_lag"].items():
        sig = "*" if res.get("sig_05") else ("+" if res.get("sig_10") else " ")
        log.info("  lag=%s: r=%.3f  p=%.3f %s  n=%d",
                 lag_k, res.get("r", 0), res.get("p", 1), sig, res.get("n", 0))

    log.info("[2/3] Análise municipal (lag=1) ...")
    mun_lag1 = analise_municipal(vcr, prod, lag=1)
    sig_pos = [m for m in mun_lag1 if m.get("sig_05") and (m.get("r") or 0) > 0]
    sig_neg = [m for m in mun_lag1 if m.get("sig_05") and (m.get("r") or 0) < 0]
    log.info("  %d municípios analisados, %d r>0 sig., %d r<0 sig.",
             len(mun_lag1), len(sig_pos), len(sig_neg))
    for m in mun_lag1[:5]:
        log.info("  %-30s r=%.3f p=%.3f n=%d",
                 m["municipio"], m.get("r", 0), m.get("p", 1), m.get("n_pares", 0))

    log.info("[3/3] Análise municipal comparativa (lag=0, 1, 2) ...")
    mun_lags = {
        str(lag): analise_municipal(vcr, prod, lag=lag) for lag in LAGS
    }
    # Conta significativos por lag
    for lag_k, muns in mun_lags.items():
        n_sig = sum(1 for m in muns if m.get("sig_05"))
        log.info("  lag=%s: %d municípios sig.", lag_k, n_sig)

    sumario = _sumario_lag(est["correlacoes_por_lag"])
    log.info("  Sumário: melhor_lag=%s, r=%.3f, p=%.3f — %s",
             sumario["melhor_lag"], sumario.get("r_melhor_lag") or 0,
             sumario.get("p_melhor_lag") or 1, sumario["interpretacao"])

    output = {
        "meta": {
            "gerado_em":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "descricao":  "Lag crédito SICOR custeio soja(t) → produção PAM(t+lag)",
            "deflacao":   "IPCA base 2024 (BCB SGS 433)" if deflator else "nenhuma",
            "lags_testados": LAGS,
            "min_obs_mun":   MIN_OBS,
            "fonte_vcr":  "SICOR/BCB — custeio soja MA",
            "fonte_prod": "PAM/IBGE — SIDRA tabela 1612",
        },
        "sumario":  sumario,
        "estadual": est,
        "municipal_por_lag": mun_lags,
    }

    OUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info("=== Salvo em %s (%.0f KB) ===", OUT_FILE, OUT_FILE.stat().st_size / 1024)


if __name__ == "__main__":
    main()
