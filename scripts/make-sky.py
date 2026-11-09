"""Render the baking HDRI into the display-referred panorama the viewer shows; run in Blender background.
It uses the scene's own world and view transform, so the sky outside matches the baked balcony.
"""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=8;s.cycles.use_denoising=False
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
for d in p.devices:d.use=d.type=='METAL'
for o in s.objects:
 if o.type!='CAMERA':o.hide_render=True
cam=bpy.data.objects.new('Sky camera',bpy.data.cameras.new('Sky camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='PANO';cam.data.panorama_type='EQUIRECTANGULAR';cam.location=(1.4,6,3.5);cam.rotation_euler=(1.5707963,0,0)
s.render.resolution_x=4096;s.render.resolution_y=2048;s.render.resolution_percentage=100;s.render.film_transparent=False;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.filepath=str(ROOT/'.cache/sky.png');bpy.ops.render.render(write_still=True)
print('SKY_RENDERED',flush=True)
