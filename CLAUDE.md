# Agent rules

- **Do not update the Portal variant.** The owner is going with the regular V18 layout. Changes to the flat go into V18 only: `source/flat-v18.blend`, `scripts/generate-data.py`, the default bake and the V18 data. Do not run `scripts/build-portal-variant.py`, `generate-portal-data.py`, or any `FLAT_VARIANT=portal` step, and do not re-bake the portal, unless the owner asks for it explicitly. A shared script change (for example to `scripts/bake-room.py` or `src/viewer.js`) must still leave the frozen portal assets loading. Portal-only checks are not to be fixed by re-baking.
- `scripts/optimize-models.mjs` needs the local KTX tool: `KTX_BIN=~/.local/ktx/bin/ktx DYLD_LIBRARY_PATH=~/.local/ktx/lib`.
