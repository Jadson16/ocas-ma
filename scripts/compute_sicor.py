"""
Integra dados SICOR (crédito rural BCB) ao indicadores.json do OCAS-MA.

Lê:
  data/sicor/custeio_ma_raw.csv   — operações individuais (tem cd_programa)
  data/sicor/invest_ma_raw.csv    — operações individuais (tem cd_programa)
  data/indicadores.json           — indicadores existentes (produção)

Escreve de volta em data/indicadores.json, adicionando a chave "credito":

  credito:
    vcr          → Volume de Crédito (custeio + investimento, R$) por mun/cadeia/ano
    ql_cred      → QL calculado sobre VCR  (mesma fórmula do QL de produção)
    pr_cred      → Participação Relativa do município no crédito estadual da cadeia (%)
    tcg_cred     → Taxa de Crescimento Geométrico do crédito (janela TCG_JANELA anos)
    pronaf_share → % do crédito Pronaf no crédito total da cadeia/município/ano
    icr          → Intensidade de Crédito = VCR / valor_produção  (adimensional)

Indicador ICR só é gerado para cadeias que existem tanto no SICOR quanto nos dados
de produção (PEVS/PAM/PPM), respeitando o mesmo municipio_id.

PRONAF: cdPrograma == '0001'

Lógica de mapeamento produto SICOR → chave de cadeia OCAS:
  1. Normaliza: upper, strip, remove aspas e acentos irrelevantes
  2. Verifica se alguma KEYWORD da cadeia está contida no nome do produto SICOR
  3. Caso ambíguo (ex: BOVINOS matcheia "bovino" mas não "bubalino") → cadeia mais específica ganha
"""

import json
import logging
import math
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SICOR_DIR = DATA_DIR / "sicor"
IND_FILE = DATA_DIR / "indicadores.json"

TCG_JANELA = 10   # igual ao compute_indicators.py
CD_PRONAF  = "0001"

# ---------------------------------------------------------------------------
# Mapeamento: keywords que identificam cada cadeia nos nomes de produto SICOR
# Ordem importa quando há ambiguidade: keywords mais longas/específicas primeiro
# ---------------------------------------------------------------------------
CADEIA_KEYWORDS: dict[str, list[str]] = {
    # PEVS
    "babacu":         ["BABACU", "BABASSU", "BABASU"],
    "acai":           ["ACAI"],        # cobre extrativista e cultivado
    "buriti":         ["BURITI"],
    "carnauba":       ["CARNAUBA"],
    "piacava":        ["PIACAVA", "PIASSAVA"],
    # PAM temp
    "soja":           ["SOJA"],
    "milho":          ["MILHO"],
    "arroz":          ["ARROZ"],
    "feijao":         ["FEIJAO", "FEIJÃO"],
    "mandioca":       ["MANDIOCA", "AIPIM", "MACAXEIRA"],
    "cana":           ["CANA-DE-ACUCAR", "CANA DE ACUCAR", "CANA"],
    "algodao":        ["ALGODAO", "ALGODÃO"],
    "amendoim":       ["AMENDOIM"],
    "melancia":       ["MELANCIA"],
    # PAM perm
    "banana":         ["BANANA"],
    "castanha_caju":  ["CASTANHA DE CAJU", "CAJU"],
    "coco":           ["COCO"],
    "laranja":        ["LARANJA"],
    "mamao":          ["MAMAO", "MAMÃO"],
    "manga":          ["MANGA"],
    "maracuja":       ["MARACUJA", "MARACUJÁ"],
    "borracha":       ["BORRACHA", "LATEX", "LÁTEX"],
    # PPM
    "mel":            ["MEL DE ABELHA", "MEL"],
    "leite":          ["LEITE"],
    "ovos":           ["OVOS"],
    # PPM rebanhos (sem valor monetário direto, mas têm crédito)
    "bovino":         ["BOVINOS", "BOVINO", "PASTAGEM", "CAPINEIRA"],
    "bubalino":       ["BUBALINO", "BUFALO", "BÚFALO"],
    "suino":          ["SUINOS", "SUÍNO", "SUINO"],
    "caprino":        ["CAPRINOS", "CAPRINO"],
    "ovino":          ["OVINOS", "OVINO"],
    "galinaceo":      ["GALINHA", "GALINACEO", "FRANGO", "AVES"],
}


def _norm(s: str) -> str:
    """Normaliza string: maiúsculo, sem acentos, sem aspas."""
    s = s.upper().strip().strip('"')
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _map_produto(nome_raw: str, _cache: dict = {}) -> str | None:
    """Retorna chave de cadeia OCAS ou None se não mapeado."""
    nome = _norm(nome_raw)
    if nome in _cache:
        return _cache[nome]
    match = None
    for cadeia, keywords in CADEIA_KEYWORDS.items():
        for kw in keywords:
            if kw in nome:
                match = cadeia
                break
        if match:
            break
    _cache[nome] = match
    return match


