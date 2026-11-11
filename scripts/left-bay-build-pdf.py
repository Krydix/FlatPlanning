"""Build plan + shopping list for the window-side (far-left) coat bay of V18, as HTML for Chrome print-to-PDF."""
import json, sys, html

REPO = sys.argv[1]
OUT = sys.argv[2]
proj = json.load(open(f"{REPO}/docs/data/project.json"))
asm = json.load(open(f"{REPO}/docs/data/assembly.json"))
parts = {p["id"]: p for p in proj["parts"]}

# ---- bay scope, taken from assembly.json ids -------------------------------------------
BAY_POSTS = ["RF2", "RB2", "RF3", "RB3"]
BAY_IDS = set()
for p in asm["parts"]:
    i = p["id"]
    if i.split(".")[0] in BAY_POSTS:
        BAY_IDS.add(i)
    if i.startswith(("ShelfCross.RF2.RB2.185", "ShelfCross.RF2.RB2.2175", "ShelfCross.RF3.RB3",
                     "Rack.depth3.", "Rack.clean2.", "Rack.wall2.", "Rack.wall3.",
                     "Rack.top2", "Rack.coat_shoes")):
        BAY_IDS.add(i)
# neighbour (folded bay) sleeves that live on the shared RF2/RB2 posts -> stage now
PRESTAGE = [p for p in asm["parts"] if p["kind"] == "slide_tee" and p["data"].get("host", "").split(".")[0] in ("RF2", "RB2")
            and p["id"] not in BAY_IDS]
counts = {}
for p in asm["parts"]:
    if p["id"] in BAY_IDS:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1

KIND_TO_PART = {"flange": "flange", "tube_1000": "tube_1000", "tube_1200": "tube_1200", "extension": "extension",
                "cap": "cap", "slide_tee": "slide_tee", "tube_250": "tube_250", "tube_602": "tube_602",
                "tube_40": "tube_40", "saddle": "saddle"}
LABEL = {"flange": "Ø70 mm flange (4 floor feet + 2 wall ties)", "tube_1000": "Pipe 1,000 mm (lower posts)",
         "tube_1200": "Pipe 1,200 mm (upper posts)", "extension": "Coupling, female–female",
         "cap": "End cover (pack of 2)", "slide_tee": "Sliding T connector", "tube_250": "Pipe 250 mm (depth rungs)",
         "tube_602": "Pipe 602 mm (coat rail)", "tube_40": "Pipe 40 mm (wall ties)",
         "saddle": "Saddle shelf holder (pack of 2)"}
ORDER = ["slide_tee", "tube_1200", "tube_1000", "flange", "tube_250", "saddle", "cap", "tube_602", "extension", "tube_40"]

