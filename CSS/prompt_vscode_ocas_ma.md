# Prompt — Implementação da Identidade Visual OCAS-MA
## Para uso no chat do VS Code (GitHub Copilot / Cursor / Claude Dev)

---

Implemente a identidade visual oficial do **OCAS-MA — Observatório de Cadeias, Arranjos e Sustentabilidade do Maranhão** no dashboard existente em `https://jadson16.github.io/ocas-ma/`. O projeto é vinculado ao **GEIA — CECON — UFMA**.

---

## 1. DESIGN SYSTEM — VARIÁVEIS CSS

Adicione ao arquivo CSS principal (ou `:root` do `index.html`) as seguintes variáveis:

```css
:root {
  /* === PALETA PRIMÁRIA === */
  --ocas-floresta:   #1B4332;   /* títulos principais */
  --ocas-mata:       #2D6A4F;   /* cor primária, stroke, links */
  --ocas-igapo:      #40916C;   /* labels, subtítulos */
  --ocas-babacu:     #52B788;   /* accent, hover states, símbolo central */
  --ocas-buriti:     #74C69D;   /* badges, tags, highlights */
  --ocas-varzea:     #D8F3DC;   /* backgrounds suaves, bg de cards */

  /* === BACKGROUNDS LIGHT === */
  --ocas-bg-page:    #F7FAF8;   /* fundo da página */
  --ocas-bg-header:  #ffffff;   /* fundo do header */
  --ocas-bg-card:    #ffffff;   /* fundo dos cards */
  --ocas-bg-nav:     #F7FAF8;   /* fundo da barra de navegação */

  /* === BORDAS === */
  --ocas-border:     #ddeee5;   /* borda padrão */
  --ocas-border-soft:#c8e0d0;   /* borda suave (separadores) */
  --ocas-divider:    #95D5B2;   /* linha decorativa */

  /* === CORES DE APOIO TEMÁTICO === */
  --ocas-cerrado:    #C9A84C;   /* eixo MATOPIBA / soja / agropecuária */
  --ocas-rio:        #2C6E8A;   /* eixo pesca / recursos hídricos */

  /* === TIPOGRAFIA === */
  --ocas-font-titulo:  Georgia, 'Times New Roman', serif;
  --ocas-font-label:   'Courier New', Courier, monospace;
  --ocas-font-dados:   system-ui, -apple-system, sans-serif;

  /* === ESPAÇAMENTO === */
  --ocas-radius-sm:  6px;
  --ocas-radius-md:  10px;
  --ocas-radius-lg:  12px;

  /* === SOMBRAS === */
  --ocas-shadow-card: 0 1px 3px rgba(27, 67, 50, 0.06);
}
```

---

## 2. SÍMBOLO SVG — LOGO (TRAMA DE CADEIAS)

Use este SVG como símbolo institucional. É um hexágono com nós interligados representando cadeias produtivas e APLs.

### Versão 64px — header (com linhas de conexão completas)
```html
<svg width="48" height="48" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="OCAS-MA">
  <polygon points="32,4 56,18 56,46 32,60 8,46 8,18"
    fill="none" stroke="#2D6A4F" stroke-width="2" stroke-linejoin="round"/>
  <circle cx="32" cy="4"  r="3.5" fill="#2D6A4F"/>
  <circle cx="56" cy="18" r="3.5" fill="#2D6A4F"/>
  <circle cx="56" cy="46" r="3.5" fill="#2D6A4F"/>
  <circle cx="32" cy="60" r="3.5" fill="#2D6A4F"/>
  <circle cx="8"  cy="46" r="3.5" fill="#2D6A4F"/>
  <circle cx="8"  cy="18" r="3.5" fill="#2D6A4F"/>
  <!-- nó central -->
  <circle cx="32" cy="32" r="6" fill="#52B788"/>
  <!-- linhas de conexão -->
  <line x1="32" y1="26" x2="32" y2="7"  stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
  <line x1="37" y1="29" x2="53" y2="21" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
  <line x1="37" y1="35" x2="53" y2="43" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
  <line x1="32" y1="38" x2="32" y2="57" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
  <line x1="27" y1="35" x2="11" y2="43" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
  <line x1="27" y1="29" x2="11" y2="21" stroke="#52B788" stroke-width="1.2" opacity="0.7"/>
</svg>
```

