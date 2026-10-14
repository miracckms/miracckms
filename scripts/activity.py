"""Draws the animated activity card from the public contribution graph.

The public graph includes private contributions (as counts) when the profile allows it,
which the GraphQL-based stat services do not see. Standard library only.

Usage: python3 scripts/activity.py <github-user> <output.svg>
"""
import datetime as dt
import re
import sys
import urllib.request

USER, OUT = sys.argv[1], sys.argv[2]
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
BG, BLUE, PURPLE, PINK, MUTED = "#0b0e1a", "#7aa2f7", "#bb9af7", "#f472b6", "#737aa2"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-activity-card"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def parse(html):
    dates = dict(re.findall(r'data-date="(\d{4}-\d{2}-\d{2})" id="([^"]+)"', html))
    by_id = {v: k for k, v in dates.items()}
    days = {}
    for cell, label in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        if cell in by_id:
            m = re.match(r"([\d,]+) contributions?", label)
            days[by_id[cell]] = int(m.group(1).replace(",", "")) if m else 0
    return days


def first_year():
    html = fetch(f"https://github.com/{USER}")
    years = [int(y) for y in re.findall(r'id="year-link-(\d{4})"', html)]
    return min(years) if years else dt.date.today().year - 5


today = dt.date.today()
days = {}
for year in range(first_year(), today.year + 1):
    days.update(parse(fetch(f"https://github.com/users/{USER}/contributions?from={year}-01-01&to={year}-12-31")))
days.update(parse(fetch(f"https://github.com/users/{USER}/contributions")))
days = {dt.date.fromisoformat(k): v for k, v in days.items() if dt.date.fromisoformat(k) <= today}
if not days:
    sys.exit("no contribution data found")

ordered = sorted(days)
total = sum(days.values())
year_ago = today - dt.timedelta(days=365)
last_year = sum(v for d, v in days.items() if d > year_ago)

longest, longest_range, run, run_start = 0, None, 0, None
for d in ordered:
    if days[d] > 0:
        run_start = d if run == 0 else run_start
        run += 1
        if run > longest:
            longest, longest_range = run, (run_start, d)
    else:
        run = 0

current, d = 0, today
if days.get(d, 0) == 0:
    d -= dt.timedelta(days=1)  # today is not over yet
while days.get(d, 0) > 0:
    current += 1
    d -= dt.timedelta(days=1)
current_start = d + dt.timedelta(days=1)

active = sum(1 for d, v in days.items() if d > year_ago and v > 0)
weeks = []
start = today - dt.timedelta(days=7 * 52)
for i in range(52):
    a = start + dt.timedelta(days=7 * i)
    weeks.append(sum(days.get(a + dt.timedelta(days=k), 0) for k in range(1, 8)))


def fmt_date(d):
    return d.strftime("%b %-d, %Y")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def hold(start, end, delay, dur, spline=".16 1 .3 1", attr=None):
    total_t = delay + dur
    k = f"{delay / total_t:.4f}"
    tag = f'animate attributeName="{attr}"' if attr else 'animateTransform attributeName="transform" type="translate"'
    return (f'<{tag} values="{start};{start};{end}" keyTimes="0;{k};1" dur="{total_t:.2f}s" fill="freeze" '
            f'calcMode="spline" keySplines="0 0 1 1;{spline}"/>')


W, H = 1000, 330
clips, parts = [], []
metrics = [
    (f"{total:,}", "Total contributions", f"since {ordered[0].year}"),
    (f"{last_year:,}", "Last 12 months", f"{active} active days"),
    (f"{current}", "Current streak", f"{fmt_date(current_start)} - today" if current else "starts today"),
    (f"{longest}", "Longest streak", f"{fmt_date(longest_range[0])} - {fmt_date(longest_range[1])}" if longest_range else "-"),
]
gap, pad = 16, 16
cw = (W - 2 * pad - 3 * gap) / 4
fs, lh = 40, 50
adv = fs * 0.6
for i, (val, label, sub) in enumerate(metrics):
    x = pad + i * (cw + gap)
    parts.append(f'<rect x="{x:.1f}" y="{pad}" width="{cw:.1f}" height="128" rx="14" fill="#ffffff" fill-opacity=".03" stroke="#fff" stroke-opacity=".07"/>')
    if i == 2:  # flame on the current streak
        parts.append(f'<g transform="translate({x + cw - 26:.1f} {pad + 36})"><text font-size="18" text-anchor="middle">🔥'
                     f'<animateTransform attributeName="transform" type="scale" values="1;1.15;1" dur="1.4s" repeatCount="indefinite"/></text></g>')
    sx = x + cw / 2 - len(val) * adv / 2
    base = 78
    for j, ch in enumerate(val):
        cx = sx + j * adv
        if ch.isdigit():
            seq = list(range(10)) + list(range(int(ch) + 1))
            dist = (len(seq) - 1) * lh
            cid = f"m{i}_{j}"
            clips.append(f'<clipPath id="{cid}"><rect x="{cx - 2:.1f}" y="{base - 38}" width="{adv + 4:.1f}" height="{lh}"/></clipPath>')
            col = "".join(f'<text x="{cx:.1f}" y="{base + k * lh}" font-size="{fs}" font-weight="800" class="mono" fill="url(#brand)">{n}</text>' for k, n in enumerate(seq))
            parts.append(f'<g clip-path="url(#{cid})"><g transform="translate(0 {-dist})">{col}{hold("0 0", f"0 {-dist}", .3 + i * .2 + j * .08, 1.8)}</g></g>')
        else:
            parts.append(f'<text x="{cx:.1f}" y="{base}" font-size="{fs}" font-weight="800" class="mono" fill="url(#brand)">{esc(ch)}</text>')
    parts.append(f'<text x="{x + cw / 2:.1f}" y="{base + 30}" text-anchor="middle" font-size="14" font-weight="600" fill="#c0caf5">{esc(label)}</text>')
    parts.append(f'<text x="{x + cw / 2:.1f}" y="{base + 50}" text-anchor="middle" font-size="11.5" fill="{MUTED}" class="mono">{esc(sub)}</text>')

