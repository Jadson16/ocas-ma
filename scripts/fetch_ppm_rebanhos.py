"""
Coleta dados PPM — efetivo de rebanhos do SIDRA/IBGE para municípios do Maranhão.
Tabela 3939 — variável 105 (efetivo, cabeças), classificação 79.
Salva um CSV por produto em data/{key}/{key}_ppm.csv.
"""
import time, requests, pandas as pd, urllib3
from pathlib import Path
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TABLE      = 3939
VAR        = "105"
CLASSIF    = 79
STATE_CODE = 21
START_YEAR = 1995
END_YEAR   = 2024
BATCH_SIZE = 10
DATA_DIR   = Path(__file__).parent.parent / "data"

PRODUCTS = {
    "bovino":    (2670,  "Bovino"),
    "bubalino":  (2675,  "Bubalino"),
    "equino":    (2672,  "Equino"),
    "suino":     (32794, "Suino"),
    "caprino":   (2681,  "Caprino"),
    "ovino":     (2677,  "Ovino"),
    "galinaceo": (32796, "Galinaceos"),
}


def build_url(cat, batch):
    period = "|".join(str(y) for y in batch)
    base   = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (f"{base}/{TABLE}/periodos/{period}/variaveis/{VAR}"
            f"?localidades=N6[in N3[{STATE_CODE}]]&classificacao={CLASSIF}[{cat}]")


def parse(data):
    rows = []
    for var in data:
        for res in var["resultados"]:
            for entry in res["series"]:
                loc = entry["localidade"]
                for year, raw in entry["serie"].items():
                    val = None if raw in ("-", "...") else float(raw.replace(",", "."))
                    rows.append({"municipio_id": loc["id"], "municipio": loc["nome"],
                                 "ano": int(year), "efetivo_cabecas": val})
    return (pd.DataFrame(rows)
              .sort_values(["municipio","ano"])
              .reset_index(drop=True))


def fetch(key, cat, label):
    all_years = list(range(START_YEAR, END_YEAR + 1))
    batches   = [all_years[i:i+BATCH_SIZE] for i in range(0, len(all_years), BATCH_SIZE)]
    frames    = []
    for i, batch in enumerate(batches, 1):
        url = build_url(cat, batch)
        for tentativa in range(1, 4):
            try:
                r = requests.get(url, timeout=120, verify=False)
                r.raise_for_status()
                frames.append(parse(r.json()))
                break
            except Exception as e:
                print(f"    Tentativa {tentativa} falhou: {e}. Aguardando 10s...")
                time.sleep(10)
        else:
            print(f"  FALHOU apos 3 tentativas — {key}")
            return
        if i < len(batches):
            time.sleep(4)

    df = pd.concat(frames, ignore_index=True).sort_values(["municipio","ano"]).reset_index(drop=True)
    out = DATA_DIR / key
    out.mkdir(exist_ok=True)
    df.to_csv(out / f"{key}_ppm.csv", index=False, encoding="utf-8-sig")
    n = df["efetivo_cabecas"].notna().sum()
    print(f"  {label}: {df['municipio_id'].nunique()} mun, {n} registros")


def main():
    for key, (cat, label) in PRODUCTS.items():
        print(f"\n{label}...")
        fetch(key, cat, label)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
