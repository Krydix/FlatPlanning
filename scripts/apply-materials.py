"""Swap the flat's procedural colours for photographic textures; run in Blender background.
Textures come from source/textures (see CREDITS.md) and are projected in world space at real sizes, so
they need no UVs and survive the bake's atlas layout. Relief goes through a height-based bump rather
than a tangent-space normal map, because the bake's packed islands would scramble tangents. Everything
is baked into the atlases: the browser sees the result, not these materials. Running it again is safe.
"""
import bpy,math,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;TEX=ROOT/'source/textures'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
def image(name):
 path=TEX/(name+'.jpg')
 return bpy.data.images.load(str(path),check_existing=True) if path.exists() else None
def pbr(name,tex,size,bump=.15,distance=.002,tint=(1,1,1),gain=1,rotate=0,offset=(0,0),flat=False,saturation=1):
 """size = metres per tile. flat projects straight down; otherwise a box projection covers every face."""
 m=bpy.data.materials.get(name);img=image(tex)
 if not m or not img:return print('SKIP',name,tex,flush=True)
 m.use_nodes=True;t=m.node_tree;p=next(n for n in t.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled');out=next(n for n in t.nodes if n.bl_idname=='ShaderNodeOutputMaterial')
 for n in list(t.nodes):
  if n not in (p,out):t.nodes.remove(n)
 geo=t.nodes.new('ShaderNodeNewGeometry');mp=t.nodes.new('ShaderNodeMapping');tx=t.nodes.new('ShaderNodeTexImage');hsv=t.nodes.new('ShaderNodeHueSaturation');mix=t.nodes.new('ShaderNodeVectorMath');gray=t.nodes.new('ShaderNodeRGBToBW');bp=t.nodes.new('ShaderNodeBump')
 mp.inputs['Scale'].default_value=(1/size,1/size,1/size);mp.inputs['Rotation'].default_value=(0,0,math.radians(rotate));mp.inputs['Location'].default_value=(*offset,0)
 tx.image=img;tx.extension='REPEAT';tx.interpolation='Cubic'
 if not flat:tx.projection='BOX';tx.projection_blend=.12
 hsv.inputs['Saturation'].default_value=saturation;hsv.inputs['Value'].default_value=gain;mix.operation='MULTIPLY';mix.inputs[1].default_value=tint
 bp.inputs['Strength'].default_value=bump;bp.inputs['Distance'].default_value=distance
 l=t.links.new;l(geo.outputs['Position'],mp.inputs['Vector']);l(mp.outputs['Vector'],tx.inputs['Vector']);l(tx.outputs['Color'],hsv.inputs['Color']);l(hsv.outputs['Color'],mix.inputs[0]);l(mix.outputs['Vector'],p.inputs['Base Color'])
 l(tx.outputs['Color'],gray.inputs['Color']);l(gray.outputs['Val'],bp.inputs['Height']);l(bp.outputs['Normal'],p.inputs['Normal'])
# Pale oak, as photographed. Each plank family gets its own part of the texture so boards do not repeat.
for i,shade in enumerate((.94,1.0,.97,1.03,.99,1.05)):
 pbr(f'Floor oak {i}','oak_floor_albedo',.72,bump=.08,gain=shade,offset=(i*.37,i*.61),flat=True)
pbr('Oak for proposed furniture','oak_shelf_albedo',.75,bump=.08,saturation=.72,gain=1.08)
# Divider boards run across the room, so they need the grain turned with them.
across=bpy.data.materials.get('Oak for proposed furniture').copy() if bpy.data.materials.get('Oak across the room') is None else bpy.data.materials['Oak across the room'];across.name='Oak across the room'
for n in across.node_tree.nodes:
 if n.bl_idname=='ShaderNodeMapping':n.inputs['Rotation'].default_value=(0,0,math.radians(90))
pbr('Rental white matte','plaster_white_albedo',1.4,bump=.015,tint=(.98,.985,1),saturation=0)
# The curtains are blue-grey in the flat. The bed throw stays rust, so it needs its own material.
throw=bpy.data.materials.get('Bed throw rust') or bpy.data.materials['Rust textile'].copy();throw.name='Bed throw rust'
for o in bpy.data.objects:
 if o.name.startswith('Rust bed throw'):o.data.materials[0]=throw
pbr('Bed throw rust','curtain_fabric_albedo',.3,bump=.25,distance=.003,saturation=0,tint=(.95,.3,.16))
pbr('Rust textile','curtain_fabric_albedo',.35,bump=.25,distance=.003,tint=(.86,.95,1.16))
pbr('Petrol textile','duvet_fabric_albedo',.45,bump=.15)
pbr('KNAGGLIG untreated pale pine','pine_crate_albedo',.5,bump=.1)
pbr('Balcony composite decking','decking_albedo',.56,bump=.6,distance=.005,flat=True,gain=.55)
pbr('Balcony concrete slab','concrete_albedo',1.2,bump=.1,gain=.8)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
print('MATERIALS_APPLIED',flush=True)
