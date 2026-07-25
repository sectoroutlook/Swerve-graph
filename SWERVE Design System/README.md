# SWERVE Design System

## Overview

**SWERVE** is an investing SaaS platform built for institutional research on Emerging Markets. It simplifies complex financial data into a sharp, fluid, and responsive experience — designed for analysts, portfolio managers, and institutional investors.

> "Finance doesn't need to be intimidating. With the right tools and the right tone, it can feel fluid, empowering, and even enjoyable." — Brand Guidelines v1.0

### Sources
- Brand Guidelines PDF: `uploads/brand-guidelines.pdf` (SWERVE Brand Guideline Presentation v1.0, 2025)
- Logo assets: `uploads/SWERVE Final Assets.ai` + PNG exports
- Fonts: Poppins (all weights, TTF) + Montserrat (variable TTF, secondary)
- No codebase or Figma URL provided

---

## CONTENT FUNDAMENTALS

### Product Context
- **What**: AI-powered financial research platform — generates analyst-grade reports faster, smarter, with unmatched precision
- **URL**: https://swerve.wtf
- **Tagline**: "AI Financial Research" / "AI Powered Analysis"
- **Scale**: 500+ reports per quarter, 100+ analysts + AI
- **Model**: Hybrid — AI generates draft reports, human analysts review and approve
- **Who**: Analysts, portfolio managers, institutional investors
- **Markets covered**: Emerging Markets — India, Brazil, Vietnam, MENA, Africa, Southeast Asia + 40+ countries
- **Core value prop**: "Say goodbye to manual drudgery and hello to seamless, automated insights that save time and elevate performance"

### Tone & Voice
- **Calm, confident, calculated** — the brand's own words for its color palette; apply to copy too
- **Clear and empowering** — finance should feel fluid, not intimidating
- **Data-literate and human-aware** — balance technical precision with approachability
- **Direct and lean** — no filler words; every sentence earns its place
- **"You" focused** — speaks directly to the user/analyst
- **No emoji** — the brand is clean and professional
- **Casing**: sentence case for body; Title Case for headings; ALL CAPS for overline labels only

### Copy Examples
- "Finance, redesigned for how you think."
- "From uncertainty to clarity, from question to decision."
- "Built for a new generation of users — intuitive, clear, and relevant."
- "This is not just a letter — it's a signal." (re: the W mark)

---

## VISUAL FOUNDATIONS

### Colors (Official — from Brand Guidelines)

#### Primary Colors
| Token | Hex | Name | Usage |
|---|---|---|---|
| `--color-core-purple` | `#9666e3` | Core Purple | Bold, expressive; foundational brand tone |
| `--color-primary-blue` | `#1892f3` | Primary Blue | Crisp, energetic; actions, CTAs, motion |

#### Secondary Colors
| Token | Hex | Name | Usage |
|---|---|---|---|
| `--color-soft-purple` | `#d1c4fc` | Soft Purple | Calm, supportive; bg tints, hover states |
| `--color-soft-blue` | `#cfe6fa` | Soft Blue | Airy, breathing room; light backgrounds |

#### Neutral Colors
| Token | Hex | Name | Usage |
|---|---|---|---|
| `--color-neutral-black` | `#2c2c2e` | Neutral Black | Dark mode, typography, grounding |
| `--color-base-white` | `#f3f1f3` | Base White | Off-white; clean UI, light mode base |

#### Dark Mode Gradient Palette
| Token | Hex | Name |
|---|---|---|
| `--color-infra-shadow` | `#0e0d11` | Infra Shadow (deepest bg) |
| `--color-synth-purple` | `#aa7bff` | Synth Purple |
| `--color-pulse-blue` | `#6bd6ff` | Pulse Blue |
| `--color-ghost-lilac` | `#e3cfff` | Ghost Lilac |

### Gradients
- **Always built from the brand palette only** — no external colors
- **Light mode**: `linear-gradient(to right, #9666e3, #1892f3)` — left to right
- **Hero/Splash**: blend with soft tones — `#d1c4fc → #9666e3 → #1892f3 → #cfe6fa`
- **Dark mode**: `linear-gradient(135deg, #0e0d11, #aa7bff, #6bd6ff, #e3cfff)`
- **Max 3–4 stops** to maintain clarity
- **Use gradients for**: hero backgrounds, splash screens, dashboards, onboarding flows, behind the logo
- **Avoid gradients on**: body text, data tables, buttons, toggles, small UI components

### The W Mark
The SWERVE logo's custom "W" is inspired by the **Head and Shoulders trading chart pattern** — representing movement, insight, and investing logic. The upward/downward shapes visually reference a stock chart. It is used as: brand pattern, app icon, favicon, and animations.

