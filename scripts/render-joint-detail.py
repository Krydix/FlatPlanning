"""Render the corrected stock desk connections without changing the source scene."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
scene=bpy.context.scene
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'ceiling' in o.name.lower():o.data.energy=0
 if o.name.startswith('Chair'):o.hide_render=True
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=96;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='METAL'
data=bpy.data.cameras.new('Desk joint detail');cam=bpy.data.objects.new('Desk joint detail',data);scene.collection.objects.link(cam)
cam.location=(2.10,2.1125,.56);target=Vector((3.29,2.1125,.56));cam.rotation_euler=(target-Vector(cam.location)).to_track_quat('-Z','Y').to_euler();data.lens=15;data.clip_start=.01;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=94;scene.render.filepath=str(ROOT/'public/images/desk-support.jpg')
bpy.ops.render.render(write_still=True)
print('JOINT_DETAIL_RENDERED',flush=True)
