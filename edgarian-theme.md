\# Edgarian — Design Theme \& Template Reference

\*Business magazine aesthetic · Dark/Light mode · v1.0 · April 2026\*



\---



\## 1. Design Philosophy



\- \*\*Magazine editorial\*\* — Georgia serif headlines, Helvetica Neue sans body/UI, generous whitespace

\- \*\*Flat \& minimal\*\* — no gradients, no shadows, no noise textures; 0.5px borders only

\- \*\*Data-first\*\* — typography and spacing serve the data, never decorate it

\- \*\*Two-mode parity\*\* — every component ships dark and light; neither is an afterthought



\---



\## 2. Color Tokens



\### Dark Mode (default)



```css

\--bg:      #0a0a0a   /\* page background \*/

\--bg2:     #111111   /\* card / surface \*/

\--bg3:     #1a1a1a   /\* inset / score block \*/

\--bg4:     #222222   /\* bar track / pill bg \*/

\--border:  rgba(255,255,255,0.07)   /\* subtle divider \*/

\--border2: rgba(255,255,255,0.13)   /\* card border / nav border \*/

\--text:    #f0ede8   /\* primary text \*/

\--muted:   #7a7874   /\* secondary text / labels \*/

\--accent:  #c8c0b0   /\* links, ticker symbols \*/



/\* Signal colors \*/

\--green-bg:     #141f0d

\--green-text:   #97c459

\--green-border: rgba(99,153,34,0.25)



\--red-bg:       #1c0d0d

\--red-text:     #f09595

\--red-border:   rgba(163,45,45,0.25)



\--amber-bg:     #1c1108

\--amber-text:   #ef9f27

\--amber-border: rgba(186,117,23,0.25)



\--score-color:  #97c459   /\* Edgarian Score number \*/

```



\### Light Mode



```css

\--bg:      #f4f2ee

\--bg2:     #ffffff

\--bg3:     #eceae5

\--bg4:     #e4e2dc

\--border:  rgba(0,0,0,0.07)

\--border2: rgba(0,0,0,0.13)

\--text:    #18170f

\--muted:   #6b6760

\--accent:  #2c2a22



\--green-bg:     #eaf3de

\--green-text:   #3b6d11

\--green-border: rgba(59,109,17,0.2)



\--red-bg:       #fcebeb

\--red-text:     #a32d2d

\--red-border:   rgba(163,45,45,0.2)



\--amber-bg:     #faeeda

\--amber-text:   #854f0b

\--amber-border: rgba(133,79,11,0.2)



\--score-color:  #3b6d11

```



\---



\## 3. Typography



| Role | Font | Size | Weight |

|---|---|---|---|

| Logo / Page headline | Georgia, serif | 52px (hero), 32px (section), 22px (logo) | 700 |

| Section title | Georgia, serif | 24–32px | 700 |

| Signal headline | Helvetica Neue, sans-serif | 14px | 600 |

| Body / descriptions | Helvetica Neue, sans-serif | 13–16px | 400 |

| Labels / eyebrows | Helvetica Neue, sans-serif | 10–11px | 400 |

| Accession numbers | Courier New, monospace | 10px | 400 |

| Prices / scores | Helvetica Neue, sans-serif | varies | 500–700 |



\*\*Eyebrow style:\*\* `font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted)`  

\*\*Line height:\*\* 1.7 for body text, 1.08 for large hero headlines



\---



\## 4. Spacing \& Layout



```

Page padding:       40px horizontal

Section padding:    56px vertical, 40px horizontal

Card padding:       18–28px

Gap between cards:  12–16px

Nav height:         \~56px

Sidebar width:      280px

```



\### Grid patterns

\- Hero: `grid-template-columns: 1fr 1fr` — content left, score card right

\- Signal grid: `repeat(3, 1fr)` with `gap: 16px`

\- Sidebar layout: `grid-template-columns: 280px 1fr`



\---



\## 5. Component Library



\### Navigation

```

height: \~56px

padding: 16–18px 40px

border-bottom: 0.5px solid var(--border2)

background: var(--bg)

logo: Georgia 20–22px bold

links: Helvetica Neue 12–13px, var(--muted), letter-spacing: 0.04em

active link: color var(--text) + border-bottom: 1px solid var(--text)

```



\### Mode Toggle Button

```

background: var(--bg3)

border: 0.5px solid var(--border2)

color: var(--muted)

font-size: 11–12px

padding: 5–6px 12–14px

border-radius: 20px

```



