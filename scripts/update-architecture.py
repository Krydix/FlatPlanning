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
ceiling.name='Ceiling slab';ceiling['height_basis']='measured' if GEO['ceiling_measured'] else 'assumed';ceiling['height_mm']=GEO['ceiling']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('ARCHITECTURE_FITTED',f'ceiling {old*1000:.0f} -> {new*1000:.0f} mm','measured' if GEO['ceiling_measured'] else 'assumed',flush=True)
