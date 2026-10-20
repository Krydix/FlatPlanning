"""Rebuild the connected desk joints from the graph; run in Blender background."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import build,profile_from_measurements
from blender_components import rebuild,model_errors
from blender_equipment import rebuild_equipment
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
a=build(profile_from_measurements(ROOT/'source/Measurements-v8.json'),shared_desk=True);assert not a.validate()['geometry_errors'];a.save(ROOT/'source/assembly.json')
fixed={o.name:tuple(v for row in o.matrix_world for v in row) for o in bpy.context.scene.objects if o.name!='Audio interface' and not o.get('service_equipment') and not any(c.name.startswith('13 ') for c in o.users_collection)}
rebuild(a);rebuild_equipment(ROOT);assert not model_errors(a),model_errors(a)
assert all(tuple(v for row in bpy.data.objects[name].matrix_world for v in row)==matrix for name,matrix in fixed.items())
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
for t in bpy.data.texts:
 if t.name.startswith('Assembly'):t.clear();t.write((ROOT/'source/assembly.json').read_text())
bpy.context.scene['desk_joint_revision']='Four-way threaded desk crosses and offset low front T braces'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('JOINTS_REBUILT',len(a.parts),flush=True)