# weekly area chart
cx0, cx1, cy0, cy1 = 40, W - 40, 190, 300
# square-root scale so a few very busy weeks do not flatten the rest of the year
peak = max(weeks) ** .5 or 1
pts = [(cx0 + i * (cx1 - cx0) / (len(weeks) - 1), cy1 - v ** .5 / peak * (cy1 - cy0)) for i, v in enumerate(weeks)]
line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
area = line + f" L{cx1} {cy1} L{cx0} {cy1} Z"
length = sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** .5 for i in range(len(pts) - 1))
parts.append(f'<text x="{cx0}" y="{cy0 - 16}" font-size="12" font-weight="700" letter-spacing="2.5" fill="{MUTED}">WEEKLY CONTRIBUTIONS · LAST 12 MONTHS</text>')
for k in range(4):
    gy = cy0 + k * (cy1 - cy0) / 3
    parts.append(f'<line x1="{cx0}" y1="{gy:.1f}" x2="{cx1}" y2="{gy:.1f}" stroke="#fff" stroke-opacity=".05"/>')
parts.append(f'<path d="{area}" fill="url(#areaFill)">{hold(0, 1, 1.4, 1.2, ".4 0 .2 1", "opacity")}</path>')
parts.append(f'<path d="{line}" fill="none" stroke="url(#brand)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" '
             f'stroke-dasharray="{length:.0f}" stroke-dashoffset="0">{hold(f"{length:.0f}", 0, .8, 2.2, ".4 0 .2 1", "stroke-dashoffset")}</path>')
lx, ly = pts[-1]
parts.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="{PINK}"/>'
             f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="none" stroke="{PINK}" stroke-width="2">'
             f'<animate attributeName="r" values="4.5;16" dur="1.8s" begin="3s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values=".9;0" dur="1.8s" begin="3s" repeatCount="indefinite"/></circle>')
updated = dt.datetime.now(dt.timezone.utc).strftime("%b %-d, %Y")
parts.append(f'<text x="{cx1}" y="{cy0 - 16}" text-anchor="end" font-size="11" fill="{MUTED}" class="mono" opacity=".7">updated {updated}</text>')

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BLUE}"/><stop offset=".5" stop-color="{PURPLE}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
  <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PURPLE}" stop-opacity=".35"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient>
  <linearGradient id="border" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BLUE}" stop-opacity=".55"/><stop offset=".5" stop-color="{PURPLE}" stop-opacity=".15"/><stop offset="1" stop-color="{PINK}" stop-opacity=".55"/></linearGradient>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="55"/></filter>
  {''.join(clips)}
</defs>
<style>text {{ font-family: {SANS}; }} .mono {{ font-family: {MONO}; }}</style>
<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <g filter="url(#blur)">
    <circle cx="200" cy="300" r="130" fill="{BLUE}" opacity=".14"><animateTransform attributeName="transform" type="translate" values="0 0;80 -30;0 0" dur="16s" repeatCount="indefinite"/></circle>
    <circle cx="820" cy="40" r="130" fill="{PINK}" opacity=".12"><animateTransform attributeName="transform" type="translate" values="0 0;-80 40;0 0" dur="19s" repeatCount="indefinite"/></circle>
  </g>
  {''.join(parts)}
</g>
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="17.5" fill="none" stroke="url(#border)" stroke-width="1.5"/>
</svg>
"""
open(OUT, "w").write(svg)
print(f"total={total} last_year={last_year} current={current} longest={longest} days={len(days)}")
