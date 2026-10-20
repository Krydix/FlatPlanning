# FlatPlanning — locked V18

**Live GitHub Pages site: https://krydix.github.io/FlatPlanning/**

An interactive Three.js model of the approved studio apartment, with baked practical night lighting (main ceiling fixture off), an original illustrated assembly planning guide and a complete linked, priced bill of materials.

## On the site

- **Free 3D:** orbit, zoom and switch between seven room views, including the desk joints and equipment, with Cycles-baked lighting throughout camera movement. Smart cutaway retains the illuminated walls inside the apartment.
- Follow 21 illustrated stages, or inspect each stage in a 3D component viewer. All 291 frame/timber components are assigned exactly once.
- Save assembly progress and purchase checks in your browser. Nothing is sent to a server.
- Search/filter the BOM, follow supplier links and download CSV cut lists, DXF plans and the original Blender model.
- Print the complete illustrated guide and BOM using your browser’s PDF/print function.

The freely movable room uses a **128-sample Cycles bake**, with UV atlases up to **4096 × 4096**. Direct light, indirect bounce, emission and diffuse colour are stored in the textures, exported as unlit glTF and compressed with Meshopt. Camera presets and hand orbit use exactly the same model, materials and cutaway rule. They do not switch lighting systems.

The desktop uses two DOLLE four-way threaded crosses, fully connected rear bridges and offset low front T braces. The cross-bearing uprights are split into catalog stock sections; the €4 per-cross price is a budget allowance. Shelf positions and the 64.1 cm entrance gap remain unchanged.

The rear equipment shelf holds the M1 Mac mini, router and separated power bricks. The OWC Thunderbolt 4 dock and Focusrite mount under opposite front ends with exposed controls; the 700 mm central knee width stays clear. The Equipment camera hides the chair for inspection only. Holder designs and router/brick envelopes remain provisional; their costs are allowances. A €40 allowance covers a 2 m certified Thunderbolt lead for the shown routing; reuse a suitable existing lead if available.

## Development

Requires Node.js 22.12+ (or a compatible newer version) and Python 3 for data generation/tests.

```sh
npm ci
npm run dev
```

```sh
npm run check
node --test scripts/test-viewer.mjs
python3 -m unittest discover -s source -p 'test_*.py'
npm run build
```

`docs/` contains the reproducible static build. The Pages workflow checks the data and model tests, rebuilds the site and publishes on pushes to `main`. Relative asset URLs support the `/FlatPlanning/` path.

## Source of truth

- `source/flat-v18.blend`: the locked apartment model.
- `source/assembly.json`: checked component graph, stock lengths and preview fitting profile.
- `source/pipe_engine.py`: connection rules and shared desk-frame design.
- `source/equipment-layout.json`: measured M1 case size and provisional equipment/mount clearances.
- `source/prices.json`: dated hardware prices and timber/fixing allowances.
- `scripts/generate-data.py`: BOM reconciliation, assembly-stage assignment and original SVG illustrations.
- `scripts/update-desk-joints.py`: rebuild the corrected frame from the stock-pipe graph in Blender.
- `scripts/update-joint-drawings.py`: refresh the matching DXF graph layers.
- `scripts/bake-room.py`: Blender 5.2 bake/export pipeline, preserving the practical lights with the ceiling fixture off.
- `public/data/bake-manifest.json`: bake settings and asset records.
- `scripts/optimize-models.mjs`: Meshopt compression for the browser asset.

Smaller devices cap uploaded texture sizes to reduce GPU memory use.

After changing the locked source, regenerate with:

```sh
# Run scripts/update-desk-joints.py with Blender if the frame graph changes.
python3 scripts/generate-data.py
# Run scripts/bake-room.py with Blender 5.2 in background mode.
node scripts/optimize-models.mjs
npm run check
npm run build
```

## Planning limits

V18 is a locked layout, not a structural fabrication approval. Room height and connector seating offsets are unmeasured. Clamp anti-rotation, shelf-holder screws, wall anchors, tabletop stiffness and actual equipment loads need verification before building. Timber sizes, bores and light-pocket details are provisional. The bathroom is a shell because its fixtures are unknown.

Core working estimate: **€2,968.90**, including a 10% reserve. With the six KNAGGLIG crates and corresponding reserve: **€3,034.83**. Without wood: **€1,821.64**, including a recalculated 10% reserve; excludes boards, timber waste and light covers, while retaining machining/fixings. Add the actual reclaimed-wood cost separately. The Parts & budget page shows every category subtotal and the filtered-table subtotal. Price basis: 19–20 October 2026; store stock and final prices must be checked. Bed, entrance furniture, installation labour and new electronics are excluded.

![Approved apartment](public/images/room.jpg)