### Versão 32px — navegação / favicon (sem linhas, apenas nós)
```html
<svg width="32" height="32" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="OCAS-MA">
  <polygon points="32,4 56,18 56,46 32,60 8,46 8,18"
    fill="none" stroke="#2D6A4F" stroke-width="2.5" stroke-linejoin="round"/>
  <circle cx="32" cy="4"  r="4" fill="#2D6A4F"/>
  <circle cx="56" cy="18" r="4" fill="#2D6A4F"/>
  <circle cx="56" cy="46" r="4" fill="#2D6A4F"/>
  <circle cx="32" cy="60" r="4" fill="#2D6A4F"/>
  <circle cx="8"  cy="46" r="4" fill="#2D6A4F"/>
  <circle cx="8"  cy="18" r="4" fill="#2D6A4F"/>
  <circle cx="32" cy="32" r="7" fill="#52B788"/>
</svg>
```

---

## 3. HEADER — ESTRUTURA HTML + CSS

```html
<header class="ocas-header">
  <div class="ocas-header-inner">

    <div class="ocas-brand">
      <!-- SVG 48px aqui -->
      <div class="ocas-brand-text">
        <span class="ocas-sigla">OCAS-MA</span>
        <span class="ocas-vinculo">GEIA · CECON · UFMA</span>
      </div>
    </div>

    <div class="ocas-header-meta">
      Atualização: mai. 2026
      <span class="ocas-status">● online</span>
    </div>

  </div>
</header>
```

```css
.ocas-header {
  background: var(--ocas-bg-header);
  border-bottom: 1px solid var(--ocas-border);
  padding: 18px 28px;
}

.ocas-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.ocas-brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.ocas-brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ocas-sigla {
  font-family: var(--ocas-font-titulo);
  font-size: 22px;
  font-weight: 700;
  color: var(--ocas-floresta);
  letter-spacing: 1px;
  line-height: 1;
}

.ocas-vinculo {
  font-family: var(--ocas-font-label);
  font-size: 9px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--ocas-igapo);
}

.ocas-header-meta {
  font-family: var(--ocas-font-label);
  font-size: 10px;
  color: var(--ocas-igapo);
  text-align: right;
  line-height: 1.8;
}

.ocas-status {
  color: var(--ocas-babacu);
  margin-left: 6px;
}
```

---

## 4. NAVEGAÇÃO — ESTRUTURA HTML + CSS

```html
<nav class="ocas-nav">
  <a href="#cadeias"       class="ocas-nav-item active">Cadeias</a>
  <a href="#arranjos"      class="ocas-nav-item">Arranjos / APLs</a>
  <a href="#sustentabilidade" class="ocas-nav-item">Sustentabilidade</a>
  <a href="#territorio"    class="ocas-nav-item">Território</a>
  <a href="#boletins"      class="ocas-nav-item">Boletins</a>
</nav>
```

```css
.ocas-nav {
  background: var(--ocas-bg-nav);
  border-bottom: 1px solid var(--ocas-border);
  display: flex;
  padding: 0 28px;
}

.ocas-nav-item {
  padding: 10px 16px;
  font-family: var(--ocas-font-label);
  font-size: 11px;
  letter-spacing: 0.5px;
  color: var(--ocas-buriti);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}

.ocas-nav-item:hover {
  color: var(--ocas-mata);
}

.ocas-nav-item.active {
  color: var(--ocas-mata);
  border-bottom-color: var(--ocas-mata);
}
```

---

## 5. STAT CARDS — ESTRUTURA HTML + CSS

Os cards de indicadores têm variação de cor na borda esquerda conforme o eixo temático.

