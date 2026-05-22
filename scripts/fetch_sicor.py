"""
Coleta dados de crédito rural (SICOR/BCB) para o Maranhão.

Fontes:
  - CusteioMunicipioProduto  → custeio agrícola por município e produto
  - InvestMunicipioProduto   → investimento agrícola por município e produto

Estratégia: paginação por ano+mês (evita limite de 5000 registros/req).
Filtros:
  - Custeio : codIbge ge '2100000' and codIbge le '2199999'  (IBGE MA = 21xxxxx)
  - Investimento: cdEstado eq '11'  (código BCB para MA)

Saída:
  data/sicor/custeio_ma.csv
  data/sicor/invest_ma.csv
"""

import requests
import urllib3
import urllib.parse
import pandas as pd
import time
import sys
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata"
OUT_DIR = Path(__file__).parent.parent / "data" / "sicor"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ANO_INICIO = 2013
ANO_FIM = 2025
MESES = [f"{m:02d}" for m in range(1, 13)]
MAX_TOP = 5000
RETRY = 3
SLEEP_RETRY = 15

# Campos relevantes de cada endpoint
CAMPOS_CUSTEIO = [
    "codIbge", "Municipio", "nomeProduto",
    "AnoEmissao", "MesEmissao",
    "cdPrograma", "cdFonteRecurso",
    "VlCusteio", "AreaCusteio",
]
CAMPOS_INVEST = [
    "cdMunicipio", "Municipio", "nomeProduto",
    "AnoEmissao", "MesEmissao",
    "cdPrograma", "cdFonteRecurso",
    "VlInvest", "AreaInvest",
    "cdEstado",
]


def fetch(endpoint: str, filtro: str) -> list[dict]:
    url = (
        f"{BASE}/{endpoint}"
        f"?$top={MAX_TOP}&$format=json"
        f"&$filter={urllib.parse.quote(filtro)}"
    )
    for tentativa in range(1, RETRY + 1):
        try:
            r = requests.get(url, timeout=90, verify=False)
            if r.status_code == 200:
                rows = r.json().get("value", [])
                if len(rows) == MAX_TOP:
                    print(f"    AVISO: {endpoint} retornou {MAX_TOP} (limite atingido)")
                return rows
            print(f"    HTTP {r.status_code} (tentativa {tentativa}/{RETRY})")
        except Exception as e:
            print(f"    Erro: {e} (tentativa {tentativa}/{RETRY})")
        if tentativa < RETRY:
            time.sleep(SLEEP_RETRY)
    return []


def coletar_custeio() -> pd.DataFrame:
    filtro_base = "codIbge ge '2100000' and codIbge le '2199999'"
    registros = []
    total = 0
    for ano in range(ANO_INICIO, ANO_FIM + 1):
        for mes in MESES:
            filtro = f"{filtro_base} and AnoEmissao eq '{ano}' and MesEmissao eq '{mes}'"
            rows = fetch("CusteioMunicipioProduto", filtro)
            registros.extend(rows)
            total += len(rows)
            sys.stdout.write(f"\r  Custeio {ano}/{mes}: {len(rows):>4} | total acum: {total:>7}")
            sys.stdout.flush()
    print()
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    cols = [c for c in CAMPOS_CUSTEIO if c in df.columns]
    df = df[cols].copy()
    df.rename(columns={
        "codIbge": "cod_ibge",
        "Municipio": "municipio",
        "nomeProduto": "produto",
        "AnoEmissao": "ano",
        "MesEmissao": "mes",
        "cdPrograma": "cd_programa",
        "cdFonteRecurso": "cd_fonte",
        "VlCusteio": "vl_custeio",
        "AreaCusteio": "area_custeio",
    }, inplace=True)
    df["produto"] = df["produto"].str.strip('"')
    df["municipio"] = df["municipio"].str.title()
    return df


