import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { rendererFor,loopViewer,limitTextureSize } from './viewer.js';

// These are full Cycles photographs, already transformed to display sRGB by
// Blender. Do not apply a second exposure, tone map, or any runtime lighting.
export class PanoramaViewer {
 constructor(container,{onLoading,onReady,onError,onView}={}){
  this.container=container;this.onLoading=onLoading;this.onReady=onReady;this.onError=onError;this.onView=onView;
  this.cache=new Map();this.scene=new THREE.Scene();
  this.renderer=rendererFor(container,0x20241d);this.renderer.toneMapping=THREE.NoToneMapping;this.renderer.toneMappingExposure=1;
  this.camera=new THREE.PerspectiveCamera(72,1,.001,100);
  this.camera.position.set(0,0,.01);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);
  this.controls.enablePan=false;this.controls.enableZoom=false;this.controls.rotateSpeed=-.35;
  this.controls.enableDamping=true;this.controls.dampingFactor=.1;
  this.controls.minPolarAngle=.02;this.controls.maxPolarAngle=Math.PI-.02;
  const sphere=new THREE.SphereGeometry(30,96,64);sphere.scale(-1,1,1);
  this.material=new THREE.MeshBasicMaterial({toneMapped:false});
  this.sphere=new THREE.Mesh(sphere,this.material);this.sphere.rotation.y=-Math.PI/2;
  this.scene.add(this.sphere);
  this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container,null,()=>{
   this.camera.fov=this.camera.aspect<.8?88:72;
  });
 }
 async setView(name){
  if(!['entrance','desk','wardrobe'].includes(name))name='entrance';
  const token={};this.loading=token;this.onLoading?.(name);
  try{
   let promise=this.cache.get(name);
   if(!promise){promise=new THREE.TextureLoader().loadAsync(new URL(`panoramas/${name}.jpg?render=cycles256-v1`,document.baseURI).href);this.cache.set(name,promise);}
   const texture=await promise;if(this.loading!==token)return;
   texture.colorSpace=THREE.SRGBColorSpace;
   if(window.matchMedia('(pointer: coarse)').matches||this.container.clientWidth<600)limitTextureSize(texture,4096);
   texture.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());
   this.material.map=texture;this.material.needsUpdate=true;
   // Retain only the current panorama on the GPU. HTTP caching still makes
   // revisiting positions quick, without holding three 6K textures in memory.
   for(const [key,cached] of this.cache)if(key!==name){this.cache.delete(key);cached.then(t=>{if(t!==this.material.map)t.dispose();},()=>{});}
   // Match the interior directions of the freely movable room camera.
   const direction=name==='entrance'?new THREE.Vector3(-.33,-.45,-2.1):name==='desk'?new THREE.Vector3(1.62,-.08,0):new THREE.Vector3(1.70,-.12,-.30);
   this.controls.reset();this.controls.target.set(0,0,0);
   this.camera.position.copy(direction.normalize().multiplyScalar(-.01));
   this.controls.update();this.currentView=name;this.runner.size();this.runner.draw();
   this.onView?.(name);this.onReady?.(name);
  }catch(error){if(this.loading===token){this.cache.delete(name);this.onError?.(error);}}
 }
 setEnabled(value){this.runner.enable(value);}
 resize(){this.runner.size();}
}