def _safe(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------

def load_sicor() -> pd.DataFrame:
    """
    Carrega custeio_raw + invest_raw, mapeia produtos → cadeias, retorna:
      cod_ibge | municipio | cadeia | ano | vl_credito | is_pronaf
    """
    frames = []

    # Monta lookup nome_normalizado → cod_ibge a partir do custeio (que tem codIbge)
    ibge_lookup: dict[str, str] = {}
    custeio_path = SICOR_DIR / "custeio_ma_raw.csv"
    if custeio_path.exists():
        df_lookup = pd.read_csv(custeio_path, dtype={"cod_ibge": str},
                                usecols=["cod_ibge", "municipio"])
        df_lookup["_chave"] = df_lookup["municipio"].str.upper().str.strip()
        ibge_lookup = df_lookup.drop_duplicates("_chave").set_index("_chave")["cod_ibge"].to_dict()
        log.info("  Lookup IBGE: %d municipios carregados do custeio", len(ibge_lookup))

    for fname, col_val in [
        ("custeio_ma_raw.csv", "vl_custeio"),
        ("invest_ma_raw.csv",  "vl_invest"),
    ]:
        path = SICOR_DIR / fname
        if not path.exists():
            log.warning("Arquivo nao encontrado: %s — ignorado", fname)
            continue
        df = pd.read_csv(path, dtype={"cod_ibge": str, "cd_programa": str})
        df = df.rename(columns={col_val: "vl_credito"})
        df["is_pronaf"] = df["cd_programa"] == CD_PRONAF
        # Garante cod_ibge de 7 dígitos (custeio já tem; investimento precisa de lookup)
        if "cod_ibge" in df.columns:
            df["cod_ibge"] = df["cod_ibge"].str.zfill(7)
        elif ibge_lookup and "municipio" in df.columns:
            df["_chave"] = df["municipio"].str.upper().str.strip()
            df["cod_ibge"] = df["_chave"].map(ibge_lookup)
            n_ok  = df["cod_ibge"].notna().sum()
            n_tot = len(df)
            log.info("  %s: cod_ibge recuperado por nome para %d/%d linhas (%.1f%%)",
                     fname, n_ok, n_tot, 100 * n_ok / n_tot if n_tot else 0)
            df = df.drop(columns=["_chave"])
        else:
            log.warning("%s sem cod_ibge e sem lookup disponivel", fname)
        cols_keep = [c for c in ["cod_ibge", "municipio", "produto", "ano", "vl_credito", "is_pronaf"]
                     if c in df.columns]
        frames.append(df[cols_keep])
        log.info("  %s: %d linhas", fname, len(df))

    if not frames:
        raise FileNotFoundError("Nenhum arquivo SICOR raw encontrado em data/sicor/")

    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all[df_all["vl_credito"].notna() & (df_all["vl_credito"] > 0)]

    # Mapeamento produto → cadeia
    df_all["cadeia"] = df_all["produto"].map(_map_produto)
    n_nan = df_all["cadeia"].isna().sum()
    total = len(df_all)
    log.info("  Mapeamento: %d/%d produtos reconhecidos (%.1f%%)",
             total - n_nan, total, 100 * (total - n_nan) / total)

    # Produtos não mapeados (top 10 por volume)
    nao_mapeados = (
        df_all[df_all["cadeia"].isna()]
        .groupby("produto")["vl_credito"].sum()
        .nlargest(10)
    )
    if not nao_mapeados.empty:
        log.info("  Top produtos NAO mapeados (R$ total):")
        for prod, val in nao_mapeados.items():
            log.info("    %-50s R$ %s", prod, f"{val:,.0f}")

    df_all = df_all[df_all["cadeia"].notna()].copy()
    df_all["ano"] = df_all["ano"].astype(int)
    return df_all


# ---------------------------------------------------------------------------
# Agregações base
# ---------------------------------------------------------------------------

def agg_vcr(df: pd.DataFrame) -> pd.DataFrame:
    """VCR total por cod_ibge × cadeia × ano."""
    return (
        df.groupby(["cod_ibge", "municipio", "cadeia", "ano"], as_index=False)
        ["vl_credito"].sum()
        .rename(columns={"vl_credito": "vcr"})
    )


def agg_pronaf(df: pd.DataFrame) -> pd.DataFrame:
    """Share Pronaf: VCR_pronaf / VCR_total por cod_ibge × cadeia × ano."""
    total = (
        df.groupby(["cod_ibge", "cadeia", "ano"])["vl_credito"]
        .sum()
        .rename("vcr_total")
    )
    pronaf = (
        df[df["is_pronaf"]]
        .groupby(["cod_ibge", "cadeia", "ano"])["vl_credito"]
        .sum()
        .rename("vcr_pronaf")
    )
    merged = total.to_frame().join(pronaf, how="left").fillna(0)
    merged["pronaf_share"] = _safe_div(merged["vcr_pronaf"], merged["vcr_total"])
    return merged.reset_index()


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    result = a / b
    result[b == 0] = None
    return result


# ---------------------------------------------------------------------------
# Indicadores derivados (mesma lógica do compute_indicators.py)
# ---------------------------------------------------------------------------

def compute_ql_cred(df_vcr: pd.DataFrame, anos: list[int]) -> dict:
    """QL baseado em VCR: (vcr_ij/vcr_i) / (vcr_j/vcr_total)."""
    pivot_total = df_vcr.groupby(["cod_ibge", "ano"])["vcr"].sum()
    result: dict = {}
    for cadeia, grp in df_vcr.groupby("cadeia"):
        result[cadeia] = {}
        for ano in anos:
            sub = grp[grp["ano"] == ano]
            if sub.empty:
                continue
            v_j = sub["vcr"].sum()
            try:
                v_total = pivot_total.xs(ano, level="ano").sum()
            except KeyError:
                continue
            if v_j == 0 or v_total == 0:
                continue
            share_j = v_j / v_total
            row = {}
            for _, r in sub.iterrows():
                mid = r["cod_ibge"]
                v_i = pivot_total.get((mid, ano), 0)
                if v_i == 0:
                    continue
                ql = (r["vcr"] / v_i) / share_j
                v = _safe(ql)
                if v is not None:
                    row[mid] = v
            if row:
                result[cadeia][str(ano)] = row
    return result


def compute_pr_cred(df_vcr: pd.DataFrame, anos: list[int]) -> dict:
    """PR baseado em VCR: vcr_ij / vcr_j × 100."""
    result: dict = {}
    for cadeia, grp in df_vcr.groupby("cadeia"):
        result[cadeia] = {}
        for ano in anos:
            sub = grp[grp["ano"] == ano]
            v_j = sub["vcr"].sum()
            if v_j == 0:
                continue
            row = {r["cod_ibge"]: _safe(r["vcr"] / v_j * 100) for _, r in sub.iterrows()}
            row = {k: v for k, v in row.items() if v is not None}
            if row:
                result[cadeia][str(ano)] = row
    return result


def compute_tcg_cred(df_vcr: pd.DataFrame, anos: list[int], janela: int = TCG_JANELA) -> dict:
    """TCG baseado em VCR."""
    result: dict = {}
    for cadeia, grp in df_vcr.groupby("cadeia"):
        pivot = grp.pivot_table(index="cod_ibge", columns="ano", values="vcr", aggfunc="sum")
        result[cadeia] = {}
        for ano in anos:
            ano0 = ano - janela
            if ano0 not in pivot.columns or ano not in pivot.columns:
                continue
            row = {}
            for mid in pivot.index:
                v_t  = pivot.at[mid, ano]
                v_t0 = pivot.at[mid, ano0]
                if pd.isna(v_t) or pd.isna(v_t0) or v_t0 == 0:
                    continue
                tcg = (v_t / v_t0) ** (1 / janela) - 1
                v = _safe(tcg)
                if v is not None:
                    row[mid] = v
            if row:
                result[cadeia][str(ano)] = row
    return result


def compute_pronaf_out(df_pronaf: pd.DataFrame, anos: list[int]) -> dict:
    """Serializa pronaf_share para JSON por cadeia → ano → municipio."""
    result: dict = {}
    for cadeia, grp in df_pronaf.groupby("cadeia"):
        result[cadeia] = {}
        for ano in anos:
            sub = grp[grp["ano"] == ano]
            if sub.empty:
                continue
            row = {r["cod_ibge"]: _safe(r["pronaf_share"]) for _, r in sub.iterrows()
                   if _safe(r["pronaf_share"]) is not None}
            if row:
                result[cadeia][str(ano)] = row
    return result


def compute_icr(df_vcr: pd.DataFrame, ind_existente: dict, anos: list[int]) -> dict:
    """
    ICR = VCR / valor_producao.

    Valor de produção vem de ind_existente["indicadores"]["pr"] não serve — precisamos
    das séries de valor absoluto. Como compute_indicators não salva valor absoluto no JSON,
    o ICR é calculado a partir dos CSVs de produção diretamente.

    Se os CSVs não estiverem disponíveis, retorna {} (indicador opcional).
    """
    from compute_indicators import PRODUCTS_COM_VALOR  # importa catálogo local

    result: dict = {}
    for cadeia, grp_vcr in df_vcr.groupby("cadeia"):
        if cadeia not in PRODUCTS_COM_VALOR:
            continue
        csv_rel, _, _ = PRODUCTS_COM_VALOR[cadeia]
        csv_path = DATA_DIR / csv_rel
        if not csv_path.exists():
            continue
        df_prod = pd.read_csv(csv_path, dtype={"municipio_id": str})
        if "valor_mil_reais" not in df_prod.columns:
            continue
        df_prod = df_prod[df_prod["valor_mil_reais"].notna() & (df_prod["valor_mil_reais"] > 0)]

        result[cadeia] = {}
        for ano in anos:
            vcr_ano = grp_vcr[grp_vcr["ano"] == ano].set_index("cod_ibge")["vcr"]
            prod_ano = (
                df_prod[df_prod["ano"] == ano]
                .groupby("municipio_id")["valor_mil_reais"]
                .sum()
                * 1000  # converte mil_reais → reais para comparar com R$ crédito
            )
            comuns = vcr_ano.index.intersection(prod_ano.index)
            if comuns.empty:
                continue
            row = {}
            for mid in comuns:
                v_prod = prod_ano[mid]
                v_cred = vcr_ano[mid]
                if v_prod > 0:
                    icr = _safe(v_cred / v_prod)
                    if icr is not None:
                        row[mid] = icr
            if row:
                result[cadeia][str(ano)] = row
    return result


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_sicor — início ===")

    # 1. Carregar dados SICOR
    log.info("[1/6] Carregando dados SICOR...")
    df = load_sicor()
    log.info("  %d operações após mapeamento", len(df))

    anos = sorted(df["ano"].unique().tolist())
    log.info("  Anos: %s a %s", anos[0], anos[-1])

    # 2. Agregar VCR e Pronaf
    log.info("[2/6] Agregando VCR e Pronaf share...")
    df_vcr    = agg_vcr(df)
    df_pronaf = agg_pronaf(df)

    # 3. Calcular indicadores de crédito
    log.info("[3/6] Calculando QL, PR, TCG (crédito)...")
    ql_cred     = compute_ql_cred(df_vcr, anos)
    pr_cred     = compute_pr_cred(df_vcr, anos)
    tcg_cred    = compute_tcg_cred(df_vcr, anos)
    pronaf_out  = compute_pronaf_out(df_pronaf, anos)

    # 4. ICR (intensidade crédito/produção)
    log.info("[4/6] Calculando ICR (intensidade crédito/produção)...")
    ind_existente = json.loads(IND_FILE.read_text(encoding="utf-8")) if IND_FILE.exists() else {}
    icr = compute_icr(df_vcr, ind_existente, anos)
    log.info("  ICR calculado para %d cadeias", len(icr))

    # 5. VCR absoluto (volume bruto para frontend)
    log.info("[5/6] Serializando VCR absoluto...")
    vcr_out: dict = {}
    for cadeia, grp in df_vcr.groupby("cadeia"):
        vcr_out[cadeia] = {}
        for ano in anos:
            sub = grp[grp["ano"] == ano]
            if sub.empty:
                continue
            row = {r["cod_ibge"]: _safe(r["vcr"]) for _, r in sub.iterrows()
                   if _safe(r["vcr"]) is not None}
            if row:
                vcr_out[cadeia][str(ano)] = row

    # 6. Merge no indicadores.json
    log.info("[6/6] Salvando em indicadores.json...")
    ind_existente["credito"] = {
        "meta": {
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "anos_disponiveis": anos,
            "tcg_janela_anos": TCG_JANELA,
            "cd_pronaf": CD_PRONAF,
            "n_cadeias": len(vcr_out),
            "descricao": {
                "vcr":          "Volume de Crédito Rural (custeio + investimento) em R$",
                "ql_cred":      "Quociente Locacional do crédito (QL baseado em VCR)",
                "pr_cred":      "Participação Relativa do município no crédito estadual da cadeia (%)",
                "tcg_cred":     "Taxa de Crescimento Geométrico do crédito (janela 10 anos)",
                "pronaf_share": "Participação do crédito Pronaf no crédito total (0–1)",
                "icr":          "Intensidade de Crédito = VCR / Valor_Produção (adimensional)",
            },
        },
        "vcr":          vcr_out,
        "ql_cred":      ql_cred,
        "pr_cred":      pr_cred,
        "tcg_cred":     tcg_cred,
        "pronaf_share": pronaf_out,
        "icr":          icr,
    }

    IND_FILE.write_text(
        json.dumps(ind_existente, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    log.info("=== Salvo em %s (%.0f KB) ===", IND_FILE, IND_FILE.stat().st_size / 1024)


if __name__ == "__main__":
    main()
