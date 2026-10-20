import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
const asset = path => new URL(path, document.baseURI).href;
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const VIEWS = {
 overview: {position:[8.0,7.2,4.8],target:[1.7,.85,-1.05],fov:43},
 entrance: {position:[2.93,1.55,.42],target:[2.60,1.10,-1.68],fov:73},
 desk: {position:[1.58,1.43,-2.1125],target:[3.20,1.35,-2.1125],fov:62},
 wardrobe: {position:[1.52,1.55,-3.85],target:[3.22,1.43,-4.15],fov:65},
 plan: {position:[1.72,10.8,-1.4],target:[1.72,0,-1.4],fov:49},
};
export function rendererFor(element,background){
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.75));renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.toneMapping=THREE.AgXToneMapping;renderer.toneMappingExposure=1.15;
 renderer.setClearColor(background);renderer.domElement.tabIndex=0;element.appendChild(renderer.domElement);return renderer;
}
export function limitTextureSize(texture,limit){
 const image=texture.image;if(!image||Math.max(image.width,image.height)<=limit)return;
 const scale=limit/Math.max(image.width,image.height),canvas=document.createElement('canvas');
 canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);
 const context=canvas.getContext('2d');if(!context)return;
 context.drawImage(image,0,0,canvas.width,canvas.height);texture.image=canvas;texture.needsUpdate=true;
}
export function loopViewer(renderer,scene,camera,controls,container,labels,onResize){
 let dirty=true;let enabled=true;let frame;
 const size=()=>{const box=container.getBoundingClientRect();if(box.width<1||box.height<1)return;renderer.setSize(box.width,box.height);if(labels)labels.setSize(box.width,box.height);camera.aspect=box.width/box.height;onResize?.();camera.updateProjectionMatrix();dirty=true;};
 const ro=new ResizeObserver(size);ro.observe(container);controls.addEventListener('change',()=>{dirty=true;});
 const tick=()=>{frame=requestAnimationFrame(tick);if(!enabled)return;if(controls.update()||dirty){renderer.render(scene,camera);if(labels)labels.render(scene,camera);dirty=false;}};tick();size();
 return {size,draw(){dirty=true;},enable(value){enabled=value;if(value)size();},dispose(){cancelAnimationFrame(frame);ro.disconnect();renderer.dispose();}};
}
export class RoomViewer {
 constructor(container,{onProgress,onReady,onError,onCutaway}={}){
  this.container=container;this.onCutaway=onCutaway;this.onError=onError;this.cutaway=true;this.currentView='overview';this.scene=new THREE.Scene();
  this.camera=new THREE.PerspectiveCamera(43,1,.02,100);this.renderer=rendererFor(container,0xe8eadf);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.1;this.controls.minDistance=.35;this.controls.maxDistance=21;this.controls.maxPolarAngle=Math.PI*.52;
  this.controls.addEventListener('start',()=>{this.animation=null;});
  this.controls.addEventListener('change',()=>this.updateCutaway());
  this.labels=new CSS2DRenderer();this.labels.domElement.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:2';container.appendChild(this.labels.domElement);
  this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container,this.labels,()=>{this.camera.fov=this.responsiveFov(VIEWS[this.currentView]?.fov||43);});
  this.dimensionGroup=new THREE.Group();this.dimensionGroup.visible=false;this.scene.add(this.dimensionGroup);this.addDimensions();this.setView('overview',true);
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);
  loader.load(asset('models/flat-baked.glb?bake=cycles128-4k-v2'),gltf=>{
   this.model=gltf.scene;this.scene.add(this.model);const atlasLimit=window.matchMedia('(pointer: coarse)').matches||container.clientWidth<600?2048:4096;
   this.model.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=false;const mats=Array.isArray(o.material)?o.material:[o.material];for(const m of mats){m.toneMapped=true;if(m.map){limitTextureSize(m.map,atlasLimit);m.map.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());}if(o.name==='flat_glass'){m.transparent=true;m.opacity=.10;m.depthWrite=false;m.side=THREE.DoubleSide;}}}});
   this.shellBounds=new THREE.Box3();this.model.traverse(o=>{if(o.isMesh&&o.userData.category==='shell')this.shellBounds.expandByObject(o);});
   this.setCutaway(this.cutaway);this.runner.draw();onReady?.();
  },event=>{if(event.total)onProgress?.(Math.round(event.loaded/event.total*100));},error=>{console.error('Room model load failed',error);onError?.(error);});
 }
 responsiveFov(fov){return Math.min(105,2*Math.atan(Math.tan(fov*Math.PI/360)*Math.max(1,1.25/this.camera.aspect))*180/Math.PI);}
 addDimensions(){
  const line=(a,b,text,label)=>{const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...a),new THREE.Vector3(...b)]);this.dimensionGroup.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0x6b8c4e,depthTest:false,transparent:true,opacity:.9})));const el=document.createElement('span');el.className='dimension-label';el.textContent=text;const object=new CSS2DObject(el);object.position.set(...label);this.dimensionGroup.add(object);};
  line([0,.05,-5.55],[3.45,.05,-5.55],'3.45 m',[1.725,.06,-5.55]);
  line([-.22,.05,0],[-.22,.05,-5.30],'5.30 m',[-.22,.06,-2.65]);
  line([2.410,.78,-.735],[2.703,.78,-1.305],'64.1 cm entry',[2.53,.9,-1.00]);
  line([2.70,0,-2.02],[2.70,.732,-2.02],'73.2 cm',[2.64,.39,-2.02]);
 }
 setDimensions(value){this.dimensionGroup.visible=value;this.runner.draw();}
 updateCutaway(){
  if(!this.model)return;
  // The same rule runs during hand orbit and preset motion. Inside the flat,
  // retain the baked walls/ceiling; only outside views need the shell removed.
  const inside=this.shellBounds?.containsPoint(this.camera.position);
  this.model.traverse(o=>{const category=o.userData.category;
   if(['shell','ceiling','glass'].includes(category))o.visible=!this.cutaway||inside;
   if(category==='exterior')o.visible=!this.cutaway;
  });
 }
 setCutaway(value){this.cutaway=value;this.updateCutaway();this.onCutaway?.(value);this.runner.draw();}
 setView(name,immediate=false){
  // Presets move the same camera through the same baked model. Preserve the
  // cutaway preference and never change materials or lights here.
  const view=VIEWS[name]||VIEWS.overview;this.currentView=name;this.controls.enablePan=true;
  const from=this.camera.position.clone(),fromTarget=this.controls.target.clone(),to=new THREE.Vector3(...view.position),toTarget=new THREE.Vector3(...view.target),oldFov=this.camera.fov;
  const token={};this.animation=token;const start=performance.now();
  const move=time=>{if(this.animation!==token)return;const t=(immediate||reduced)?1:Math.min((time-start)/750,1);const k=1-Math.pow(1-t,3);this.camera.position.lerpVectors(from,to,k);this.controls.target.lerpVectors(fromTarget,toTarget,k);this.camera.fov=THREE.MathUtils.lerp(oldFov,this.responsiveFov(view.fov),k);this.camera.updateProjectionMatrix();this.controls.update();this.runner.draw();if(t<1)requestAnimationFrame(move);};move(start);
 }
 resize(){this.runner.size();}
 setEnabled(value){this.runner.enable(value);}
}
export class AssemblyViewer {
 constructor(container,onReady,onError){
  this.container=container;this.scene=new THREE.Scene();this.camera=new THREE.PerspectiveCamera(39,1,.02,70);this.renderer=rendererFor(container,0xfbfcf7);this.renderer.toneMapping=THREE.NoToneMapping;
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.minDistance=.25;this.controls.maxDistance=12;this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container);
  this.materials={active:new THREE.MeshBasicMaterial({color:0x344b38}),wood:new THREE.MeshBasicMaterial({color:0xe2dfd0}),context:new THREE.MeshBasicMaterial({color:0xe4e8df}),initial:new THREE.MeshBasicMaterial({color:0xa6b69b})};
  this.edgeMaterial=new THREE.LineBasicMaterial({color:0x18281b});this.meshes=[];
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);loader.load(asset('models/assembly.glb'),gltf=>{
   this.model=gltf.scene;this.scene.add(this.model);this.model.traverse(o=>{if(!o.isMesh)return;let p=o;while(p&&!p.userData.part_id)p=p.parent;const id=p?.userData.part_id;if(!id)return;o.userData.componentId=id;o.userData.componentKind=p.userData.catalog_kind;const edge=new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry,38),this.edgeMaterial);o.add(edge);o.userData.edge=edge;this.meshes.push(o);});this.ready=true;onReady?.();
  },undefined,e=>{console.error('Assembly model load failed',e);onError?.(e);});
 }
 select(stage,stages){if(!this.ready){this.pending={stage,stages};return;}const active=new Set(stage.parts),seen=new Set(stages.filter(s=>s.id<=stage.id).flatMap(s=>s.parts));const showAll=stage.id<=2||stage.id>=18;const box=new THREE.Box3();let hasFocus=false;
  for(const mesh of this.meshes){const id=mesh.userData.componentId;const selected=active.has(id);mesh.visible=showAll||seen.has(id);mesh.material=selected?(mesh.userData.componentKind==='wood'?this.materials.wood:this.materials.active):showAll?this.materials.initial:this.materials.context;mesh.userData.edge.visible=selected||showAll;if(selected){box.expandByObject(mesh);hasFocus=true;}}
  if(!hasFocus)box.setFromObject(this.model);const centre=box.getCenter(new THREE.Vector3());const size=box.getSize(new THREE.Vector3());const distance=Math.max(size.x,size.y,size.z,1.15)*1.55*Math.max(1,1.2/this.camera.aspect);this.controls.target.copy(centre);this.camera.position.copy(centre).add(new THREE.Vector3(-1.5,.9,1.15).normalize().multiplyScalar(distance));this.controls.update();this.runner.size();this.runner.draw();
 }
 setEnabled(value){this.runner.enable(value);}
 resize(){this.runner.size();}
}
