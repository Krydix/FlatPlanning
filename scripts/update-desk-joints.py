"""Rebuild the connected desk joints from the graph; run in Blender background."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import build,profile_from_measurements
from blender_components import rebuild,model_errors
from blender_equipment import rebuild_equipment,REPLACED
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
a=build(profile_from_measurements(ROOT/'source/Measurements-v8.json'),shared_desk=True);assert not a.validate()['geometry_errors'];a.save(ROOT/'source/assembly.json')
# Under-bed boxes are resized below; everything else outside the graph must stay exactly where it was.
def underbed(o):return o.name.startswith(('Crate slat','Crate end slat')) and any(c.name.startswith('05 ') for c in o.users_collection)
fixed={o.name:tuple(v for row in o.matrix_world for v in row) for o in bpy.context.scene.objects if o.name not in REPLACED and not o.get('service_equipment') and not underbed(o) and not any(c.name.startswith('13 ') for c in o.users_collection)}
rebuild(a);rebuild_equipment(ROOT);assert not model_errors(a),model_errors(a)
assert all(tuple(v for row in bpy.data.objects[name].matrix_world for v in row)==matrix for name,matrix in fixed.items())
# Under-bed boxes slide out beneath the 250 mm side beam: three 40 mm slat rows, top 230 mm incl. casters.
ROWS=((.100,.095),(.165,.1525),(.230,.210))
for o in bpy.data.objects:
 if not underbed(o):continue
 old,new=min(ROWS,key=lambda r:min(abs(o.location.z-r[0]),abs(o.location.z-r[1])))
 zs=[v.co.z for v in o.data.vertices];o.location.z=new;o.scale.z=.040/(max(zs)-min(zs))
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
for t in bpy.data.texts:
 if t.name.startswith('Assembly'):t.clear();t.write((ROOT/'source/assembly.json').read_text())
bpy.context.scene['desk_joint_revision']='Four-way threaded desk crosses, rounded entrance corner, ear-aimed speakers'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('JOINTS_REBUILT',len(a.parts),flush=True)
