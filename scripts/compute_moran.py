"""
Calcula indicadores de autocorrelação espacial (Moran I Global + LISA)
para as cadeias produtivas do Maranhão.

Entrada : data/indicadores.json  (seção indicadores.ql)
Geometry: data/municipios_ma.geojson (id = cod_ibge 7 dígitos)

Saída   : data/espacial.json
  {
    meta: { ... },
    moran: { cadeia: { ano: { I, z, p, n } } },
    lisa:  { cadeia: { ano: { cod_ibge: { q, p, z, lz } } } }
  }

  q  = quadrante LISA: "HH"|"HL"|"LH"|"LL" (todos 217 muns)
  p  = p-valor via permutação (999)
  z  = QL padronizado (z-score municipal)
  lz = defasagem espacial de z (para diagrama de Moran)

APL candidato: q == "HH" and p < 0.05

Uso:
  cd scripts
  python compute_moran.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import libpysal
import numpy as np
from esda import Moran, Moran_Local
from libpysal.weights import lag_spatial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent
DATA_DIR  = ROOT / "data"
GEO_FILE  = DATA_DIR / "municipios_ma.geojson"
IND_FILE  = DATA_DIR / "indicadores.json"
OUT_FILE  = DATA_DIR / "espacial.json"

PERMUTATIONS = 999
P_THRESH     = 0.05
MIN_NONZERO  = 20   # mínimo de municípios com dados para calcular Moran
SEED         = 42

QUAD_LABELS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}


# ---------------------------------------------------------------------------
# Geometria e matriz de pesos
# ---------------------------------------------------------------------------

def build_weights(geo_file: Path) -> tuple[list[str], libpysal.weights.W]:
    """
    Lê o GeoJSON, constrói pesos Queen contiguidade (row-standardized).
    Retorna (lista ordenada de IDs, objeto W).
    """
    log.info("Carregando geometria: %s", geo_file)
    gdf = gpd.read_file(geo_file)
    gdf = gdf.set_index("id")                   # cod_ibge como índice
    gdf = gdf.sort_index()                       # ordem estável

    log.info("  %d municípios no GeoJSON", len(gdf))

    w = libpysal.weights.Queen.from_dataframe(gdf, use_index=True)
    w.transform = "r"                            # row-standardize

    mids = list(gdf.index)                       # ordem alinhada com W
    log.info("  W: %d nós, %.2f vizinhos médios", w.n, w.mean_neighbors)
    return mids, w


# ---------------------------------------------------------------------------
# Cálculo por cadeia × ano
# ---------------------------------------------------------------------------

def _safe_float(v) -> float | None:
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def compute_spatial(ql_data: dict, mids: list[str], w: libpysal.weights.W,
                    anos: list[int]) -> tuple[dict, dict]:
    """
    Para cada cadeia e ano, calcula Moran I Global e LISA.
    Retorna (moran_dict, lisa_dict).
    """
    moran_out: dict = {}
    lisa_out:  dict = {}
    cadeias = list(ql_data.keys())
    n_total  = len(cadeias) * len(anos)
    feito    = 0

    for cadeia in cadeias:
        moran_out[cadeia] = {}
        lisa_out[cadeia]  = {}

        for ano in anos:
            anoS = str(ano)
            ql_ano = ql_data.get(cadeia, {}).get(anoS, {})

            # Vetor y completo (217 posições), zeros onde sem dados
            y = np.array([float(ql_ano.get(mid, 0.0)) for mid in mids],
                         dtype=float)
            n_nonzero = int(np.count_nonzero(y))

            feito += 1
            sys.stdout.write(
                f"\r  [{feito}/{n_total}] {cadeia}/{anoS}: {n_nonzero} muns  "
            )
            sys.stdout.flush()

            if n_nonzero < MIN_NONZERO:
                continue

            try:
                # ── Global Moran I ──────────────────────────────────────────
                np.random.seed(SEED)
                mi = Moran(y, w, permutations=PERMUTATIONS)
                moran_out[cadeia][anoS] = {
                    "I": _safe_float(mi.I),
                    "z": _safe_float(mi.z_sim),
                    "p": _safe_float(mi.p_sim),
                    "n": n_nonzero,
                }

                # ── LISA ────────────────────────────────────────────────────
                np.random.seed(SEED)
                lisa = Moran_Local(y, w, permutations=PERMUTATIONS)

                # Padronização para diagrama de Moran (média/std sobre y > 0
                # é mais informativa que sobre todos, mas usamos todos os 217
                # para respeitar a estrutura espacial)
                y_mean = float(y.mean())
                y_std  = float(y.std())
                if y_std == 0:
                    continue

                z_vec  = (y - y_mean) / y_std        # z-score QL
                lz_vec = lag_spatial(w, z_vec)        # defasagem espacial de z

                row: dict = {}
                for i, mid in enumerate(mids):
                    q = int(lisa.q[i])
                    p = float(lisa.p_sim[i])
                    row[mid] = {
                        "q":  QUAD_LABELS.get(q, "NA"),
                        "p":  round(p, 4),
                        "z":  round(float(z_vec[i]),  4),
                        "lz": round(float(lz_vec[i]), 4),
                    }

                lisa_out[cadeia][anoS] = row

            except Exception as exc:
                log.warning("\n  ERRO %s/%s: %s", cadeia, anoS, exc)

    print()  # newline após progress
    return moran_out, lisa_out


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== compute_moran — início ===")

    # 1. Geometria + pesos
    mids, w = build_weights(GEO_FILE)

    # 2. Carregar QL
    log.info("Carregando indicadores.json...")
    ind = json.loads(IND_FILE.read_text(encoding="utf-8"))
    ql_data = ind["indicadores"]["ql"]
    anos    = list(ind["meta"]["anos_disponiveis"])
    log.info("  %d cadeias × %d anos", len(ql_data), len(anos))

    # 3. Calcular
    log.info("Calculando Moran I Global + LISA (permutações=%d)...", PERMUTATIONS)
    moran_out, lisa_out = compute_spatial(ql_data, mids, w, anos)

    # 4. Contar resultados
    n_moran = sum(len(v) for v in moran_out.values())
    n_lisa  = sum(len(v) for v in lisa_out.values())
    log.info("  Moran global: %d registros", n_moran)
    log.info("  LISA:         %d registros (cadeia × ano)", n_lisa)

    # Contar municípios HH significativos (APL candidatos) em 2023
    n_hh_sig = 0
    for cadeia in lisa_out:
        lisa_2023 = lisa_out[cadeia].get("2023", {})
        n_hh_sig += sum(
            1 for v in lisa_2023.values()
            if v["q"] == "HH" and v["p"] < P_THRESH
        )
    log.info("  APL candidatos (HH sig, 2023, todos cadeias): %d mun×cadeia", n_hh_sig)

    # 5. Salvar
    out = {
        "meta": {
            "gerado_em":       datetime.now().strftime("%Y-%m-%d %H:%M"),
            "metodo":          "Queen contiguity, row-standardized, permutações=999",
            "variavel":        "QL (Quociente Locacional da produção)",
            "p_threshold":     P_THRESH,
            "min_muns":        MIN_NONZERO,
            "n_muns_total":    len(mids),
            "quad_labels":     {"HH": "alto-alto", "LH": "baixo-alto",
                                "LL": "baixo-baixo", "HL": "alto-baixo"},
            "campos_lisa":     {"q": "quadrante", "p": "p-valor",
                                "z": "QL padronizado", "lz": "defasagem espacial de z"},
        },
        "moran":   moran_out,
        "lisa":    lisa_out,
    }

    OUT_FILE.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = OUT_FILE.stat().st_size // 1024
    log.info("=== Salvo em %s (%d KB) ===", OUT_FILE, size_kb)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
