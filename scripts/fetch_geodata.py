"""
Baixa arquivos geográficos estáticos do Maranhão:
  - municipios_ma.geojson  : polígonos municipais (geodata-br)
  - maranhao_estado.geojson: fronteira do estado (IBGE malhas)
Execute uma vez e commite os resultados.
"""

import json
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

MUN_URL = (
    "https://raw.githubusercontent.com/tbrugz/geodata-br/"
    "master/geojson/geojs-21-mun.json"
)
ESTADO_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/21"
    "?formato=application/vnd.geo+json&resolucao=5"
)


def fetch_municipios():
    print("Baixando GeoJSON de municípios do MA...")
    r = requests.get(MUN_URL, timeout=60)
    r.raise_for_status()
    geojson = r.json()
    out = DATA_DIR / "municipios_ma.geojson"  # compartilhado entre todas as cadeias
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"  {len(geojson['features'])} municípios -> {out}")


def fetch_estado():
    print("Baixando fronteira do estado do MA...")
    r = requests.get(ESTADO_URL, timeout=60)
    r.raise_for_status()
    geojson = r.json()
    out = DATA_DIR / "maranhao_estado.geojson"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"  {len(geojson['features'])} feature(s) -> {out}")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    fetch_municipios()
    fetch_estado()
    print("Concluído.")


if __name__ == "__main__":
    main()
