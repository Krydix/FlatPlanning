# Verification — V18 site

- The published room geometry comes from the locked V18 Blender file. The source-model copy was checked with the component adapter before local render paths and obsolete notes were removed; geometry is unchanged.
- Cycles combined UV baking uses 128 samples, six diffuse bounces and UV atlases up to 4096 px with the main ceiling fixture off. The runtime room has unlit baked materials and exports no live lights.
- Camera presets do not change the user’s cutaway setting or replace baked materials. Smart cutaway retains the room shell for interior camera positions during both orbit and preset movement. Three regression tests cover transitions, interrupted transitions and interior shell visibility.
- Meshopt compresses the high-resolution baked room geometry for the browser. The separate assembly model retains component IDs for stage highlighting.
- Data checks reconcile the core €2,751.61 estimate, purchase pack quantities, source graph, downloadable files and glTF compression/lighting properties.
- All 270 frame/timber components are assigned exactly once across 21 planning stages.
- The 42 source connection/geometry tests pass.
- Browser checks verified the 3D room, workstation camera, cutaway, stage-specific 3D highlighting, illustrated guide, supplier links, BOM search, pack counts and browser-local checklist persistence.
- A 390 px viewport check verified responsive navigation and guide layout; the narrow-screen camera framing was corrected.

Physical dimensions and hardware load ratings are still provisional as described in the README and guide. These checks do not certify structural safety or the physical installation sequence.