def coletar_investimento() -> pd.DataFrame:
    registros = []
    total = 0
    for ano in range(ANO_INICIO, ANO_FIM + 1):
        for mes in MESES:
            filtro = f"cdEstado eq '11' and AnoEmissao eq '{ano}' and MesEmissao eq '{mes}'"
            rows = fetch("InvestMunicipioProduto", filtro)
            registros.extend(rows)
            total += len(rows)
            sys.stdout.write(f"\r  Invest  {ano}/{mes}: {len(rows):>4} | total acum: {total:>7}")
            sys.stdout.flush()
    print()
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    cols = [c for c in CAMPOS_INVEST if c in df.columns]
    df = df[cols].copy()
    df.rename(columns={
        "cdMunicipio": "cd_municipio_bcb",
        "Municipio": "municipio",
        "nomeProduto": "produto",
        "AnoEmissao": "ano",
        "MesEmissao": "mes",
        "cdPrograma": "cd_programa",
        "cdFonteRecurso": "cd_fonte",
        "VlInvest": "vl_invest",
        "AreaInvest": "area_invest",
        "cdEstado": "cd_estado_bcb",
    }, inplace=True)
    df["produto"] = df["produto"].str.strip('"')
    df["municipio"] = df["municipio"].str.title()
    return df


def agregar(df: pd.DataFrame, col_valor: str, col_area: str) -> pd.DataFrame:
    grupo = ["municipio", "produto", "ano"]
    if "cod_ibge" in df.columns:
        grupo = ["cod_ibge"] + grupo
    agg = {col_valor: "sum"}
    if col_area in df.columns:
        agg[col_area] = "sum"
    agg["mes"] = "count"  # qtd operações
    df_agg = df.groupby(grupo, as_index=False).agg(agg)
    df_agg.rename(columns={"mes": "qtd_operacoes"}, inplace=True)
    return df_agg.sort_values(grupo)


if __name__ == "__main__":
    import sys
    # Forçar UTF-8 no stdout (evita erro em terminais Windows cp1252)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"=== SICOR - Credito Rural Maranhao ({ANO_INICIO}-{ANO_FIM}) ===")

    raw_custeio = OUT_DIR / "custeio_ma_raw.csv"
    raw_invest  = OUT_DIR / "invest_ma_raw.csv"

    # --- Custeio ---
    if raw_custeio.exists():
        print(f"\n[1/4] custeio_ma_raw.csv ja existe ({raw_custeio.stat().st_size // 1024} KB) — pulando coleta.")
        df_custeio = pd.read_csv(raw_custeio, dtype={"cod_ibge": str})
    else:
        print("\n[1/4] Coletando custeio...")
        df_custeio = coletar_custeio()
        if not df_custeio.empty:
            df_custeio.to_csv(raw_custeio, index=False, encoding="utf-8")
            print(f"  Raw: {len(df_custeio):,} registros -> {raw_custeio.name}")
        else:
            print("  Nenhum dado de custeio retornado.")

    if not df_custeio.empty:
        print("[2/4] Agregando custeio por municipio/produto/ano...")
        df_custeio_agg = agregar(df_custeio, "vl_custeio", "area_custeio")
        out_c = OUT_DIR / "custeio_ma.csv"
        df_custeio_agg.to_csv(out_c, index=False, encoding="utf-8")
        print(f"  Agregado: {len(df_custeio_agg):,} linhas -> {out_c.name}")

    # --- Investimento ---
    if raw_invest.exists():
        print(f"\n[3/4] invest_ma_raw.csv ja existe ({raw_invest.stat().st_size // 1024} KB) — pulando coleta.")
        df_invest = pd.read_csv(raw_invest)
    else:
        print("\n[3/4] Coletando investimento...")
        df_invest = coletar_investimento()
        if not df_invest.empty:
            df_invest.to_csv(raw_invest, index=False, encoding="utf-8")
            print(f"  Raw: {len(df_invest):,} registros -> {raw_invest.name}")
        else:
            print("  Nenhum dado de investimento retornado.")

    if not df_invest.empty:
        print("[4/4] Agregando investimento por municipio/produto/ano...")
        df_invest_agg = agregar(df_invest, "vl_invest", "area_invest")
        out_i = OUT_DIR / "invest_ma.csv"
        df_invest_agg.to_csv(out_i, index=False, encoding="utf-8")
        print(f"  Agregado: {len(df_invest_agg):,} linhas -> {out_i.name}")

    print("\nConcluido.")
