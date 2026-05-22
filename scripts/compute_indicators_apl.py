"""
Identifica APLs (Arranjos Produtivos Locais) no Maranhão cruzando:
  1. LISA HH significativo (p < 0,05) — clustering espacial
  2. QL ≥ limiar (1,0 básico / 1,25 consolidado)
  3. TCG > 0 — crescimento positivo no período

Categorias:
  consolidado  HH sig + QL ≥ 1,25 + TCG > 0 + persistente (≥3 anos de APL em 5)
  emergente    HH sig + QL ≥ 1,0  + TCG > 0  (sem persistência ou QL entre 1,0-1,25)
  retracao     HH sig + QL ≥ 1,0  + TCG ≤ 0  (cluster em declínio)
  potencial    QL ≥ 1,25 + TCG > 0 (sem clustering LISA — especialização local)

Score APL (0–1):
  0,35 * norm(ql)       + 0,25 * lisa_hh_sig
  0,20 * norm(tcg)      + 0,20 * norm(persist)

Entradas : data/indicadores.json, data/espacial.json
Saída    : data/apl.json
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent
DATA_DIR  = ROOT / "data"
IND_FILE  = DATA_DIR / "indicadores.json"
ESP_FILE  = DATA_DIR / "espacial.json"
OUT_FILE  = DATA_DIR / "apl.json"

# ── Parâmetros ──────────────────────────────────────────────────────
QL_APL        = 1.00   # mínimo para qualquer categoria
QL_CONSOL     = 1.25   # mínimo para consolidado
P_LISA        = 0.05   # limiar de significância LISA
PERSIST_ANOS  = 5      # janela de persistência (últimos N anos)
PERSIST_MIN   = 3      # mínimo de anos como APL para ser "consolidado"

# Pesos do score composto
W_QL      = 0.35
W_LISA    = 0.25
W_TCG     = 0.20
W_PERSIST = 0.20

# Normalização
QL_MAX    = 4.00   # QL acima disso → 1,0 na componente
TCG_MAX   = 0.15   # 15% a.a. → 1,0 na componente TCG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(v) -> float | None:
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _norm_ql(ql: float) -> float:
    return min(ql / QL_MAX, 1.0)


def _norm_tcg(tcg: float) -> float:
    return min(max(tcg / TCG_MAX, 0.0), 1.0)


def _norm_persist(p: int) -> float:
    return min(p / PERSIST_ANOS, 1.0)


def score_apl(ql: float, tcg: float, lisa_hh_sig: bool, persist: int) -> float:
    """Score composto APL 0–1."""
    return round(
        W_QL      * _norm_ql(ql) +
        W_LISA    * (1.0 if lisa_hh_sig else 0.0) +
        W_TCG     * _norm_tcg(tcg) +
        W_PERSIST * _norm_persist(persist),
        4,
    )


def categoria(ql: float, tcg: float | None, lisa_hh: bool, lisa_sig: bool,
              persist: int) -> str | None:
    """
    Retorna categoria APL ou None se não qualifica.
    """
    hh_sig = lisa_hh and lisa_sig
    if hh_sig:
        if ql >= QL_APL:
            if tcg is not None and tcg > 0:
                if ql >= QL_CONSOL and persist >= PERSIST_MIN:
                    return "consolidado"
                return "emergente"
            else:
                return "retracao"
    # Sem clustering LISA mas especializado e crescendo
    if ql >= QL_CONSOL and tcg is not None and tcg > 0:
        return "potencial"
    return None


# ---------------------------------------------------------------------------
# Carga de dados
# ---------------------------------------------------------------------------

def load_data() -> tuple[dict, dict]:
    log.info("Carregando indicadores.json...")
    ind = json.loads(IND_FILE.read_text(encoding="utf-8"))
    log.info("Carregando espacial.json...")
    esp = json.loads(ESP_FILE.read_text(encoding="utf-8"))
    return ind, esp


# ---------------------------------------------------------------------------
# Cálculo APL
# ---------------------------------------------------------------------------

def compute_apl(ind: dict, esp: dict) -> dict:
    ql_data  = ind["indicadores"]["ql"]
    tcg_data = ind["indicadores"]["tcg"]
    anos_all = sorted(ind["meta"]["anos_disponiveis"])

    lisa_data  = esp.get("lisa",  {})
    moran_data = esp.get("moran", {})

    cadeias = list(ql_data.keys())
    log.info("  %d cadeias × %d anos", len(cadeias), len(anos_all))

    apl_out:    dict = {}   # apl[cadeia][ano][mid] = {...}
    resumo_out: dict = {}   # resumo[cadeia][ano]   = {...}

    for cadeia in cadeias:
        apl_out[cadeia]    = {}
        resumo_out[cadeia] = {}

        for i_ano, ano in enumerate(anos_all):
            anoS = str(ano)
            ql_ano  = ql_data.get(cadeia, {}).get(anoS, {})
            tcg_ano = tcg_data.get(cadeia, {}).get(anoS, {})
            lisa_ano = lisa_data.get(cadeia, {}).get(anoS, {})
            moran_rec = moran_data.get(cadeia, {}).get(anoS, {})

            if not ql_ano:
                continue

            # Janela de persistência: últimos PERSIST_ANOS anteriores
            anos_passados = anos_all[max(0, i_ano - PERSIST_ANOS + 1): i_ano + 1]

            row:     dict = {}
            n_cat    = {"consolidado": 0, "emergente": 0,
                        "retracao": 0, "potencial": 0}

            for mid, ql_v in ql_ano.items():
                ql_v = _safe(ql_v)
                if ql_v is None or ql_v < QL_APL:
                    continue  # abaixo do mínimo absoluto

                tcg_v   = _safe(tcg_ano.get(mid))
                lisa_v  = lisa_ano.get(mid, {})
                lisa_hh  = lisa_v.get("q") == "HH"
                lisa_sig = lisa_v.get("p", 1.0) < P_LISA
                lisa_p   = _safe(lisa_v.get("p"))

                # Persistência histórica: anos passados onde mid qualificou
                persist = 0
                for pa in anos_passados:
                    paS = str(pa)
                    ql_pa = _safe(ql_data.get(cadeia, {}).get(paS, {}).get(mid))
                    tcg_pa = _safe(tcg_data.get(cadeia, {}).get(paS, {}).get(mid))
                    lisa_pa = lisa_data.get(cadeia, {}).get(paS, {}).get(mid, {})
                    hh_pa = (lisa_pa.get("q") == "HH" and
                             lisa_pa.get("p", 1.0) < P_LISA)
                    # qualifica como APL no ano passado?
                    if (ql_pa and ql_pa >= QL_APL and
                            tcg_pa is not None and tcg_pa > 0 and hh_pa):
                        persist += 1

                cat = categoria(ql_v, tcg_v, lisa_hh, lisa_sig, persist)
                if cat is None:
                    continue

                sc = score_apl(ql_v, tcg_v or 0.0, lisa_hh and lisa_sig, persist)
                rec: dict = {
                    "cat":   cat,
                    "ql":    ql_v,
                    "score": sc,
                    "persist": persist,
                }
                if tcg_v is not None:
                    rec["tcg"] = tcg_v
                if lisa_p is not None:
                    rec["lisa_p"] = lisa_p
                if lisa_v.get("q"):
                    rec["lisa_q"] = lisa_v["q"]

                row[mid] = rec
                n_cat[cat] += 1

            if row:
                apl_out[cadeia][anoS] = row

            n_tot = sum(n_cat.values())
            resumo_out[cadeia][anoS] = {
                "n":     n_tot,
                "n_con": n_cat["consolidado"],
                "n_eme": n_cat["emergente"],
                "n_ret": n_cat["retracao"],
                "n_pot": n_cat["potencial"],
                "I":     _safe(moran_rec.get("I")),
                "I_p":   _safe(moran_rec.get("p")),
            }

        log.info("  %s: %d ano-cadeia com APLs",
                 cadeia, sum(1 for v in resumo_out[cadeia].values() if v["n"] > 0))

    return apl_out, resumo_out


def compute_municipio_index(apl_out: dict, ano_ref: int) -> dict:
    """
    Índice invertido: municipio → {ano: [cadeias com APL]}.
    Apenas para o ano de referência.
    """
    anoS = str(ano_ref)
    mun_index: dict[str, list[str]] = {}
    for cadeia, anos in apl_out.items():
        for mid in anos.get(anoS, {}):
            mun_index.setdefault(mid, []).append(cadeia)
    return {mid: sorted(cadeias) for mid, cadeias in mun_index.items()}


# ---------------------------------------------------------------------------
# Estatísticas globais
# ---------------------------------------------------------------------------

def stats_globais(resumo_out: dict, apl_out: dict, ano_ref: int) -> dict:
    anoS = str(ano_ref)
    n_mun_apls: dict[str, int] = {}   # municipio → n cadeias como APL
    for cadeia, anos in apl_out.items():
        for mid in anos.get(anoS, {}):
            n_mun_apls[mid] = n_mun_apls.get(mid, 0) + 1

    top_muns = sorted(n_mun_apls.items(), key=lambda x: -x[1])[:15]
    cadeias_ranking = sorted(
        [(c, resumo_out[c].get(anoS, {}).get("n", 0)) for c in resumo_out],
        key=lambda x: -x[1],
    )

    return {
        "ano_ref":     ano_ref,
        "n_mun_com_apl": len(n_mun_apls),
        "top_muns_multiplos": top_muns,   # (mid, n_cadeias)
        "cadeias_ranking": cadeias_ranking,  # (cadeia, n_apl)
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_indicators_apl — início ===")

    ind, esp = load_data()
    anos_all = sorted(ind["meta"]["anos_disponiveis"])
    ano_ref  = max(a for a in anos_all if any(
        str(a) in esp["moran"].get(c, {}) for c in esp["moran"]))
    log.info("Ano de referência para resumo: %d", ano_ref)

    log.info("Calculando APLs...")
    apl_out, resumo_out = compute_apl(ind, esp)

    log.info("Construindo índice município→cadeias...")
    mun_index = compute_municipio_index(apl_out, ano_ref)

    log.info("Calculando estatísticas globais...")
    stats = stats_globais(resumo_out, apl_out, ano_ref)

    n_apl_total = sum(
        resumo_out[c].get(str(ano_ref), {}).get("n", 0) for c in resumo_out)
    log.info("  Total APLs (%d): %d mun×cadeia | %d municípios únicos",
             ano_ref, n_apl_total, stats["n_mun_com_apl"])

    # Detalhar por categoria
    for cat in ["consolidado", "emergente", "retracao", "potencial"]:
        key = f"n_{cat[:3]}"
        n = sum(resumo_out[c].get(str(ano_ref), {}).get(key, 0) for c in resumo_out)
        log.info("  %-14s %3d mun×cadeia", cat + ":", n)

    out = {
        "meta": {
            "gerado_em":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ano_ref":         ano_ref,
            "criterios": {
                "ql_min_apl":        QL_APL,
                "ql_min_consolidado": QL_CONSOL,
                "p_lisa":            P_LISA,
                "persist_janela":    PERSIST_ANOS,
                "persist_min":       PERSIST_MIN,
            },
            "score_pesos": {
                "ql": W_QL, "lisa": W_LISA,
                "tcg": W_TCG, "persist": W_PERSIST,
            },
            "categorias": {
                "consolidado": "HH sig + QL≥1,25 + TCG>0 + persistente (≥3/5 anos)",
                "emergente":   "HH sig + QL≥1,0  + TCG>0",
                "retracao":    "HH sig + QL≥1,0  + TCG≤0",
                "potencial":   "QL≥1,25 + TCG>0  (sem cluster LISA)",
            },
        },
        "apl":       apl_out,
        "resumo":    resumo_out,
        "mun_index": mun_index,
        "stats":     stats,
    }

    OUT_FILE.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = OUT_FILE.stat().st_size // 1024
    log.info("=== Salvo em %s (%d KB) ===", OUT_FILE, size_kb)


if __name__ == "__main__":
    main()
