# Verification — V18 site

## What is measured and what is not

- **Ceiling: measured, 2,630 mm** (reported 23 October 2026, location not recorded). The Blender walls, lintels, slab, ceiling lamp and pendant cables were refitted from the former 2,500 mm assumption by `scripts/update-architecture.py`.
- **Still assumed:** width 3,450 and length 5,300 mm (the CAD footprint carried since V8, `source/room-measurements.json`). Sockets, switches, radiators and pipes are not surveyed, and door swing directions are assumed. All 21 DOLLE fitting offsets in `source/Measurements-v8.json` are preview values.
- The site labels each dimension with its basis. Solid green is shown only for site measurements: currently the ceiling and the crate-to-ceiling gap. Everything else is dashed amber (assumed, preview profile or model-derived).
- `scripts/check-clearances.py` checks that the Blender architecture agrees with the room file. If a measured value differs by more than 5 mm, the check fails until the architecture is redrawn.

## Clearance report (`public/data/clearances.json`, 16 checks, no clashes)

| Check | Model value | Status |
|---|---|---|
| Kitchen-corner passage (now limited by the near leg's low brace, previously 640.9 mm at the desk corner) | 665.5 mm | tight; at least 600, about 800 is comfortable |
| Top crates to the measured ceiling (was 32 mm at the assumed 2,500 mm) | 162 mm | ok; 412 mm above the top boards lets a crate tilt in |
| Bed to desk aisle | 673 mm | tight |
| Under-bed boxes below the 250 mm side beam (was a 5 mm overlap) | 20 mm | ok |
| Computer keyboard to MIDI controller (was a 10 mm overlap) | 20 mm | ok |
| Desk equipment intersections, including the new monitor arm | 0 | ok |
| Speakers at the rear-outer tray corner (30 mm from tray centre; the 5 mm tray edge margin is the limit, frame parts 90–115 mm away) | 77 mm to wall | ok |
| Speaker tweeter aim error at the seated ear reference (was about 17°) | 5.0° | ok |
| Room, bathroom, entrance and both balcony leaf sweeps (directions assumed) | 27–160 mm | ok |
| Central knee zone | 700 mm wide | ok; check against your own knees and chair arms |

## Geometry and data

- 54 source connection/geometry tests pass. They cover the R100 entrance corner, ear-aimed speaker trays, mirrored rear-outer speaker placement and the wall plane read from the room file.
- All 291 frame/timber components are assigned exactly once across 21 planning stages. The BOM part counts are unchanged.
- Data checks reconcile the core €2,968.90 estimate, pack quantities, KTX2 textures, the Basis transcoder version, the clearance report and the measured/assumed dimension labels.
- Supplier status notes were rechecked on 21 October 2026. Globus listings were sold out without a price. Three OBI pages returned 404. The four-way cross EAN is listed elsewhere as a corner coupling and must be confirmed. The 1,200 mm tube is DOLLE 96322.

## Rendering

- Cycles combined bake: 128 samples and six diffuse bounces, with the main ceiling fixture off. Atlases are sized by texel density, about 1.5–3 mm per pixel on the frame, desk timber and equipment. Hidden faces are removed, islands are tightly packed, and margins are 16 px. The 18 atlases took 761 s to bake.
- Atlases are baked in float and saved through the scene's AgX view transform (exposure +0.45). The browser renders them without tone mapping, so the colour matches the Blender poster.
- KTX2 textures (UASTC + Zstandard; ETC1S for walls, ceiling, exterior and glass), mipmapped. The model is 13.5 MB, with about 77 MB of GPU texture memory, previously about 520 MB.
- Inside the flat, the cutaway keeps walls, ceiling and outside view. The render loop sleeps when idle, follows pixel-density changes and pauses and recovers on WebGL context loss. The 3D viewers load on first use.
- Eight viewer tests pass. Browser checks covered the overview, workstation, dimensions, two-click measure tool, assembly 3D view and a 390 px layout.

Physical dimensions and hardware load ratings remain provisional. These checks do not certify structural safety or the physical installation sequence.
