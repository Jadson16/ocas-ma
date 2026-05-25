"""
Baixa o IPCA mensal do BCB (série SGS 433) e calcula deflator anual com base 2024.

Saída: data/ipca_deflator.csv
  ano             — ano
  ipca_anual_pct  — IPCA acumulado no ano (%, composto dos 12 meses)
  price_level     — índice de preços acumulado desde início da série
  deflator_base2024 — fator p/ converter valores do ano para R$ de 2024
                      valor_real2024 = valor_nominal × deflator_base2024

Uso:
  python scripts/fetch_ipca.py
"""

import logging
import time
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

BCB_URL     = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
ANO_INICIO  = 1994   # um ano antes do início dos dados PAM para capturar a base corretamente
ANO_FIM     = 2024
DATA_DIR    = Path(__file__).parent.parent / "data"
OUT_FILE    = DATA_DIR / "ipca_deflator.csv"
RETRY       = 3
SLEEP_RETRY = 10


def fetch_mensal() -> list[dict]:
    params = {
        "formato": "json",
        "dataInicial": f"01/01/{ANO_INICIO}",
        "dataFinal":   f"31/12/{ANO_FIM}",
    }
    for tentativa in range(1, RETRY + 1):
        try:
            r = requests.get(BCB_URL, params=params, timeout=60, verify=False)
            r.raise_for_status()
            dados = r.json()
            log.info("  BCB SGS 433: %d observações mensais carregadas", len(dados))
            return dados
        except Exception as exc:
            log.warning("  Tentativa %d/%d falhou: %s", tentativa, RETRY, exc)
            if tentativa < RETRY:
                time.sleep(SLEEP_RETRY)
    raise RuntimeError("Falha ao baixar IPCA do BCB após todas as tentativas.")


def build_deflator(dados: list[dict]) -> pd.DataFrame:
    records = []
    for item in dados:
        dia, mes, ano = item["data"].split("/")
        records.append({
            "ano": int(ano),
            "mes": int(mes),
            "var_pct": float(item["valor"]),
        })

    df = pd.DataFrame(records).sort_values(["ano", "mes"])

    # Fator anual composto dos 12 meses
    annual: dict[int, float] = {}
    for ano, grp in df.groupby("ano"):
        fator = 1.0
        for v in grp["var_pct"]:
            fator *= (1.0 + v / 100.0)
        annual[ano] = fator

    anos = sorted(annual)
    rows = []
    price_level = 1.0
    for ano in anos:
        price_level *= annual[ano]
        rows.append({
            "ano":            ano,
            "ipca_anual_pct": round((annual[ano] - 1.0) * 100.0, 4),
            "price_level":    round(price_level, 8),
        })

    df_out = pd.DataFrame(rows)

    # Deflator base 2024: D(Y) = P(2024) / P(Y)
    # Valor em 2024 R$ = valor_nominal_Y × D(Y)
    p2024 = df_out.loc[df_out["ano"] == ANO_FIM, "price_level"].values[0]
    df_out["deflator_base2024"] = (p2024 / df_out["price_level"]).round(6)

    return df_out[["ano", "ipca_anual_pct", "price_level", "deflator_base2024"]]


def main() -> None:
    log.info("=== fetch_ipca — início ===")
    dados = fetch_mensal()
    df = build_deflator(dados)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    log.info("=== Salvo em %s (%d anos) ===", OUT_FILE, len(df))
    log.info("  Deflator 1995: %.4f × | Deflator 2024: %.4f ×",
             df.loc[df["ano"] == 1995, "deflator_base2024"].values[0],
             df.loc[df["ano"] == 2024, "deflator_base2024"].values[0])


if __name__ == "__main__":
    main()
