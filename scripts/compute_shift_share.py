"""
Decomposição shift-share da produção de soja no Maranhão (1995–2024).

Responde: o crescimento veio de expansão de área ou de ganho de produtividade?

Decomposição (Hayami-Ruttan / Componentes de Crescimento):
  ΔQ = Q_t - Q_{t-1}
     = Ȳ_{t-1} × ΔA   (efeito área     — mais hectares com produtividade antiga)
     + Ā_{t-1} × ΔY   (efeito yield    — mais t/ha na área antiga)
     + ΔA × ΔY         (efeito interação — sinergia entre expansão e ganho)

  onde:
    Q = produção total (ton)
    A = área colhida (ha)
    Y = produtividade = Q / A  (ton/ha)

Cálculo em dois níveis:
  1. Estadual — série ano a ano + agregação por fase
  2. Municipal — contribuição de cada município ao crescimento estadual

Entrada : data/soja/soja_pam.csv   (precisa de area_colhida_ha)
Saída   : data/shift_share_soja.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SOJA_CSV = DATA_DIR / "soja" / "soja_pam.csv"
OUT_FILE = DATA_DIR / "shift_share_soja.json"

# Fases detectadas por compute_soja_article.py
FASES = [
    {"id": 1, "nome": "Fase Pioneira",        "inicio": 1995, "fim": 2005},
    {"id": 2, "nome": "Fase de Consolidação", "inicio": 2005, "fim": 2016},
    {"id": 3, "nome": "Fase de Expansão",     "inicio": 2016, "fim": 2019},
    {"id": 4, "nome": "Fase de Boom",         "inicio": 2019, "fim": 2024},
]


def _safe(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _pct(parte, total) -> float | None:
    if total and total != 0:
        return _safe(parte / total * 100)
    return None


# ---------------------------------------------------------------------------
# Decomposição núcleo
# ---------------------------------------------------------------------------

def decompoe(q0: float, a0: float, q1: float, a1: float) -> dict:
    """
    Decompõe ΔQ entre dois períodos em efeito área, yield e interação.
    Retorna dict com valores absolutos e participações percentuais.
    """
    if a0 <= 0 or a1 <= 0:
        return {}

    y0 = q0 / a0
    y1 = q1 / a1
    dq = q1 - q0
    da = a1 - a0
    dy = y1 - y0

    ef_area   = y0 * da          # efeito área
    ef_yield  = a0 * dy          # efeito produtividade
    ef_inter  = da * dy          # interação

    check = ef_area + ef_yield + ef_inter  # deve ≈ dq

    return {
        "q0":             _safe(q0),
        "q1":             _safe(q1),
        "a0":             _safe(a0),
        "a1":             _safe(a1),
        "y0_ton_ha":      _safe(y0),
        "y1_ton_ha":      _safe(y1),
        "delta_q":        _safe(dq),
        "delta_a":        _safe(da),
        "delta_y":        _safe(dy),
        "ef_area":        _safe(ef_area),
        "ef_yield":       _safe(ef_yield),
        "ef_inter":       _safe(ef_inter),
        "ef_area_pct":    _pct(ef_area,  dq),
        "ef_yield_pct":   _pct(ef_yield, dq),
        "ef_inter_pct":   _pct(ef_inter, dq),
        "dominante":      (
            "área"          if abs(ef_area)  >= abs(ef_yield) and abs(ef_area)  >= abs(ef_inter)
            else "yield"    if abs(ef_yield) >= abs(ef_inter)
            else "interação"
        ),
    }


# ---------------------------------------------------------------------------
# Nível estadual — ano a ano
# ---------------------------------------------------------------------------

def shift_share_estadual(df: pd.DataFrame) -> dict:
    estado = (
        df.groupby("ano")
        .agg(q=("quantidade_ton", "sum"), a=("area_colhida_ha", "sum"))
        .sort_index()
    )
    anos = estado.index.tolist()
    resultado = {}
    for i in range(1, len(anos)):
        a_ant, a_at = anos[i - 1], anos[i]
        row = estado.loc[a_ant]
        row_at = estado.loc[a_at]
        dec = decompoe(row["q"], row["a"], row_at["q"], row_at["a"])
        if dec:
            resultado[str(a_at)] = dec
    return resultado


# ---------------------------------------------------------------------------
# Nível estadual — por fase
# ---------------------------------------------------------------------------

def shift_share_fases(df: pd.DataFrame) -> list[dict]:
    estado = (
        df.groupby("ano")
        .agg(q=("quantidade_ton", "sum"), a=("area_colhida_ha", "sum"))
        .sort_index()
    )
    resultado = []
    for fase in FASES:
        ini, fim = fase["inicio"], fase["fim"]
        if ini not in estado.index or fim not in estado.index:
            continue
        dec = decompoe(
            estado.loc[ini, "q"], estado.loc[ini, "a"],
            estado.loc[fim, "q"], estado.loc[fim, "a"],
        )
        if dec:
            resultado.append({
                "id":   fase["id"],
                "nome": fase["nome"],
                "inicio": ini,
                "fim":    fim,
                **dec,
            })
    return resultado


# ---------------------------------------------------------------------------
# Nível municipal — contribuição ao crescimento estadual por fase
# ---------------------------------------------------------------------------

def shift_share_municipal(df: pd.DataFrame) -> dict:
    """
    Para cada fase, decompõe a contribuição de cada município ao ΔQ estadual.
    Contribuição = (ΔQ_municipal / ΔQ_estadual) × 100
    """
    resultado = {}
    for fase in FASES:
        ini, fim = fase["inicio"], fase["fim"]
        sub_ini = df[df["ano"] == ini].set_index("municipio_id")
        sub_fim = df[df["ano"] == fim].set_index("municipio_id")

        # Municípios presentes em pelo menos um dos anos
        mids = sub_ini.index.union(sub_fim.index)

        dq_estado = (
            sub_fim["quantidade_ton"].sum() - sub_ini["quantidade_ton"].sum()
        )
        if dq_estado == 0:
            continue

        muns = []
        for mid in mids:
            q0 = float(sub_ini.loc[mid, "quantidade_ton"])   if mid in sub_ini.index else 0.0
            a0 = float(sub_ini.loc[mid, "area_colhida_ha"])  if mid in sub_ini.index else 0.0
            q1 = float(sub_fim.loc[mid, "quantidade_ton"])   if mid in sub_fim.index else 0.0
            a1 = float(sub_fim.loc[mid, "area_colhida_ha"])  if mid in sub_fim.index else 0.0
            nome = (
                sub_fim.loc[mid, "municipio"] if mid in sub_fim.index
                else sub_ini.loc[mid, "municipio"]
            )

            dec = decompoe(q0, a0, q1, a1) if (a0 > 0 or a1 > 0) else {}
            contrib_pct = _pct(q1 - q0, dq_estado)

            muns.append({
                "municipio_id":  mid,
                "municipio":     nome,
                "contrib_delta_q_pct": contrib_pct,
                **({k: dec[k] for k in ("ef_area_pct","ef_yield_pct","ef_inter_pct","dominante","y0_ton_ha","y1_ton_ha")} if dec else {}),
            })

        # Ordena pelos maiores contribuidores absolutos
        muns.sort(key=lambda x: abs(x.get("contrib_delta_q_pct") or 0), reverse=True)
        resultado[str(fase["id"])] = {
            "nome":      fase["nome"],
            "inicio":    ini,
            "fim":       fim,
            "dq_estado": _safe(dq_estado),
            "municipios": muns,
        }
    return resultado


# ---------------------------------------------------------------------------
# Série de produtividade estadual
# ---------------------------------------------------------------------------

def serie_produtividade(df: pd.DataFrame) -> dict:
    estado = (
        df.groupby("ano")
        .agg(q=("quantidade_ton", "sum"), a=("area_colhida_ha", "sum"))
        .sort_index()
    )
    return {
        str(ano): {
            "producao_ton":    _safe(row["q"]),
            "area_colhida_ha": _safe(row["a"]),
            "produtividade_ton_ha": _safe(row["q"] / row["a"]) if row["a"] > 0 else None,
        }
        for ano, row in estado.iterrows()
    }


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_shift_share — início ===")

    df = pd.read_csv(SOJA_CSV, dtype={"municipio_id": str})
    df = df[df["quantidade_ton"].notna() & (df["quantidade_ton"] > 0)].copy()

    if "area_colhida_ha" not in df.columns or df["area_colhida_ha"].isna().all():
        log.error("area_colhida_ha ausente. Execute fetch_pam_temp.py soja primeiro.")
        raise SystemExit(1)

    df = df[df["area_colhida_ha"].notna() & (df["area_colhida_ha"] > 0)]
    log.info("  %d registros com área colhida, %d municípios, anos %d–%d",
             len(df), df["municipio_id"].nunique(), df["ano"].min(), df["ano"].max())

    log.info("[1/4] Série de produtividade estadual...")
    serie_prod = serie_produtividade(df)

    log.info("[2/4] Shift-share estadual ano a ano...")
    ss_estadual = shift_share_estadual(df)

    log.info("[3/4] Shift-share por fase...")
    ss_fases = shift_share_fases(df)

    for f in ss_fases:
        log.info("  %s (%d–%d): área=%+.1f%%  yield=%+.1f%%  inter=%+.1f%%  dominante=%s",
                 f["nome"], f["inicio"], f["fim"],
                 f.get("ef_area_pct") or 0,
                 f.get("ef_yield_pct") or 0,
                 f.get("ef_inter_pct") or 0,
                 f.get("dominante", "?"))

    log.info("[4/4] Shift-share municipal por fase...")
    ss_mun = shift_share_municipal(df)

    output = {
        "meta": {
            "gerado_em":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "descricao":  "Decomposição shift-share soja MA — efeito área vs. produtividade",
            "formula":    "ΔQ = Y₀×ΔA (área) + A₀×ΔY (yield) + ΔA×ΔY (interação)",
            "fonte":      "PAM/IBGE — SIDRA tabela 1612",
            "periodo":    f"{df['ano'].min()}–{df['ano'].max()}",
        },
        "serie_produtividade": serie_prod,
        "estadual_ano_a_ano":  ss_estadual,
        "por_fase":            ss_fases,
        "municipal_por_fase":  ss_mun,
    }

    OUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info("=== Salvo em %s (%.0f KB) ===", OUT_FILE, OUT_FILE.stat().st_size / 1024)


if __name__ == "__main__":
    main()
