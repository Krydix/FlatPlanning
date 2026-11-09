"""Fit the Blender architecture to source/room-measurements.json; run in Blender background.
Only the ceiling height is applied so far: wall tops, lintels and the slab move to the
measured plane, and ceiling-mounted fittings move with it. Hanging pendants keep their
height above the bar and their cables are extended. Running it again is a no-op.
"""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import room_geometry
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
GEO=room_geometry();ceiling=next(o for o in bpy.data.objects if any(c.name.startswith('09 ') for c in o.users_collection) and o.name.startswith('Ceiling') and 'lamp' not in o.name)
old=min((ceiling.matrix_world@v.co).z for v in ceiling.data.vertices);new=GEO['ceiling']/1000;delta=new-old
def lift(o,test):
 # Move world-space vertices that satisfy test(z) by delta, keeping the object transform.
 m=o.matrix_world;inv=m.inverted()
 for v in o.data.vertices:
  w=m@v.co
  if test(w.z):w.z+=delta;v.co=inv@w
 o.data.update()
if abs(delta)>1e-6:
 for o in bpy.data.objects:
  cols=[c.name for c in o.users_collection]
  if o.type=='MESH' and any(c.startswith('01 ') for c in cols):lift(o,lambda z:abs(z-old)<.0006)
  elif o.type=='MESH' and any(c.startswith('09 ') for c in cols):o.location.z+=delta
  elif o.type=='MESH' and o.name.startswith('Pendant cable'):lift(o,lambda z:z>old-.02)
  elif o.type=='LIGHT' and o.name.startswith('V9') and 'ceiling' in o.name.lower():o.location.z+=delta
# Floors run under the walls so no slit shows the background, and meet inside the door openings.
# The hall and bathroom rise to the wall feet; the main slab stays 5 mm down, below the parquet.
FLOORS={'Main room floor':(-.010,3.460,-.012,5.330,-.005),'Hall floor':(2.150,3.460,-3.225,.012,0),'Bathroom shell floor - fixtures unknown':(-.010,2.150,-3.210,-.290,0)}
for name,(x0,x1,y0,y1,top) in FLOORS.items():
 o=bpy.data.objects[name];m=o.matrix_world;inv=m.inverted();world=[m@v.co for v in o.data.vertices];lo=[min(w[i] for w in world) for i in range(3)];hi=[max(w[i] for w in world) for i in range(3)]
 for v,w in zip(o.data.vertices,world):
  w.x=x0 if abs(w.x-lo[0])<abs(w.x-hi[0]) else x1;w.y=y0 if abs(w.y-lo[1])<abs(w.y-hi[1]) else y1
  if abs(w.z-hi[2])<abs(w.z-lo[2]):w.z=top
  v.co=inv@w
 o.data.update()
ceiling.name='Ceiling slab';ceiling['height_basis']='measured' if GEO['ceiling_measured'] else 'assumed';ceiling['height_mm']=GEO['ceiling']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('ARCHITECTURE_FITTED',f'ceiling {old*1000:.0f} -> {new*1000:.0f} mm','measured' if GEO['ceiling_measured'] else 'assumed',flush=True)
