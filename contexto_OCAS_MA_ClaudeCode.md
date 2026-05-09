# Contexto do Projeto — OCAS-MA
## Para uso no Claude Code

---

## Identidade do Observatório

**Nome completo:** Observatório de Cadeias, Arranjos e Sustentabilidade do Maranhão  
**Sigla:** OCAS-MA  
**Vínculo institucional:** GEIA — CECON — UFMA  
**Coordenador:** Prof. Dr. Jadson Pessoa da Silva  

---

## Escopo

**Objeto:** cadeias produtivas e arranjos produtivos locais (APLs) com expressão territorial no Maranhão — qualquer setor, sem restrição prévia.

**Unidade de análise:** município.

**Cobertura geográfica:** Maranhão inteiro — Amazônia Legal maranhense, Pré-Amazônia e Cerrado maranhense.

**Horizonte temporal:** máximo permitido pelas fontes de dados disponíveis.

**Incorporação de cadeias:** progressiva, condicionada à disponibilidade de dados por município.

**Atributos transversais de análise:** dimensões socioambiental, de trabalho e de crédito — monitoradas dentro de cada cadeia, não como eixos autônomos.

---

## Produtos

### Produto 1 — Painel Geoespacial (PRIORIDADE)

- **Linguagem:** Python
- **Hospedagem:** GitHub Pages
- **Atualização:** automática via API — GitHub Actions
- **Fontes de dados (fase inicial):** SIDRA/IBGE (PEVS — Produção da Extração Vegetal e da Silvicultura)
- **Cadeia de entrada:** babaçu
- **Variáveis iniciais (babaçu via SIDRA/PEVS):**
  - Quantidade produzida por município
  - Valor da produção por município
- **Expansão futura de fontes:** CONAB/PGPM-Bio, MapBiomas, RAIS/CAGED, BCB/SCR, Censo Agropecuário
- **Expansão futura de cadeias:** açaí, pesca artesanal, soja, pecuária bovina, piscicultura, turismo, meliponicultura, avicultura, leite e derivados, mandiocultura, caju, ovinocaprinocultura, cachaça, hortifruticultura, economia criativa — conforme disponibilidade de dados municipais

### Produto 2 — Boletim Semestral

- Nota técnica com densidade analítica
- Periodicidade semestral (mínimo)
- Com ISSN
- Estrutura narrativa em texto corrido com tabelas e mapas integrados
- Análise narrativa dos dados do painel geoespacial
- Público múltiplo: pesquisadores, gestores públicos, parceiros institucionais, sociedade civil

---

## Arquitetura técnica do painel (a ser desenvolvida no Claude Code)

- **Coleta de dados:** API SIDRA/IBGE — tabela PEVS, variáveis de quantidade e valor da produção extrativa, filtradas por município do Maranhão
- **Tratamento:** Python (Pandas, GeoPandas)
- **Visualização geoespacial:** Folium ou Plotly
- **Automação:** GitHub Actions para atualização periódica
- **Hospedagem:** GitHub Pages

---

## Repositório GitHub

**URL:** https://github.com/Jadson16/ocas-ma  
**GitHub Pages:** https://jadson16.github.io/ocas-ma  
**Branch principal:** main  

---

## Tarefa imediata no Claude Code

Construir o painel geoespacial do OCAS-MA, começando pela cadeia do babaçu, com dados da API SIDRA/IBGE (PEVS), unidade de análise municipal, cobertura do estado do Maranhão, visualização geoespacial interativa em Python, hospedagem no GitHub Pages e atualização automática via GitHub Actions.

Começar pela coleta e tratamento dos dados via API SIDRA antes de partir para a visualização.
