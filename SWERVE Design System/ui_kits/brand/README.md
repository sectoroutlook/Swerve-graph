# SWERVE Brand UI Kit

A high-fidelity click-through prototype of the SWERVE marketing/brand surface.

## Screens

| Screen | File | Description |
|--------|------|-------------|
| Home | `HomeScreen.jsx` | Hero, features grid, CTA banner |
| Pricing | `PricingScreen.jsx` | 3-tier pricing cards with gradient featured plan |
| Sign Up | `SignUpScreen.jsx` | Split-panel auth with gradient left, form right |

## Components (`Components.jsx`)

| Component | Props | Notes |
|-----------|-------|-------|
| `Nav` | `onNav, current` | Sticky frosted nav with logo + CTA |
| `Btn` | `variant, size, onClick, style` | primary / secondary / ghost |
| `Badge` | `color` | purple / blue / grad pill badges |
| `Card` | `gradient, style` | Elevated card, optional gradient border |
| `Label` | — | Overline label (uppercase, spaced) |

## Usage

Open `index.html` in a browser. Use the screen switcher at the top to navigate.

## Design Notes

- Dark-mode first (`#0a0a0a` base)
- Fonts loaded from `../../fonts/` (Poppins + Montserrat)
- Gradient: `linear-gradient(135deg, #c4b5fd 0%, #a78bfa 25%, #6d9ef5 65%, #93c5fd 100%)`
- See `../../colors_and_type.css` for all tokens
