"""Check the actual rebuilt desktop mesh against pipe/fitting envelopes."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import Assembly
from blender_components import model_errors
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
a=Assembly.load(ROOT/'source/assembly.json');assert not model_errors(a),model_errors(a)
dg=bpy.context.evaluated_depsgraph_get()
def tree(o):
 eo=o.evaluated_get(dg);me=eo.to_mesh();v=[eo.matrix_world@p.co for p in me.vertices];polys=[list(p.vertices) for p in me.polygons];t=BVHTree.FromPolygons(v,polys);eo.to_mesh_clear();return t
def bounds(o):
 p=[o.matrix_world@Vector(v) for v in o.bound_box];return [(min(v[i] for v in p),max(v[i] for v in p)) for i in range(3)]
clashes=[]
for bid in ('Desk.top','Desk.service_shelf'):
 board=next(o for o in bpy.data.objects[bid].children if o.type=='MESH');bt=tree(board);bb=bounds(board)
 for o in bpy.data.collections['13 V8 - component assembly'].objects:
  if o.type!='MESH' or not o.parent:continue
  k=o.parent.get('catalog_kind','')
  if not k.startswith('tube_') and k not in ('cross','slide_tee','elbow','extension','cap','flange'):continue
  ob=bounds(o)
  if all(min(x[1],y[1])-max(x[0],y[0])>.00005 for x,y in zip(bb,ob)) and bt.overlap(tree(o)):clashes.append([bid,o.name])
assert not clashes,clashes
assert 'Audio interface' not in bpy.data.objects
print('BLENDER_JOINT_CHECK_PASSED',len(a.parts),'parts; no pipe/fitting intersections with desktop or service shelf; old tabletop interface removed',flush=True)
