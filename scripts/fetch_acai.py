"""
Coleta dados PEVS (açaí) do SIDRA/IBGE para municípios do Maranhão.
Tabela 289 — variáveis 144 (quantidade, t) e 145 (valor, mil R$).
"""

import requests
import pandas as pd
from pathlib import Path

TABLE = 289
VARIABLES = "144|145"
STATE_CODE = 21
CLASSIFICATION = 193
CATEGORY = 3403          # Açaí (bagas)
START_YEAR = 1994        # Plano Real
END_YEAR = 2024

DATA_DIR = Path(__file__).parent.parent / "data" / "acai"
OUT_FILE = DATA_DIR / "acai_pevs.csv"


def build_url() -> str:
    years = "|".join(str(y) for y in range(START_YEAR, END_YEAR + 1))
    base = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (
        f"{base}/{TABLE}/periodos/{years}/variaveis/{VARIABLES}"
        f"?localidades=N6[in N3[{STATE_CODE}]]"
        f"&classificacao={CLASSIFICATION}[{CATEGORY}]"
    )


def parse_response(data: list) -> pd.DataFrame:
    rows = []
    for var in data:
        var_id = var["id"]
        for resultado in var["resultados"]:
            for entry in resultado["series"]:
                loc = entry["localidade"]
                for year, raw in entry["serie"].items():
                    value = None if raw in ("-", "...") else float(raw.replace(",", "."))
                    rows.append({
                        "municipio_id": loc["id"],
                        "municipio": loc["nome"],
                        "ano": int(year),
                        "var_id": var_id,
                        "valor": value,
                    })

    df = pd.DataFrame(rows)
    df_wide = (
        df.pivot_table(
            index=["municipio_id", "municipio", "ano"],
            columns="var_id",
            values="valor",
        )
        .reset_index()
    )
    df_wide.columns.name = None
    df_wide = df_wide.rename(columns={"144": "quantidade_ton", "145": "valor_mil_reais"})
    return df_wide.sort_values(["municipio", "ano"]).reset_index(drop=True)


def main():
    url = build_url()
    print(f"Requisicao SIDRA (acai):\n{url}\n")

    resp = requests.get(url, timeout=180)
    resp.raise_for_status()

    df = parse_response(resp.json())

    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Arquivo salvo: {OUT_FILE}")
    print(f"Linhas totais        : {len(df)}")
    print(f"Municipios           : {df['municipio_id'].nunique()}")
    print(f"Periodo              : {df['ano'].min()} - {df['ano'].max()}")
    n_prod = df["quantidade_ton"].notna().sum()
    print(f"Registros com producao: {n_prod} ({n_prod/len(df):.1%})")


if __name__ == "__main__":
    main()
