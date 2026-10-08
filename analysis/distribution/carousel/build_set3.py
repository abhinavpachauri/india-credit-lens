"""Build the Set 3 carousel page: Set 2's styles + Set 3 slides. Numbers are the dashboard's stored values."""
src = open('../set2/slides.html').read()
head = src[:src.index('<body>') + len('<body>')].replace('<title>Set 2 carousel</title>', '<title>Set 3 carousel</title>')
css = r'''
  /* Set 3 */
  .duo { display: flex; flex-direction: column; gap: 22px; margin-top: 30px; }
  .duo .item { background: var(--card); border: 2px solid var(--border); border-radius: 24px; padding: 22px 26px; }
  .duo .top { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; }
  .duo .nm { font-size: 40px; font-weight: 700; }
  .duo .ft { font-size: 64px; font-weight: 800; letter-spacing: -.02em; white-space: nowrap; }
  .duo .ft span { color: var(--muted); font-weight: 500; margin: 0 10px; font-size: 48px; }
  .duo .why { font-size: 32px; color: var(--muted); margin-top: 4px; }
  .duo img { display: block; width: 100%; margin-top: 16px; border-radius: 10px; border: 2px solid var(--border); }
  .pbars { margin-top: 20px; display: flex; flex-direction: column; gap: 16px; }
  .pb { display: grid; grid-template-columns: 210px 1fr; gap: 20px; align-items: center; }
  .pb .nm { font-size: 38px; font-weight: 700; }
  .pb .rows { display: flex; flex-direction: column; gap: 6px; }
  .pb .r { display: flex; align-items: center; height: 40px; }
  .pb .f { height: 40px; border-radius: 0 8px 8px 0; background: var(--c); }
  .pb .v { font-size: 36px; font-weight: 800; margin-left: 14px; white-space: nowrap; }
  .lg { display: flex; gap: 34px; font-size: 32px; margin-top: 18px; color: var(--ink); }
  .lg i { display: inline-block; width: 24px; height: 24px; border-radius: 6px; margin-right: 10px; vertical-align: -2px; }
  .trio { display: flex; gap: 14px; margin-top: 30px; }
  .trio > div { flex: 1; background: var(--card); border: 2px solid var(--border); border-radius: 18px; padding: 14px 18px; }
  .trio .n { font-size: 30px; color: var(--muted); font-weight: 600; }
  .trio .v { font-size: 58px; font-weight: 800; letter-spacing: -.02em; }
  .line-chart { margin-top: 30px; background: var(--card); border: 2px solid var(--border); border-radius: 24px; padding: 24px 24px 12px; }
  .line-chart text { font-family: Geist, sans-serif; }
  .rr { margin-top: 54px; display: grid; grid-template-columns: 340px 1fr; column-gap: 36px; row-gap: 30px; align-items: baseline; }
  .rr b { font-size: 40px; color: var(--muted); font-weight: 600; }
  .rr span { font-size: 44px; font-weight: 800; line-height: 1.15; }
</style>'''
head = head.replace('</style>', css, 1)

# Slide 6: real card debt growth, Jan–Aug 2026 — stored series (sibc-pl, Credit Card Outstanding, real_credit).
vals = [-1.2, -1.4, 0.1, 0.3, -2.5, -2.3, -2.1, -1.1]
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
W, H, L, R, T, B = 860, 470, 90, 40, 40, 70
lo, hi = -3.0, 1.0
x = lambda i: L + i * (W - L - R) / (len(vals) - 1)
y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)
parts = []
for g in [1, 0, -1, -2, -3]:
    zero = g == 0
    stroke = '#7a6a55' if zero else '#e8ddd0'
    dash = '' if zero else ' stroke-dasharray="6 6"'
    lbl = '0%' if zero else f'{g:+d}%'.replace('-', '−')
    parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(g):.1f}" y2="{y(g):.1f}" stroke="{stroke}" stroke-width="{2 if zero else 1.5}"{dash}/>'
                 f'<text x="{L - 16}" y="{y(g) + 11:.1f}" text-anchor="end" font-size="30" fill="#7a6a55">{lbl}</text>')
pts = ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in enumerate(vals))
parts.append(f'<polyline points="{pts}" fill="none" stroke="#1f77b4" stroke-width="4" stroke-linejoin="round"/>')
for i, v in enumerate(vals):
    fill = '#1f77b4' if v < 0 else '#fffcf5'      # filled = below zero; hollow = above (second encoding, not colour alone)
    parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="{11 if i == 7 else 8}" fill="{fill}" stroke="#1f77b4" stroke-width="3"/>')
for i, m in enumerate(months):
    strong = i >= 6
    parts.append(f'<text x="{x(i):.1f}" y="{H - 24}" text-anchor="middle" font-size="30" fill="{"#2c1e0f" if strong else "#7a6a55"}" font-weight="{700 if strong else 400}">{m}</text>')
parts.append(f'<text x="{x(7):.1f}" y="{y(-1.1) - 26:.1f}" text-anchor="middle" font-size="34" font-weight="800" fill="#2c1e0f">−1.1%</text>')
parts.append(f'<text x="{x(6):.1f}" y="{y(-2.1) + 50:.1f}" text-anchor="middle" font-size="30" font-weight="700" fill="#7a6a55">−2.1%</text>')
svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Real card debt growth, Jan to Aug 2026: '
       f'below zero in 6 of 8 months; July −2.1%, August −1.1%">' + ''.join(parts) + '</svg>')

body = open('body.html').read().replace('SVG_HERE', svg)
open('slides.html', 'w').write(head + body)
print('built')