```html
<div class="ocas-cards-grid">

  <div class="ocas-card">
    <div class="ocas-card-label">Municípios</div>
    <div class="ocas-card-value">217</div>
    <div class="ocas-card-desc">cobertura estadual</div>
  </div>

  <div class="ocas-card">
    <div class="ocas-card-label">Cadeias</div>
    <div class="ocas-card-value">12</div>
    <div class="ocas-card-desc">monitoradas</div>
  </div>

  <!-- Eixo Cerrado/MATOPIBA: usar --ocas-cerrado -->
  <div class="ocas-card ocas-card--cerrado">
    <div class="ocas-card-label">APLs</div>
    <div class="ocas-card-value">38</div>
    <div class="ocas-card-desc">arranjos mapeados</div>
  </div>

  <!-- Eixo pesca/hídrico: usar --ocas-rio -->
  <div class="ocas-card ocas-card--rio">
    <div class="ocas-card-label">Série histórica</div>
    <div class="ocas-card-value">2000–</div>
    <div class="ocas-card-desc">máximo disponível</div>
  </div>

</div>
```

```css
.ocas-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  padding: 20px 28px;
  background: var(--ocas-bg-page);
}

.ocas-card {
  background: var(--ocas-bg-card);
  border: 0.5px solid var(--ocas-border);
  border-radius: var(--ocas-radius-md);
  border-left: 2px solid var(--ocas-mata);
  padding: 16px 18px;
  box-shadow: var(--ocas-shadow-card);
}

.ocas-card--cerrado {
  border-left-color: var(--ocas-cerrado);
}

.ocas-card--rio {
  border-left-color: var(--ocas-rio);
}

.ocas-card-label {
  font-family: var(--ocas-font-label);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--ocas-igapo);
  margin-bottom: 6px;
}

.ocas-card--cerrado .ocas-card-label { color: var(--ocas-cerrado); }
.ocas-card--rio     .ocas-card-label { color: var(--ocas-rio); }

.ocas-card-value {
  font-family: var(--ocas-font-titulo);
  font-size: 26px;
  font-weight: 500;
  color: var(--ocas-floresta);
  line-height: 1.1;
}

.ocas-card-desc {
  font-family: var(--ocas-font-dados);
  font-size: 10px;
  color: var(--ocas-buriti);
  margin-top: 4px;
}
```

---

## 6. RODAPÉ INSTITUCIONAL

```html
<footer class="ocas-footer">
  OCAS-MA · Observatório de Cadeias, Arranjos e Sustentabilidade do Maranhão
  · GEIA — CECON — UFMA
</footer>
```

```css
.ocas-footer {
  padding: 12px 28px;
  font-family: var(--ocas-font-label);
  font-size: 9px;
  letter-spacing: 1px;
  color: var(--ocas-buriti);
  border-top: 0.5px solid var(--ocas-border);
  background: var(--ocas-bg-page);
  text-align: center;
}
```

---

## 7. REGRAS DE TIPOGRAFIA

| Elemento | Fonte | Tamanho | Cor |
|---|---|---|---|
| Sigla OCAS-MA | Georgia bold | 20–28px | `--ocas-floresta` |
| Nome completo | Georgia regular | 13–15px | `--ocas-mata` |
| Valores numéricos | Georgia 500 | 22–30px | `--ocas-floresta` |
| Labels / tags | Courier New | 9–11px | `--ocas-igapo` |
| Vínculo institucional | Courier New | 9px | `--ocas-igapo` |
| Texto de interface | system-ui | 12–14px | herdado |
| Descrições / legenda | system-ui | 10–12px | `--ocas-buriti` |

---

## 8. NOTAS DE IMPLEMENTAÇÃO

- **Fundo da página:** sempre `--ocas-bg-page` (#F7FAF8), nunca branco puro.
- **Cards:** fundo branco (#ffffff) com borda 0.5px — o contraste sutil com o fundo de página é intencional.
- **Borda-acento nos cards:** 2px na esquerda (única exceção à regra de 0.5px); verde padrão para cadeias, Cerrado para MATOPIBA/agropecuária, Rio para pesca/hídrico.
- **Hover em links e nav:** transição `color` de 0.2s, sem `transform` ou `box-shadow`.
- **Favicon:** usar o SVG versão 32px convertido para `.ico` ou declarado como `<link rel="icon" type="image/svg+xml">` no `<head>`.
- **Responsividade:** `grid-template-columns: repeat(auto-fit, minmax(160px, 1fr))` nos cards garante colapso natural em mobile sem media queries adicionais.
- **Acessibilidade:** todos os SVGs devem ter `role="img"` e `aria-label="OCAS-MA"`.
