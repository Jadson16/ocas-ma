"""
Coleta dados PPM — produção de origem animal do SIDRA/IBGE para municípios do Maranhão.
Tabela 74 — variáveis 106 (quantidade) e 215 (valor, mil R$), classificação 80.
Salva: data/leite/leite_ppm.csv e data/ovos/ovos_ppm.csv.
"""
import time, requests, pandas as pd, urllib3
from pathlib import Path
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TABLE      = 74
VARS       = "106|215"
CLASSIF    = 80
STATE_CODE = 21
START_YEAR = 1995
END_YEAR   = 2024
BATCH_SIZE = 10
DATA_DIR   = Path(__file__).parent.parent / "data"

# (cat, label, qty_col_name, unit_qty)
PRODUCTS = {
    "leite": (2682, "Leite de vaca", "quantidade_mil_litros", "mil l"),
    "ovos":  (2685, "Ovos de galinha", "quantidade_mil_duzias", "mil dz"),
}


def build_url(cat, batch):
    period = "|".join(str(y) for y in batch)
    base   = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (f"{base}/{TABLE}/periodos/{period}/variaveis/{VARS}"
            f"?localidades=N6[in N3[{STATE_CODE}]]&classificacao={CLASSIF}[{cat}]")


def parse(data, qty_col):
    rows = []
    for var in data:
        vid = str(var["id"])
        for res in var["resultados"]:
            for entry in res["series"]:
                loc = entry["localidade"]
                for year, raw in entry["serie"].items():
                    val = None if raw in ("-", "...") else float(raw.replace(",", "."))
                    rows.append({"municipio_id": loc["id"], "municipio": loc["nome"],
                                 "ano": int(year), "var_id": vid, "valor": val})
    df = pd.DataFrame(rows)
    wide = (df.pivot_table(index=["municipio_id","municipio","ano"],
                           columns="var_id", values="valor")
              .reset_index())
    wide.columns.name = None
    wide = wide.rename(columns={"106": qty_col, "215": "valor_mil_reais"})
    return wide.sort_values(["municipio","ano"]).reset_index(drop=True)


def fetch(key, cat, label, qty_col):
    all_years = list(range(START_YEAR, END_YEAR + 1))
    batches   = [all_years[i:i+BATCH_SIZE] for i in range(0, len(all_years), BATCH_SIZE)]
    frames    = []
    for i, batch in enumerate(batches, 1):
        url = build_url(cat, batch)
        for tentativa in range(1, 4):
            try:
                r = requests.get(url, timeout=120, verify=False)
                r.raise_for_status()
                frames.append(parse(r.json(), qty_col))
                break
            except Exception as e:
                print(f"    Tentativa {tentativa} falhou: {e}. Aguardando 15s...")
                time.sleep(15)
        else:
            print(f"  FALHOU apos 3 tentativas — {key}")
            return
        if i < len(batches):
            time.sleep(8)

    df = pd.concat(frames, ignore_index=True).sort_values(["municipio","ano"]).reset_index(drop=True)
    out = DATA_DIR / key
    out.mkdir(exist_ok=True)
    df.to_csv(out / f"{key}_ppm.csv", index=False, encoding="utf-8-sig")
    n = df[qty_col].notna().sum()
    print(f"  {label}: {df['municipio_id'].nunique()} mun, {n} registros com producao")


def main():
    for key, (cat, label, qty_col, _) in PRODUCTS.items():
        print(f"\n{label}...")
        fetch(key, cat, label, qty_col)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
