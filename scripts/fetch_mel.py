"""
Coleta dados PPM (mel de abelha) do SIDRA/IBGE para municípios do Maranhão.
Tabela 74 — variáveis 106 (quantidade, kg) e 215 (valor, mil R$).
"""

import time
import requests
import pandas as pd
from pathlib import Path

TABLE = 74
VARIABLES = "106|215"
STATE_CODE = 21
CLASSIFICATION = 80
CATEGORY = 2687          # Mel de abelha
START_YEAR = 1995        # Plano Real
END_YEAR = 2024

DATA_DIR = Path(__file__).parent.parent / "data" / "mel"
OUT_FILE = DATA_DIR / "mel_ppm.csv"


def build_url(years: list) -> str:
    period = "|".join(str(y) for y in years)
    base = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (
        f"{base}/{TABLE}/periodos/{period}/variaveis/{VARIABLES}"
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
    # var 106 = quantidade (kg), var 215 = valor (mil R$)
    df_wide = df_wide.rename(columns={"106": "quantidade_kg", "215": "valor_mil_reais"})
    return df_wide.sort_values(["municipio", "ano"]).reset_index(drop=True)


BATCH_SIZE = 10   # anos por requisição


def main():
    all_years = list(range(START_YEAR, END_YEAR + 1))
    batches = [all_years[i:i+BATCH_SIZE] for i in range(0, len(all_years), BATCH_SIZE)]

    frames = []
    for i, batch in enumerate(batches, 1):
        url = build_url(batch)
        print(f"Lote {i}/{len(batches)}: anos {batch[0]}-{batch[-1]}")
        for tentativa in range(1, 4):
            try:
                resp = requests.get(url, timeout=120, verify=False)
                resp.raise_for_status()
                frames.append(parse_response(resp.json()))
                break
            except Exception as e:
                print(f"  Tentativa {tentativa} falhou: {type(e).__name__}. Aguardando 15s...")
                time.sleep(15)
        else:
            raise RuntimeError(f"Lote {i} falhou apos 3 tentativas.")
        if i < len(batches):
            time.sleep(8)

    df = pd.concat(frames, ignore_index=True).sort_values(["municipio", "ano"]).reset_index(drop=True)

    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Arquivo salvo: {OUT_FILE}")
    print(f"Linhas totais        : {len(df)}")
    print(f"Municipios           : {df['municipio_id'].nunique()}")
    print(f"Periodo              : {df['ano'].min()} - {df['ano'].max()}")
    n_prod = df["quantidade_kg"].notna().sum()
    print(f"Registros com producao: {n_prod} ({n_prod/len(df):.1%})")
    print()
    print(df[df["quantidade_kg"].notna()].nlargest(5, "quantidade_kg")[
        ["municipio", "ano", "quantidade_kg", "valor_mil_reais"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()