### Typography
**Poppins is the sole brand typeface.** Geometric sans-serif, clean and built for digital.

| Weight | Usage |
|---|---|
| Bold (700) | Page titles, H1 headers, key moments |
| Medium (500) | Subheaders, labels, menu items |
| Regular (400) | Body text, captions, tooltips |
| Light (300) | Supporting text, form hints — use sparingly |

Montserrat (variable) is available as an alternate but is not specified in the official guidelines.

### Backgrounds
- **Dark mode first** — `#0e0d11` (Infra Shadow) as page base
- **Surface layers**: `#131218`, `#1c1b23` — for panels, cards
- **Gradient backgrounds**: used for hero sections, splash, onboarding — not for data-heavy views
- **No illustrations, patterns, or textures** — visual language is clean and minimal

### Animation
- Brand is "fluid, smooth, responsive" — motion reflects growth and decision-making
- Transitions: 150–250ms, `cubic-bezier(0.4, 0, 0.2, 1)`
- Gradients used in **loading states and transitions** — not decorative
- No bouncy or spring animations — brand is precise, not playful

### Interactive States
- **Hover**: slight opacity reduction (0.85) or subtle background lift; gradient buttons may shift upward 1px
- **Focus**: purple ring — `box-shadow: 0 0 0 3px rgba(150,102,227,0.15)` + `border-color: #9666e3`
- **Press**: scale 0.97 + darker tone

### Cards
- Background: `#1c1b23`, border: `rgba(255,255,255,0.08)`, radius: 12–16px
- Featured/active cards: gradient border using `GRAD` as a pseudo-element
- Shadow: `0 4px 20px rgba(0,0,0,0.45)`

### Corner Radii
- Buttons / tags: 7–8px
- Cards / panels: 12–16px
- Modals: 20px
- Pills (badges): 9999px

### Financial-specific UI
- **Gain**: `#34d399` (green)
- **Loss**: `#f87171` (red)
- **Neutral / data**: monospace font for numbers
- Spark lines, trend indicators — use brand positive/negative colors

---

## ICONOGRAPHY

No icon set was included in the provided assets. Based on the brand's precise, minimal aesthetic:
- **Recommended**: Lucide Icons (`https://unpkg.com/lucide@latest`) — 1.5px stroke weight, clean geometry
- **Style**: Outlined/stroke icons only — no filled icons
- **Never use emoji as icons**
- The W mark (`assets/watermark-gradient.png`) is the primary brand icon/favicon

---

## FILE INDEX

```
README.md                     — This file
SKILL.md                      — Agent skill definition
colors_and_type.css           — All CSS design tokens

assets/
  logo-primary.png            — Primary wordmark (gradient W + dark text)
  logo-mark-dark.png          — Standalone W mark, charcoal
  logo-secondary-black.png    — Wordmark, all charcoal (print / light bg)
  logo-secondary-white.png    — Wordmark, white (dark bg / overlays)
  watermark-gradient.png      — W mark, gradient fill (hero, icon, favicon)
  watermark-white.png         — W mark, white (on gradient / image overlays)
  gradient-bg.png             — Brand gradient background

fonts/
  Poppins-{Weight}.ttf        — All Poppins weights (300–900)
  Montserrat-Variable.ttf     — Variable weight Montserrat

preview/                      — Design System tab cards (16 registered)
  colors-brand.html           — Official 6-color brand palette
  colors-gradient.html        — Gradient builds (light + dark)
  colors-darkmode.html        — Dark mode gradient palette
  colors-semantic.html        — CSS token reference (fg/bg/accent)
  type-display.html           — Poppins Bold display scale
  type-body.html              — Body, label, caption scale
  type-weights.html           — Weight range with official usage notes
  type-montserrat.html        — Alternate display font
  spacing-tokens.html         — Spacing scale
  radii-shadows.html          — Radii + shadow system
  components-buttons.html     — Buttons (all variants + sizes)
  components-cards.html       — Card variants
  components-badges.html      — Badges + financial indicators
  components-inputs.html      — Form input states
  brand-logos.html            — All logo variants on various backgrounds
  brand-gradient-bg.html      — Hero gradient treatment

ui_kits/
  brand/
    index.html                — Interactive kit (Dashboard · Research · Sign Up)
    Components.jsx            — Nav, Btn, Card, StatCard, Badge, SLabel, Spark
    DashboardScreen.jsx       — Markets overview + research feed + key markets
    ResearchScreen.jsx        — Full research report view with key metrics
    SignUpScreen.jsx          — Split-panel auth with gradient left + success state
    README.md                 — UI kit component reference
```
