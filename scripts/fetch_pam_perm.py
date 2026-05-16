"""
Coleta dados PAM — lavouras permanentes do SIDRA/IBGE para municípios do Maranhão.
Tabela 1613 — variáveis 214 (quantidade, t) e 215 (valor, mil R$), classificação 82.
Salva um CSV por produto em data/{key}/{key}_pam.csv.
"""
import time, requests, pandas as pd, urllib3
from pathlib import Path
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TABLE      = 1613
VARS       = "214|215"
CLASSIF    = 82
STATE_CODE = 21
START_YEAR = 1995
END_YEAR   = 2024
BATCH_SIZE = 10
DATA_DIR   = Path(__file__).parent.parent / "data"

PRODUCTS = {
    "banana":        (2720,  "Banana (cacho)"),
    "castanha_caju": (2725,  "Castanha de caju"),
    "coco":          (2727,  "Coco-da-baia"),
    "laranja":       (2733,  "Laranja"),
    "acai_cult":     (45981, "Acai (cultivado)"),
    "mamao":         (2736,  "Mamao"),
    "manga":         (2737,  "Manga"),
    "maracuja":      (2738,  "Maracuja"),
    "borracha":      (2721,  "Borracha (latex coagulado)"),
}


def build_url(cat, batch):
    period = "|".join(str(y) for y in batch)
    base   = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (f"{base}/{TABLE}/periodos/{period}/variaveis/{VARS}"
            f"?localidades=N6[in N3[{STATE_CODE}]]&classificacao={CLASSIF}[{cat}]")


def parse(data):
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
    wide = wide.rename(columns={"214": "quantidade_ton", "215": "valor_mil_reais"})
    return wide.sort_values(["municipio","ano"]).reset_index(drop=True)


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
    df.to_csv(out / f"{key}_pam.csv", index=False, encoding="utf-8-sig")
    n = df["quantidade_ton"].notna().sum()
    print(f"  {label}: {df['municipio_id'].nunique()} mun, {n} registros com producao")


def main():
    for key, (cat, label) in PRODUCTS.items():
        print(f"\n{label}...")
        fetch(key, cat, label)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
