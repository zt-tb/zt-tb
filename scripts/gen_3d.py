#!/usr/bin/env python3
"""Generate an isometric 3D contribution chart as a self-contained SVG.

Usage (GitHub Actions):  GITHUB_TOKEN=... USERNAME=zt-tb python scripts/gen_3d.py
Local preview:           python scripts/gen_3d.py --demo
No third-party packages required.
"""
import json, math, os, random, sys, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "3d-contrib.svg")

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{contributionDays{contributionCount date weekday}}
      }
    }
  }
}"""

def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "zt-tb-3d-contrib"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {data}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks

def demo():
    random.seed(7)
    weeks = [[0 if random.random() < .7 else random.randint(1, 9) for _ in range(7)] for _ in range(53)]
    for d in range(4): weeks[-1][d] = 6 + d
    return sum(map(sum, weeks)), weeks

PALETTE = ["#1c2233", "#1b7fa8", "#26A5E4", "#a06bff", "#ff4fa3"]

def shade(hex_, f):
    h = hex_.lstrip("#"); r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * f))) for c in (r, g, b))

def level(n, mx):
    if n <= 0: return 0
    q = n / mx
    return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .75 else 4

def render(total, weeks):
    s = 11.0                      # cell size
    cx, cy = s * .866, s * .5     # iso step
    mx = max([max(w) for w in weeks] + [1])
    cols = len(weeks)
    pad_x, pad_top = 30, 120
    W = int((cols + 7) * cx) + pad_x * 2
    H = int((cols + 7) * cy) + pad_top + 110
    ox = pad_x + 7 * cx           # origin x so left-most point is inside
    oy = pad_top + 70

    def P(i, j, z=0):
        return (ox + (i - j) * cx, oy + (i + j) * cy - z)

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="3D contributions">')
    out.append("""<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b0d14"/><stop offset=".55" stop-color="#12142b"/><stop offset="1" stop-color="#1b1f3a"/></linearGradient>
<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="#26A5E4"/><stop offset="1" stop-color="#ff4fa3"/></linearGradient>
<radialGradient id="glow" cx=".5" cy=".55" r=".6"><stop offset="0" stop-color="#26A5E4" stop-opacity=".22"/><stop offset="1" stop-color="#26A5E4" stop-opacity="0"/></radialGradient>
<style>
.b{opacity:0;animation:in .7s ease-out forwards}
@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
text{font-family:"Segoe UI",Arial,sans-serif}
</style></defs>""")
    out.append(f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)" stroke="#30363d"/>')
    out.append(f'<ellipse cx="{W/2}" cy="{H*.58}" rx="{W*.42}" ry="{H*.3}" fill="url(#glow)"/>')
    out.append(f'<text x="30" y="46" fill="#fff" font-size="20" font-weight="700" letter-spacing="1">3D CONTRIBUTIONS</text>')
    out.append(f'<text x="{W-30}" y="46" fill="#ff4fa3" font-size="16" font-weight="700" text-anchor="end">{total} in the last year</text>')
    out.append(f'<rect x="30" y="58" width="{W-60}" height="2" rx="1" fill="url(#ln)" opacity=".8"/>')

    # base plate
    a, b, c, d = P(-.4, -.4), P(cols - .6, -.4), P(cols - .6, 6.6), P(-.4, 6.6)
    out.append(f'<polygon points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} {c[0]:.1f},{c[1]:.1f} {d[0]:.1f},{d[1]:.1f}" fill="#0d1020" stroke="#2a2f45" stroke-width="1"/>')

    # bars: painter's algorithm, back (small i+j) to front
    cells = [(i, j, n) for i, w in enumerate(weeks) for j, n in enumerate(w)]
    cells.sort(key=lambda t: (t[0] + t[1], t[0]))
    for i, j, n in cells:
        lv = level(n, mx); col = PALETTE[lv]
        z = 2.5 if n == 0 else 5 + (n / mx) * 62
        x0, x1, y0, y1 = i, i + .82, j, j + .82
        p = {k: P(*v) for k, v in {
            "t0": (x0, y0, z), "t1": (x1, y0, z), "t2": (x1, y1, z), "t3": (x0, y1, z),
            "b1": (x1, y0, 0), "b2": (x1, y1, 0), "b3": (x0, y1, 0)}.items()}
        f = lambda *k: " ".join(f"{p[q][0]:.1f},{p[q][1]:.1f}" for q in k)
        delay = (i * 0.012)
        out.append(f'<g class="b" style="animation-delay:{delay:.2f}s">'
                   f'<polygon points="{f("t0","t1","t2","t3")}" fill="{col}"/>'
                   f'<polygon points="{f("t3","t2","b2","b3")}" fill="{shade(col,.62)}"/>'
                   f'<polygon points="{f("t2","t1","b1","b2")}" fill="{shade(col,.8)}"/></g>')

    # legend
    lx, ly = 30, H - 38
    out.append(f'<text x="{lx}" y="{ly+11}" fill="#9aa0b4" font-size="12">Less</text>')
    for k, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx+40+k*20}" y="{ly}" width="14" height="14" rx="3" fill="{c}"/>')
    out.append(f'<text x="{lx+40+5*20+6}" y="{ly+11}" fill="#9aa0b4" font-size="12">More</text>')
    out.append(f'<text x="{W-30}" y="{ly+11}" fill="#9aa0b4" font-size="12" text-anchor="end">@zt-tb</text>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    if "--demo" in sys.argv:
        total, weeks = demo()
    else:
        token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("USERNAME")
        if not token or not user:
            raise SystemExit("GITHUB_TOKEN and USERNAME are required")
        total, weeks = fetch(user, token)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf8") as fh:
        fh.write(render(total, weeks))
    print(f"wrote {OUT} ({total} contributions, {len(weeks)} weeks)")
