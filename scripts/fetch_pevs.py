"""
Coleta dados PEVS do SIDRA/IBGE para todos os produtos de extrativismo
vegetal monitorados pelo OCAS-MA.
Tabela 289 — var. 144 (quantidade, t) e 145 (valor, mil R$).

Para adicionar um novo produto PEVS: inclua uma entrada em PRODUCTS com
a chave do produto, o código de categoria do IBGE e o nome do arquivo CSV.
"""

import logging
import time

import pandas as pd
import requests
import urllib3

from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

TABLE          = 289
VARIABLES      = "144|145"
STATE_CODE     = 21       # Maranhão
CLASSIFICATION = 193
START_YEAR     = 1995     # Plano Real — evita incompatibilidade entre moedas
END_YEAR       = 2024

DATA_DIR = Path(__file__).parent.parent / "data"

# chave → (categoria IBGE, nome do csv de saída)
# A chave é usada como nome do subdiretório em data/
PRODUCTS: dict[str, tuple[int, str]] = {
    "babacu":         (3439, "babacau_pevs.csv"),   # nome histórico mantido
    "acai":           (3403, "acai_pevs.csv"),
    "buriti":         (3423, "buriti_pevs.csv"),
    "carnauba":       (3420, "carnauba_pevs.csv"),
    "carnauba_fibra": (3424, "carnauba_fibra_pevs.csv"),
    "piacava":        (3425, "piacava_pevs.csv"),
}


def _build_url(category: int) -> str:
    years = "|".join(str(y) for y in range(START_YEAR, END_YEAR + 1))
    base  = "https://servicodados.ibge.gov.br/api/v3/agregados"
    return (
        f"{base}/{TABLE}/periodos/{years}/variaveis/{VARIABLES}"
        f"?localidades=N6[in N3[{STATE_CODE}]]"
        f"&classificacao={CLASSIFICATION}[{category}]"
    )


def _parse(data: list) -> pd.DataFrame:
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
                        "municipio":    loc["nome"],
                        "ano":          int(year),
                        "var_id":       var_id,
                        "valor":        value,
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


def fetch_product(key: str, category: int, csv_name: str) -> bool:
    """Coleta um produto PEVS e salva o CSV. Retorna True se bem-sucedido."""
    url      = _build_url(category)
    out_dir  = DATA_DIR / key
    out_file = out_dir / csv_name

    for attempt in range(1, 4):
        try:
            resp = requests.get(url, timeout=180, verify=False)
            resp.raise_for_status()
            break
        except Exception as exc:
            log.warning("  tentativa %d/3 falhou: %s", attempt, exc)
            if attempt == 3:
                log.error("  %-18s ERRO — ignorado após 3 tentativas", key)
                return False
            time.sleep(10)

    df = _parse(resp.json())
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False, encoding="utf-8-sig")

    n_mun  = df["municipio_id"].nunique()
    n_prod = int(df["quantidade_ton"].notna().sum())
    log.info(
        "  %-18s OK  %d municípios · %d registros com produção (%s–%s)",
        key, n_mun, n_prod, df["ano"].min(), df["ano"].max(),
    )
    return True


def main() -> None:
    log.info("=== PEVS — início da coleta (%d produtos) ===", len(PRODUCTS))
    erros = []
    for key, (category, csv_name) in PRODUCTS.items():
        ok = fetch_product(key, category, csv_name)
        if not ok:
            erros.append(key)

    total = len(PRODUCTS)
    ok    = total - len(erros)
    if erros:
        log.error("=== PEVS — %d/%d com sucesso · falhas: %s ===", ok, total, erros)
        raise SystemExit(1)
    else:
        log.info("=== PEVS — %d/%d com sucesso ===", ok, total)


if __name__ == "__main__":
    main()