\### Signal Card

```

border: 0.5px solid var(--border2)

border-left: 3px solid \[signal color]   ← key magazine detail

border-radius: 8px

.sig-head: background var(--bg2), padding 16px 18px 10px

.sig-body: background var(--bg), border-top 0.5px solid var(--border)

headline: 14px / 600 / Helvetica Neue

plain-english: 13px / 400 / italic / var(--muted)

```



\### Signal Badge (pill)

```

font-size: 10px

padding: 3px 9px

border-radius: 20px

font-family: Helvetica Neue

font-weight: 500

Green: bg var(--green-bg), color var(--green-text)

Red:   bg var(--red-bg),   color var(--red-text)

Amber: bg var(--amber-bg), color var(--amber-text)

```



\### Score Block (sidebar)

```

background: var(--bg3)

border-radius: 8px

padding: 18px

score number: 52px / 700 / var(--score-color)

label: 10px / uppercase / letter-spacing 0.12em / var(--muted)

bar track: height 2px, background var(--bg4), border-radius 2px

bar fill:  height 2px, background var(--score-color)

```



\### Breakdown Bar Row

```css

.bar-label { display: flex; justify-content: space-between; font-size: 10px; color: var(--muted); font-family: Helvetica Neue; margin-bottom: 3px; }

.bar-track  { height: 2px; background: var(--bg4); border-radius: 2px; }

.bar-fill   { height: 2px; border-radius: 2px; background: var(--score-color); }

```



\### Feed Event Row

```

display: flex; align-items: flex-start; gap: 20px

padding: 18px 0

border-bottom: 0.5px solid var(--border)

icon: 36px × 36px, border-radius 4px, signal color bg, 11px monospace label

company: 14px / 600 / Helvetica Neue

description: 13px / var(--muted)

timestamp: 11px / var(--muted) / right-aligned

accession: 10px / Courier New / var(--muted)

```



\### Search Bar

```

input: flex 1, padding 14px 18px, bg var(--bg2), border 0.5px var(--border2), border-right none, border-radius 4px 0 0 4px

button: padding 14px 24px, bg var(--text), color var(--bg), border-radius 0 4px 4px 0, font 13px / 500 / Helvetica Neue

```



\### Notes Panel

```

border-top: 0.5px solid var(--border2)

padding: 20px 32px

background: var(--bg2)

textarea: bg var(--bg3), border 0.5px var(--border2), font 13px Helvetica Neue, border-radius 6px, height 72px

```



\### Footer

```

border-top: 0.5px solid var(--border2)

padding: 20–32px 40px

display: flex; justify-content: space-between; align-items: center

logo: 14–16px Georgia bold

note: 11–12px Helvetica Neue var(--muted)

```



\---



\## 6. Dark/Light Toggle Pattern



```javascript

let isDark = true;

function toggleMode() {

&#x20; isDark = !isDark;

&#x20; document.getElementById('app').classList.toggle('light', !isDark);

&#x20; document.querySelector('.mode-btn').textContent = isDark ? '☀ Light' : '☾ Dark';

}

```



All dark-mode tokens live on `:root`. Light-mode overrides on `.light` class applied to `#app`.



\---



\## 7. Signal Color System



| Color | Meaning | Left border | Badge bg | Badge text |

|---|---|---|---|---|

| Green | Positive / filing signal | `--green-text` | `--green-bg` | `--green-text` |

| Red | Negative / warning signal | `--red-text` | `--red-bg` | `--red-text` |

| Amber | Context-dependent / neutral | `--amber-text` | `--amber-bg` | `--amber-text` |



No Bull/Bear/Neutral labels — color carries the directional context. Investor draws their own conclusion.



\---



\## 8. Page Templates



| Page | Layout pattern | Key components |

|---|---|---|

| `/` Landing | Hero 2-col grid + signal grid 3-col + feed rows | Search bar, score card, signal cards, feed rows |

| `/signals?ticker=X` | Sidebar 280px + main flex-col | Score block, filter bar, signal cards, notes panel |

| `/feed` | Full-width, filter bar top | Feed rows, ticker search, color filter pills |

| `/special-situations?ticker=X` | Sidebar + timeline | Event timeline, filing type badges, accession links |

| `/ticker/:symbol` | Hero overview | Price, score badge, signal count summary |



\---



\*Edgarian Design Theme · v1.0 · April 2026\*  

\*Built for: React + Tailwind CSS · Reference for all mockup and Figma work\*

