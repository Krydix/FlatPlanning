"""Render full-material 360-degree Cycles photographs of the locked room."""
import bpy,json,math,time,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'public/panoramas';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/flat-v18.blend'))
scene=bpy.context.scene;scene.frame_set(1)
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=256
scene.cycles.use_denoising=True;scene.cycles.denoiser='OPENIMAGEDENOISE'
scene.cycles.seed=0;scene.cycles.max_bounces=12;scene.cycles.diffuse_bounces=6
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='METAL';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='METAL'
for obj in scene.objects:
 if obj.type=='LIGHT' and 'ceiling' in obj.name.lower():obj.data.energy=0
scene.render.resolution_x=6144;scene.render.resolution_y=3072;scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.render.image_settings.file_format='JPEG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.quality=94
camera=bpy.data.objects.new('WEB Cycles 360 camera',bpy.data.cameras.new('WEB Cycles 360 camera'))
scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='PANO';camera.data.panorama_type='EQUIRECTANGULAR'
# Image centre faces Blender +Y (Three.js -Z); the image top is world up.
camera.rotation_euler=(math.pi/2,0,0)
records=[]
for key,label,position in [
 ('entrance','Entrance',(2.93,-.42,1.55)),
 ('desk','Workstation',(1.58,2.1125,1.43)),
 ('wardrobe','Wardrobe',(1.52,3.85,1.55)),
]:
 camera.location=position;scene.render.filepath=str(OUT/(key+'.jpg'))
 start=time.time();print('PANORAMA_START',key,flush=True)
 bpy.ops.render.render(write_still=True)
 path=Path(scene.render.filepath)
 records.append({'id':key,'label':label,'file':'panoramas/'+path.name,
  'position_blender_m':list(position),'width':6144,'height':3072,
  'render_seconds':round(time.time()-start,1),'bytes':path.stat().st_size,
  'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 print('PANORAMA_DONE',key,records[-1]['render_seconds'],flush=True)
manifest={'engine':'Cycles','projection':'equirectangular','samples':256,
 'denoiser':'OPENIMAGEDENOISE','ceiling_light_on':False,'full_materials':True,
 'blender_version':bpy.app.version_string,
 'source_sha256':hashlib.sha256((ROOT/'source/flat-v18.blend').read_bytes()).hexdigest(),
 'lights':[{'name':o.name,'watts':o.data.energy} for o in scene.objects if o.type=='LIGHT' and not o.hide_render],
 'view_transform':scene.view_settings.view_transform,'exposure':scene.view_settings.exposure,
 'display_referred':True,'panoramas':records}
(ROOT/'public/data/panoramas.json').write_text(json.dumps(manifest,indent=2)+'\n')
runpy.run_path(str(ROOT/'scripts/prepare-panoramas.py'),run_name='__main__')
manifest=json.loads((ROOT/'public/data/panoramas.json').read_text())
print('PANORAMAS_COMPLETE',json.dumps(manifest),flush=True)