rows = []
hw_total = 0.0
for k in ORDER:
    q = counts[k]
    pr = parts[KIND_TO_PART[k]]
    pack = pr["packSize"] or 1
    packs = -(-q // pack)
    tot = round(packs * pr["unitPrice"], 2)
    hw_total += tot
    rows.append((LABEL[k], pr["sku"].split(";")[0], q, packs, pr["unitPrice"], tot, pr["url"]))
assert counts.get("wood") == 2, counts
wood = [("Oak board · coat shoe shelf", "606 × 350 × 28 mm", 1, 33.94), ("Oak board · top shelf", "606 × 350 × 28 mm", 1, 33.94)]
wood_total = sum(w[3] for w in wood)
small = [("Felt / non-marking pads under the 4 floor flanges", 4.00),
         ("Wall plugs + screws for 2 wall flanges (choose for your wall type)", 6.00),
         ("Short wood screws for 8 saddle tabs (≈ 3.5 × 16 mm, not included with toom saddles)", 4.00),
         ("Oil / finish + sandpaper for two boards", 15.00)]
small_total = sum(s[1] for s in small)
core = hw_total + wood_total + small_total
reserve = round(core * 0.10, 2)
core_res = core + reserve
tee = parts["slide_tee"]["unitPrice"]
pre_total = round(len(PRESTAGE) * tee, 2)

def eur(v): return f"€{v:,.2f}"

# ---- per-post sleeve order -------------------------------------------------------------------
def post_of(host): return host.split(".")[0]
sleeves = {k: [] for k in BAY_POSTS}
names = {"ShelfCross": "depth rung", "Rack.depth3": "depth brace", "Rack.clean2": "coat rail", "Rack.wall": "wall tie",
         "Wear.return1": "worn-clothes return"}
for p in asm["parts"]:
    if p["kind"] != "slide_tee":
        continue
    h = p["data"].get("host", "")
    if post_of(h) not in sleeves:
        continue
    z = round(p["origin"][2])
    tube = h.split(".")[1]
    label = next(v for k, v in names.items() if p["id"].startswith(k))
    if p["id"].startswith("ShelfCross") and p["id"] not in BAY_IDS:
        label = "folded-bay rung"
    if p["id"].startswith("ShelfCross") and z == 185:
        label = "shoe-shelf rung"
    if p["id"].startswith("ShelfCross") and z == 2175:
        label = "top-shelf rung"
    sleeves[post_of(h)].append((z, label, tube, p["id"] in BAY_IDS))
for k in sleeves:
    sleeves[k].sort()

POST_NAME = {"RF3": "Window front", "RB3": "Window rear (wall)", "RF2": "Shared front", "RB2": "Shared rear (wall)"}

# ---- drawings ----------------------------------------------------------------------------
INK, MUTE, PIPE, WOOD, PARK, WALL = "#1d1d1f", "#6e6e73", "#2b2b2b", "#d8b98a", "#c0392b", "#9a9a9a"

def front_svg():
    # looking at the wall: window wall on the left. X = (5300 - y)
    W, H = 1500, 2630
    s = []
    def X(y): return 5300 - y + 90
    def Y(z): return H - z + 40
    s.append(f'<svg viewBox="0 0 {W} {H+180}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica" >')
    s.append(f'<rect x="0" y="{Y(0)}" width="{W}" height="14" fill="#ddd"/>')
    s.append(f'<line x1="0" y1="{Y(0)}" x2="{W}" y2="{Y(0)}" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<line x1="0" y1="{Y(2630)}" x2="{W}" y2="{Y(2630)}" stroke="{WALL}" stroke-width="5" stroke-dasharray="20 14"/>')
    s.append(f'<text x="{W-10}" y="{Y(2630)+50}" text-anchor="end" font-size="40" fill="{MUTE}">ceiling 2,630</text>')
    s.append(f'<rect x="{X(5300)-60}" y="{Y(2630)}" width="60" height="2630" fill="#eee" stroke="{WALL}" stroke-width="4"/>')
    s.append(f'<text transform="translate({X(5300)-18},{Y(1300)}) rotate(-90)" text-anchor="middle" font-size="36" fill="{MUTE}">window wall</text>')
    # boards
    for b in ("Rack.coat_shoes", "Rack.top2"):
        bd = asm["boards"][b]
        y0, y1 = bd["bounds"][2], bd["bounds"][3]
        s.append(f'<rect x="{X(y1)}" y="{Y(bd["bottom"]+bd["thickness"])}" width="{y1-y0}" height="{bd["thickness"]}" fill="{WOOD}" stroke="#8a6a3a" stroke-width="3"/>')
    # posts
    for y in (5214, 4572):
        s.append(f'<rect x="{X(y)-12.5}" y="{Y(2227)}" width="25" height="{2227-15}" fill="{PIPE}"/>')
        s.append(f'<rect x="{X(y)-35}" y="{Y(15)}" width="70" height="15" fill="{PIPE}"/>')
        s.append(f'<rect x="{X(y)-18}" y="{Y(1027)}" width="36" height="12" fill="#666"/>')
        s.append(f'<rect x="{X(y)-14}" y="{Y(2237)}" width="28" height="10" fill="#555"/>')
    # coat rail
    s.append(f'<rect x="{X(5194)}" y="{Y(1950)-12.5}" width="602" height="25" fill="{PIPE}"/>')
    # sleeves
    for post, y in (("RF3", 5214), ("RF2", 4572), ("RB2", 4572)):
        for z, lab, tube, inbay in sleeves[post]:
            dx = 0 if post != "RB2" else 0
            col = PIPE if inbay else PARK
            if post == "RB2" and inbay:
                continue
            s.append(f'<rect x="{X(y)-22+dx}" y="{Y(z)-30}" width="44" height="60" rx="6" fill="{col}" fill-opacity="{1 if inbay else 0.85}"/>')
    # rungs end-on
    for y in (5214, 4572):
        for z in (185, 2175):
            s.append(f'<circle cx="{X(y)}" cy="{Y(z)}" r="16" fill="#fff" stroke="{PIPE}" stroke-width="6"/>')
    s.append(f'<circle cx="{X(5214)}" cy="{Y(1800)}" r="16" fill="#fff" stroke="{PIPE}" stroke-width="6"/>')
    # dims
    def hdim(z, txt, y=4300):
        s.append(f'<line x1="{X(4572)+40}" y1="{Y(z)}" x2="{X(y)}" y2="{Y(z)}" stroke="{MUTE}" stroke-width="2" stroke-dasharray="8 6"/>')
        s.append(f'<text x="{X(y)+10}" y="{Y(z)+13}" font-size="38" fill="{INK}">{txt}</text>')
    hdim(2218, "2,218 top of top board")
    hdim(1950, "1,950 coat rail")
    hdim(1021, "1,021 coupling")
    hdim(228, "228 shoe board top")
    s.append(f'<text x="{X(4893)}" y="{Y(-60)}" text-anchor="middle" font-size="38" fill="{INK}">642 between post axes · boards 606 long</text>')
    s.append(f'<text x="{X(5214)}" y="{Y(-110)}" text-anchor="middle" font-size="34" fill="{MUTE}">86 to wall*</text>')
    s.append('</svg>')
    return "".join(s)

def side_svg():
    # window-side frame seen from the window: room on the left, wall on the right. X = x - 2900
    W, H = 850, 2630
    s = [f'<svg viewBox="0 0 {W} {H+180}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica">']
    def X(x): return x - 2800
    def Y(z): return H - z + 40
    s.append(f'<line x1="0" y1="{Y(0)}" x2="{W}" y2="{Y(0)}" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<rect x="{X(3450)}" y="{Y(2630)}" width="60" height="2630" fill="#eee" stroke="{WALL}" stroke-width="4"/>')
    s.append(f'<text transform="translate({X(3450)+40},{Y(1300)}) rotate(-90)" text-anchor="middle" font-size="36" fill="{MUTE}">wall</text>')
    bd = asm["boards"]["Rack.top2"]
    for b in ("Rack.coat_shoes", "Rack.top2"):
        bd = asm["boards"][b]
        s.append(f'<rect x="{X(bd["bounds"][0])}" y="{Y(bd["bottom"]+28)}" width="350" height="28" fill="{WOOD}" stroke="#8a6a3a" stroke-width="3" fill-opacity=".55"/>')
    for x in (3085, 3375):
        s.append(f'<rect x="{X(x)-12.5}" y="{Y(2227)}" width="25" height="{2212}" fill="{PIPE}"/>')
        s.append(f'<rect x="{X(x)-35}" y="{Y(15)}" width="70" height="15" fill="{PIPE}"/>')
        s.append(f'<rect x="{X(x)-18}" y="{Y(1027)}" width="36" height="12" fill="#666"/>')
    for z in (185, 1800, 2175):
        s.append(f'<rect x="{X(3085)}" y="{Y(z)-12.5}" width="290" height="25" fill="{PIPE}"/>')
        for x in (3085, 3375):
            s.append(f'<rect x="{X(x)-22}" y="{Y(z)-30}" width="44" height="60" rx="6" fill="{PIPE}"/>')
    # wall tie 1900
    s.append(f'<rect x="{X(3375)}" y="{Y(1900)-12.5}" width="75" height="25" fill="{PIPE}"/>')
    s.append(f'<rect x="{X(3375)-22}" y="{Y(1900)-30}" width="44" height="60" rx="6" fill="{PIPE}"/>')
    s.append(f'<rect x="{X(3450)-15}" y="{Y(1900)-35}" width="15" height="70" fill="{PIPE}"/>')
    # coat rail end-on + saddles
    s.append(f'<circle cx="{X(3085)}" cy="{Y(1950)}" r="16" fill="#fff" stroke="{PIPE}" stroke-width="6"/>')
    for x in (3180, 3280):
        for z in (185, 2175):
            s.append(f'<rect x="{X(x)-12}" y="{Y(z)-16}" width="24" height="32" fill="#888"/>')
    def lab(x, z, t, anchor="start"):
        s.append(f'<text x="{x}" y="{Y(z)}" font-size="36" fill="{INK}" text-anchor="{anchor}">{t}</text>')
    lab(X(3085) - 30, 2175 - 10, "2,175", "end")
    lab(X(3085) - 30, 1800 - 10, "1,800", "end")
    lab(X(3085) - 30, 1950 - 10, "1,950 rail", "end")
    lab(X(3085) - 30, 185 - 10, "185", "end")
    lab(X(3085) - 30, 1900 - 70, "", "end")
    s.append(f'<text x="{X(3230)}" y="{Y(1900)-45}" font-size="32" fill="{MUTE}" text-anchor="middle">wall tie 1,900</text>')
    s.append(f'<text x="{X(3230)}" y="{Y(-60)}" text-anchor="middle" font-size="38" fill="{INK}">290 front–rear</text>')
    s.append(f'<text x="{X(3410)}" y="{Y(-110)}" text-anchor="middle" font-size="34" fill="{MUTE}">75 to wall*</text>')
    s.append('</svg>')
    return "".join(s)

def plan_svg():
    # top view, wall at top, window wall at left
    s = ['<svg viewBox="0 0 1100 560" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica">']
    def X(y): return 5300 - y + 120
    def Y(x): return x - 3450 + 520 - 40
    s.append(f'<rect x="{X(5300)}" y="{Y(3450)}" width="1000" height="22" fill="#eee" stroke="{WALL}" stroke-width="3"/>')
    s.append(f'<rect x="{X(5300)-22}" y="{Y(3450)}" width="22" height="520" fill="#eee" stroke="{WALL}" stroke-width="3"/>')
    s.append(f'<text x="{X(4400)}" y="{Y(3450)+60}" font-size="28" fill="{MUTE}">right wall</text>')
    for b in ("Rack.top2",):
        bd = asm["boards"][b]
        s.append(f'<rect x="{X(bd["bounds"][3])}" y="{Y(bd["bounds"][0])-0}" width="606" height="350" fill="{WOOD}" fill-opacity=".45" stroke="#8a6a3a" stroke-width="2" transform="translate(0,0)"/>')
    for (x, y, n) in ((3085, 5214, "front"), (3375, 5214, "rear"), (3085, 4572, "front"), (3375, 4572, "rear")):
        s.append(f'<circle cx="{X(y)}" cy="{Y(x) if False else 0}" r="0"/>')
    # Note: in plan, depth (x) goes downward from wall: wall at top means smaller distance -> top.
    s = ['<svg viewBox="0 0 1300 620" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica">']
    def PY(x): return 60 + (3450 - x)        # wall at y=60
    s.append(f'<rect x="{X(5300)}" y="38" width="1000" height="22" fill="#e6e6e6" stroke="{WALL}" stroke-width="3"/>')
    s.append(f'<rect x="{X(5300)-22}" y="38" width="22" height="560" fill="#e6e6e6" stroke="{WALL}" stroke-width="3"/>')
    s.append(f'<text x="{X(5000)}" y="30" font-size="28" fill="{MUTE}">right wall (rack wall)</text>')
    s.append(f'<text transform="translate({X(5300)-32},330) rotate(-90)" text-anchor="middle" font-size="26" fill="{MUTE}">window wall</text>')
    bd = asm["boards"]["Rack.top2"]
    s.append(f'<rect x="{X(bd["bounds"][3])}" y="{PY(bd["bounds"][1])}" width="606" height="350" fill="{WOOD}" fill-opacity=".5" stroke="#8a6a3a" stroke-width="2"/>')
    for y in (5214, 4572):
        s.append(f'<line x1="{X(y)}" y1="{PY(3375)}" x2="{X(y)}" y2="{PY(3085)}" stroke="{PIPE}" stroke-width="10"/>')
        s.append(f'<line x1="{X(y)}" y1="{PY(3375)}" x2="{X(y)}" y2="{PY(3450)}" stroke="{PIPE}" stroke-width="10" stroke-dasharray="6 4"/>')
        for x in (3085, 3375):
            s.append(f'<circle cx="{X(y)}" cy="{PY(x)}" r="35" fill="none" stroke="{MUTE}" stroke-width="2"/>')
            s.append(f'<circle cx="{X(y)}" cy="{PY(x)}" r="12.5" fill="{PIPE}"/>')
    s.append(f'<line x1="{X(5214)}" y1="{PY(3085)}" x2="{X(4572)}" y2="{PY(3085)}" stroke="{PIPE}" stroke-width="10"/>')
    # dims
    s.append(f'<text x="{X(4893)}" y="{PY(3085)+70}" text-anchor="middle" font-size="30" fill="{INK}">642 post axis to post axis</text>')
    s.append(f'<text x="{X(4572)+30}" y="{PY(3230)+10}" font-size="28" fill="{INK}">290</text>')
    s.append(f'<text x="{X(4572)+30}" y="{PY(3412)+10}" font-size="26" fill="{MUTE}">75</text>')
    s.append(f'<text x="{X(5214)-20}" y="{PY(3085)+70}" text-anchor="end" font-size="26" fill="{MUTE}">86*</text>')
    s.append(f'<text x="{X(4572)+30}" y="{PY(3085)+10}" font-size="28" fill="{INK}">front posts 365 from wall</text>')
    s.append(f'<text x="1290" y="{PY(3085)+150}" text-anchor="end" font-size="28" fill="{MUTE}">next bay (folded clothes) continues →</text>')
    s.append('</svg>')
    return "".join(s)

# ---- HTML --------------------------------------------------------------------------------
E = html.escape
shop_rows = "".join(
    f"<tr><td>{E(l)}</td><td class=m>{E(str(sku))}</td><td class=n>{q}</td><td class=n>{pk}</td><td class=n>{eur(u)}</td><td class=n>{eur(t)}</td></tr>"
    for l, sku, q, pk, u, t, url in rows)
wood_rows = "".join(f"<tr><td>{E(a)}</td><td class=m>{E(b)}</td><td class=n>{c}</td><td class=n>1</td><td class=n>{eur(d)}</td><td class=n>{eur(d)}</td></tr>" for a, b, c, d in wood)
small_rows = "".join(f"<tr><td colspan=5>{E(a)}</td><td class=n>{eur(b)}</td></tr>" for a, b in small)
links = "".join(f"<li><b>{E(l)}</b> — {E(url)}</li>" for l, sku, q, pk, u, t, url in rows if url)

def post_table():
    out = []
    for post in ("RF3", "RB3", "RF2", "RB2"):
        cells = []
        for z, lab, tube, inbay in sleeves[post]:
            where = "on 1,000 lower" if tube == "lower" else "on 1,200 upper"
            cls = "" if inbay else " class=park"
            cells.append(f"<li{cls}><b>{z}</b> {E(lab)} <span class=dim>({where})</span></li>")
        out.append(f"<div class=post><h4>{POST_NAME[post]} <span class=dim>{post}</span></h4><ol>{''.join(cells)}</ol></div>")
    return "".join(out)

n_tee_bay = counts["slide_tee"]
doc = f"""<!doctype html><html><head><meta charset=utf-8><title>V18 left coat bay · test build</title>
<style>
@page {{ size: A4; margin: 14mm 14mm 16mm; }}
body {{ font: 9.6pt/1.42 -apple-system, Helvetica, Arial, sans-serif; color:#1d1d1f; }}
h1 {{ font-size: 20pt; margin: 0 0 2mm; letter-spacing:-.01em }}
h2 {{ break-after: avoid; font-size: 12.5pt; margin: 6mm 0 2mm; border-bottom: 1.5px solid #1d1d1f; padding-bottom: 1mm; }}
h3 {{ font-size: 10.5pt; margin: 4mm 0 1.5mm; }}
h4 {{ font-size: 9.5pt; margin: 0 0 1mm; }}
.lead {{ color:#444; font-size: 10.5pt; margin: 0 0 3mm }}
table {{ width:100%; border-collapse: collapse; margin: 1mm 0 2mm; }}
th, td {{ padding: 1.2mm 1.6mm; border-bottom: .5px solid #ccc; vertical-align: top; text-align:left }}
th {{ font-size: 8.4pt; text-transform: uppercase; letter-spacing:.04em; color:#555; border-bottom:1px solid #1d1d1f }}
td.n, th.n {{ text-align:right; white-space:nowrap; font-variant-numeric: tabular-nums }}
td.m {{ color:#555; font-size: 8.6pt }}
tr.sub td {{ font-weight:600; border-bottom: 1px solid #1d1d1f }}
tr.tot td {{ font-weight:700; font-size: 10.5pt; border-bottom: none }}
.box {{ border:1px solid #1d1d1f; border-radius: 2mm; padding: 2.5mm 3.5mm; margin: 2mm 0 3mm; }}
.warn {{ border-color:#c0392b; }}
.warn b.t {{ color:#c0392b }}
.grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
.grid3 {{ display:flex; justify-content:center; gap: 10mm; align-items:flex-end }}
.grid3 svg {{ height: 125mm; width:auto; display:block; margin:0 auto }}
svg {{ max-width:100% }}
.post {{ border:1px solid #bbb; border-radius:1.5mm; padding:2mm 3mm; break-inside: avoid }}
.post ol {{ margin:0; padding-left: 4.5mm }}
.post li.park {{ color:#c0392b }}
.dim {{ color:#777; font-weight: normal; font-size: 8.4pt }}
ol.steps > li {{ margin-bottom: 2.4mm; break-inside: avoid }}
ol.steps > li > b:first-child {{ font-size: 10pt }}
ul.links {{ font-size: 7.6pt; color:#555; word-break: break-all; padding-left: 4mm }}
.check {{ list-style: none; padding-left: 0 }}
.check li::before {{ content: "☐  "; }}
.cap {{ font-size: 8.2pt; color:#555; text-align:center; margin-top: 1mm }}
.pb {{ break-before: page }}
.key span {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin: 0 1mm 0 3mm; vertical-align:-1px }}
</style></head><body>

<h1>Left coat bay — test build</h1>
<p class=lead>V18 (locked). The first bay to build: the window-side wardrobe bay with the long-coat rail, the low shoe shelf and the top shelf.
"Left" means as you stand facing the rack wall, so this is the bay nearest the balcony window.</p>

<div class=grid>
<div class=box><b>What you get</b><br>
4 posts (2,227 mm high) · 2 wall ties · coat rail at 1,950 mm · shoe shelf (top at 228 mm) · top shelf (top at 2,218 mm) · bay 642 mm wide between post centres, 350 mm deep boards.</div>
<div class=box><b>Cost</b><br>
Bay itself: <b>{eur(core)}</b> + 10% reserve = <b>{eur(core_res)}</b><br>
Plus {len(PRESTAGE)} sleeves for the next bay (strongly recommended): <b>{eur(pre_total)}</b><br>
<b>Shopping total ≈ {eur(core_res + pre_total)}</b></div>
</div>

<div class="box warn"><b class=t>Why this bay is a good test.</b> No four-way crosses, no elbows, no cut pipes, and both boards are plain rectangles with no notches.
It tests what everything else depends on: real DOLLE fitting sizes, how well the sliding Ts grip, the saddle screws, and your wall anchors.
Measure those while you build it (last page). The board sizes and heights for the rest of the flat are still calculated from unmeasured fitting sizes.</div>

<h2>Shopping list</h2>
<table>
<tr><th>Part (DOLLE PIPE, black matt, Ø25 mm / ¾")</th><th>Article</th><th class=n>Pieces</th><th class=n>Buy</th><th class=n>Each</th><th class=n>Total</th></tr>
{shop_rows}
<tr class=sub><td colspan=5>Hardware for the bay</td><td class=n>{eur(hw_total)}</td></tr>
{wood_rows}
<tr class=sub><td colspan=5>Oak (price allowance, reclaimed or bought)</td><td class=n>{eur(wood_total)}</td></tr>
{small_rows}
<tr class=sub><td colspan=5>Small items (allowance)</td><td class=n>{eur(small_total)}</td></tr>
<tr><td colspan=5>10% reserve</td><td class=n>{eur(reserve)}</td></tr>
<tr class=sub><td colspan=5>Bay total</td><td class=n>{eur(core_res)}</td></tr>
<tr><td>Sliding T, extra: sleeves for the folded-clothes bay, staged on the shared posts now</td><td class=m>96544</td><td class=n>{len(PRESTAGE)}</td><td class=n>{len(PRESTAGE)}</td><td class=n>{eur(tee)}</td><td class=n>{eur(pre_total)}</td></tr>
<tr class=tot><td colspan=5>Shopping total</td><td class=n>{eur(core_res + pre_total)}</td></tr>
</table>
<p style="font-size:8.6pt;color:#444">At the till: <b>{n_tee_bay + len(PRESTAGE)} sliding Ts</b> in total. Pieces count what you fit; the Buy column counts packs (end covers and saddles come in twos).
Prices are from 19–20 Oct 2026. Globus showed several pipes as <b>sold out</b> on 21 Oct, and the OBI pages for the coupling and the 40 mm pipe returned 404. toom also sells DOLLE (1,200 mm pipe = toom 7450880).
Check stock first, and try to buy all the black pipe from one batch so the finish matches.
Bring one sliding T, the coupling and a saddle home first if you can: everything else depends on how those three really measure.</p>

<div class="box warn"><b class=t>Why buy {len(PRESTAGE)} extra sliding Ts now.</b> The two door-side posts of this bay also carry the next (folded-clothes) bay.
Its sleeves at 685, 1,085, 1,485 and 1,835 mm on both posts, plus the 1,250 mm worn-clothes return on the front post, must be on those posts <i>before</i> the couplings, rungs and covers close them in.
Leave them loose and parked for now. If you skip them, you will have to strip this bay's top shelf and rail later to add them.</div>

<h3>Tools</h3>
<p>Tape measure · spirit level (≥ 60 cm) · step ladder (to drop parts over the 2.23 m post tops; 0.4 m ceiling clearance) · drill + bits for your wall · pencil & masking tape ·
screwdriver/bits for the saddle screws · hex key for the sliding-T grub screws (check which size) · a cloth or strap wrench to tighten pipes without marking the black finish · a helper while the posts stand up loose.</p>

<h3>Shop links (as of 19–21 Oct 2026)</h3>
<ul class=links>{links}</ul>

<div class=pb></div>
<h2>Drawings</h2>
<div class=grid3>
<div>{front_svg()}<div class=cap><b>Front view</b>, facing the rack wall. Window on the left. Red = parked sleeves for the next bay (heights in the sleeve table).</div></div>
<div>{side_svg()}<div class=cap><b>Side view</b> of the window-side frame, room on the left, wall on the right.</div></div>
</div>
<div style="width:58%;margin:3mm auto 0">{plan_svg()}<div class=cap><b>Floor plan.</b> Post centres in mm. * Measured from the CAD room (5,300 × 3,450 mm), which is still <b>assumed</b>; see step 1.</div></div>

<h2 class=pb>Sleeve order on each post (bottom → top)</h2>
<p>Sliding Ts can only go on over an open pipe end. Every post below is listed in the order its sleeves sit. <span style="color:#c0392b">Red</span> = parked sleeve for the next bay. Heights are pipe-centre heights above the floor in mm.</p>
<div class=grid>{post_table()}</div>

<div class=pb></div>
<h2>Build steps</h2>
<ol class=steps>
<li><b>Measure and mark.</b> Measure the room length along the rack wall (the model assumes 5,300 mm, still unconfirmed). The post positions run from the entrance wall:
the window-side posts sit at 5,214 mm from it, the shared posts at 4,572 mm. If the room is 5,300 mm, the window-side post centres are 86 mm from the window wall. If it is not, tell me the real length before you mark anything, because the desk end has to fit too.
Mark the four post centres on masking tape on the floor: rear posts 75 mm from the wall, front posts 365 mm (290 mm apart), the two pairs 642 mm apart. Check the wall material at 1,700 mm (shared rear post) and 1,900 mm (window rear post), and check for cables or pipes before you drill.</li>

<li><b>Dry-fit one joint.</b> Screw a 250 mm pipe into a sliding T, slide the T onto a pipe, and put a saddle on and screw it to a scrap of board. Check that the grub screw grips, that the end cover fits, and that the threads run fully home. Fit nothing by force.</li>

<li><b>Pre-assemble the horizontal modules on the floor</b>, while the T sleeves are still free to turn:
<br>• 4 × <b>depth rung</b> (T + 250 mm + T): two for 185 mm (shoe shelf), two for 2,175 mm (top shelf)
<br>• 1 × <b>depth brace</b> (T + 250 mm + T) for 1,800 mm on the window-side pair
<br>• 1 × <b>coat rail</b> (T + 602 mm + T) for 1,950 mm on the two front posts
<br>• 2 × <b>wall tie</b> (T + 40 mm + flange)
<br>Screw each pipe fully home, turning the free T onto it. Lay every two-T module flat on the floor and check that both sleeves are parallel and upright. A twisted module will not drop over two posts.</li>

<li><b>Stand the lower posts.</b> Screw a floor flange onto one end of each 1,000 mm pipe. Stand the four pipes on their pads over the marks, with your helper holding them.
Drop a <b>185 rung</b> over each pair. On the shared (door-side) pair, also drop the parked <b style="color:#c0392b">685</b> sleeve onto each post.
Then screw a coupling onto each post and a 1,200 mm pipe into it, both fully engaged. The coupling sits at about 1,021 mm. Never leave a thread half-in to adjust the height.</li>

<li><b>Drop the upper sleeves from the ladder, lowest first.</b> Work across all four posts in this order:
<b style="color:#c0392b">1,085</b> (shared front + rear) → <b style="color:#c0392b">1,250</b> worn-clothes sleeve (shared front, branch facing into the room) → <b style="color:#c0392b">1,485</b> (shared pair) →
<b>1,700</b> wall tie (shared rear, branch to the wall) → <b>1,800</b> depth brace (window pair) → <b style="color:#c0392b">1,835</b> (shared pair) →
<b>1,900</b> wall tie (window rear) → <b>1,950</b> coat rail (both front posts) → <b>2,175</b> top rungs (both pairs). Then put the four end covers on.
Point each parked sleeve's branch toward the next bay or into the room, as the drawings show, and lock it loosely anywhere it won't get in the way.</li>

<li><b>Set heights and square up.</b> Slide each sleeve to its height (pipe centre above the floor) and snug the grub screws.
Check that every post is plumb both ways, and that the diagonals of each side frame and of the front face are equal. Make the two rung heights on each level match exactly, or the boards will rock.</li>

<li><b>Fix the wall ties.</b> With the frame plumb, push the two wall flanges flat against the wall, mark, drill, plug and screw them with fixings chosen for your wall. Tighten the tie sleeves last.
The gap between the rear posts and the wall comes from the real fittings (75 mm in the model); don't force it.</li>

<li><b>Finish and fit the boards.</b> Oil both 606 × 350 × 28 mm boards first. Each board sits <i>between</i> the posts (18 mm from each post centre), on the tabs of four saddles, with 30 mm overhang in front of the front post and behind the rear post (45 mm short of the wall).
Saddle positions, measured from the front-post centre toward the wall: on the shared-side rung <b>65 and 225 mm</b>, on the window-side rung <b>95 and 195 mm</b>. They are staggered so the next bay's saddles can share the rung later.
Pre-drill and use screws shorter than 28 mm. Shoe shelf: underside 200, top 228. Top shelf: underside 2,190, top 2,218.</li>

<li><b>Load test.</b> Hang your real coats (the model allows four at about 140 mm spacing, for coats up to about 1,500 mm long). Put a crate (460 × 310 × 250) on top and check that it lifts out under the ceiling.
Lean on the frame gently, and check for T slip or rotation, saddle screw pull-out and wall-tie movement. Open the right balcony door and check that the handle and curtain stay clear of the coats.</li>
</ol>

<h2>Measure these and send them to me</h2>
<p>This is the real reason to build one bay first. Once these are measured, the desk, the shelf heights and the other boards can be recalculated before you cut any more wood.</p>
<table>
<tr><th>What</th><th>Model assumes</th><th>Measured</th></tr>
<tr><td>Floor to first pipe end: flange stand-off</td><td class=n>15 mm</td><td></td></tr>
<tr><td>Gap between pipes in a coupling</td><td class=n>12 mm</td><td></td></tr>
<tr><td>Overall post height to top of pipe (before cover)</td><td class=n>2,227 mm</td><td></td></tr>
<tr><td>Sliding T: sleeve height and outer Ø; how far the branch pipe screws in (post centre to pipe end)</td><td class=n>— / 20 mm</td><td></td></tr>
<tr><td>Saddle: pipe centre to underside of board</td><td class=n>15 mm</td><td></td></tr>
<tr><td>Rear post centre to wall, with the wall tie fitted</td><td class=n>75 mm</td><td></td></tr>
<tr><td>Room length along the rack wall · room width at three heights</td><td class=n>5,300 · 3,450</td><td></td></tr>
<tr><td>Wall type at the tie points · anchors used</td><td>unknown</td><td></td></tr>
</table>
<ul class=check>
<li>Did any T slip or turn under load? Any saddle screw loosen?</li>
<li>Does the end cover fit the thread properly?</li>
<li>Do the four coats really fit, or would three be better?</li>
</ul>
<p style="font-size:8.4pt;color:#555;margin-top:4mm">Generated from the V18 model (assembly.json, project.json) on 10 Nov 2026. Concept geometry, not a load rating or drilling template. Prices are allowances or last observed shop prices.</p>
</body></html>"""
open(OUT, "w").write(doc)
print("hw", hw_total, "core", core, "res", core_res, "pre", pre_total, "counts", counts, "prestage", [p["id"] for p in PRESTAGE])
