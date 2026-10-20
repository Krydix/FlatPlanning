"""Refresh the room's loading image from the current Blender model."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=96;s.cycles.use_denoising=True
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
for d in p.devices:d.use=d.type=='METAL'
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
s.camera=bpy.data.objects['01 Entrance perspective'];s.render.resolution_x=1600;s.render.resolution_y=1150;s.render.resolution_percentage=100
s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=94;s.render.filepath=str(ROOT/'public/images/room.jpg');bpy.ops.render.render(write_still=True)
print('ROOM_POSTER_RENDERED',flush=True)
