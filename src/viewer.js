import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
const asset = path => new URL(path, document.baseURI).href;
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
// Interior air volumes (main room, hall, bathroom) in viewer coordinates: x, height, -y.
// The cutaway keeps walls and windows whenever the camera stands inside one of them.
export const interiorFor=(ceiling=2.63)=>[[[0,0,-5.3],[3.45,ceiling,0]],[[2.2,0,.1],[3.45,ceiling,3.2]],[[0,0,.3],[2.1,ceiling,3.05]]].map(([a,b])=>new THREE.Box3(new THREE.Vector3(...a),new THREE.Vector3(...b)));
export const INTERIOR=interiorFor();
const pixelRatio=()=>Math.min(window.devicePixelRatio||1,1.75);
const formatLength=mm=>mm>=1000?`${(mm/1000).toFixed(2)} m`:`${(mm/10).toFixed(1)} cm`;
const BASIS={measured:'measured',assumed:'assumed',preview:'preview fitting profile',model:'model, from assumed room'};
const VIEWS = {
 overview: {position:[8.0,7.2,4.8],target:[1.7,.85,-1.05],fov:43},
 entrance: {position:[2.93,1.55,.42],target:[2.60,1.10,-1.68],fov:73},
 desk: {position:[1.58,1.43,-2.1125],target:[3.20,1.35,-2.1125],fov:62},
 wardrobe: {position:[1.52,1.55,-3.85],target:[3.22,1.43,-4.15],fov:65},
 equipment: {position:[2.00,.56,-2.1125],target:[3.29,.56,-2.1125],fov:90},
 joints: {position:[2.58,.50,-.94],target:[3.11,.48,-1.30],fov:68},
 plan: {position:[1.72,10.8,-1.4],target:[1.72,0,-1.4],fov:49},
};
export function rendererFor(element,background){
 // Baked atlases are already display-referred (Blender view transform applied at bake time).
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(pixelRatio());renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NoToneMapping;
 renderer.setClearColor(background);renderer.domElement.tabIndex=0;element.appendChild(renderer.domElement);return renderer;
}
export function loopViewer(renderer,scene,camera,controls,container,labels,onResize){
 // Frames are requested only while something changes: damping, a preset move or a redraw.
 let dirty=true;let enabled=true;let lost=false;let frame=0;
 const size=()=>{const box=container.getBoundingClientRect();if(box.width<1||box.height<1)return;renderer.setPixelRatio(pixelRatio());renderer.setSize(box.width,box.height);if(labels)labels.setSize(box.width,box.height);camera.aspect=box.width/box.height;onResize?.();camera.updateProjectionMatrix();wake();};
 const tick=()=>{frame=0;if(!enabled||lost)return;const moving=controls.update();if(moving||dirty){renderer.render(scene,camera);if(labels)labels.render(scene,camera);dirty=false;}if(moving)wake(false);};
 function wake(redraw=true){if(redraw)dirty=true;if(!frame&&enabled&&!lost)frame=requestAnimationFrame(tick);}
 const ro=new ResizeObserver(size);ro.observe(container);window.addEventListener('resize',size);controls.addEventListener('change',()=>wake());controls.addEventListener('start',()=>wake());
 const canvas=renderer.domElement;canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();lost=true;if(frame)cancelAnimationFrame(frame);frame=0;});canvas.addEventListener('webglcontextrestored',()=>{lost=false;wake();});
 size();
 return {size,draw(){wake();},enable(value){enabled=value;if(value)size();else if(frame){cancelAnimationFrame(frame);frame=0;}},dispose(){if(frame)cancelAnimationFrame(frame);ro.disconnect();window.removeEventListener('resize',size);renderer.dispose();}};
}
function watchContext(renderer,onLost,onRestored){const canvas=renderer.domElement;canvas.addEventListener('webglcontextlost',()=>onLost?.());canvas.addEventListener('webglcontextrestored',()=>onRestored?.());}
export class RoomViewer {
 constructor(container,{onProgress,onReady,onError,onCutaway,onContextLost,onContextRestored,onMeasure,dimensions=[],ceiling}={}){
  this.container=container;this.onCutaway=onCutaway;this.onError=onError;this.onMeasure=onMeasure;this.cutaway=true;this.currentView='overview';this.scene=new THREE.Scene();this.interior=ceiling?interiorFor(ceiling):INTERIOR;
  this.camera=new THREE.PerspectiveCamera(43,1,.02,100);this.renderer=rendererFor(container,0xe8eadf);watchContext(this.renderer,onContextLost,()=>{onContextRestored?.();this.runner.draw();});
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.1;this.controls.minDistance=.35;this.controls.maxDistance=21;this.controls.maxPolarAngle=Math.PI*.52;
  this.controls.addEventListener('start',()=>{this.animation=null;});
  this.controls.addEventListener('change',()=>this.updateCutaway());
  this.labels=new CSS2DRenderer();this.labels.domElement.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:2';container.appendChild(this.labels.domElement);
  this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container,this.labels,()=>{this.camera.fov=this.responsiveFov(VIEWS[this.currentView]?.fov||43);});
  this.dimensionGroup=new THREE.Group();this.dimensionGroup.visible=false;this.scene.add(this.dimensionGroup);this.addDimensions(dimensions);this.setView('overview',true);
  this.measureGroup=new THREE.Group();this.scene.add(this.measureGroup);this.measurePoints=[];this.measuring=false;this.bindMeasure();
  // KTX2 atlases stay GPU-compressed (UASTC/ETC1S → ASTC/BC7/ETC2), with full mip chains.
  this.ktx2=new KTX2Loader().setTranscoderPath(asset('basis/')).detectSupport(this.renderer);
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);loader.setKTX2Loader(this.ktx2);
  loader.load(asset('models/flat-baked.glb?bake=v19-speakers'),gltf=>{
   this.model=gltf.scene;this.scene.add(this.model);
   this.model.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=false;const mats=Array.isArray(o.material)?o.material:[o.material];for(const m of mats){m.toneMapped=false;if(m.map)m.map.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());if(o.name==='flat_glass'){m.transparent=true;m.opacity=.10;m.depthWrite=false;m.side=THREE.DoubleSide;}}}});
   this.setCutaway(this.cutaway);this.runner.draw();onReady?.();
  },event=>{if(event.total)onProgress?.(Math.round(event.loaded/event.total*100));},error=>{console.error('Room model load failed',error);onError?.(error);});
 }
 responsiveFov(fov){return Math.min(105,2*Math.atan(Math.tan(fov*Math.PI/360)*Math.max(1,1.25/this.camera.aspect))*180/Math.PI);}
 addDimensions(dimensions){
  // Solid green only for site measurements; everything assumed or derived is dashed amber.
  const point=([x,y,z])=>new THREE.Vector3(x/1000,z/1000,-y/1000);
  for(const d of dimensions){
   const a=point(d.a),b=point(d.b),measured=d.basis==='measured';
   const material=measured?new THREE.LineBasicMaterial({color:0x4d7a3a,depthTest:false,transparent:true,opacity:.95,toneMapped:false}):new THREE.LineDashedMaterial({color:0xb7791f,dashSize:.04,gapSize:.03,depthTest:false,transparent:true,opacity:.95,toneMapped:false});
   const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([a,b]),material);line.computeLineDistances();line.renderOrder=10;this.dimensionGroup.add(line);
   const el=document.createElement('span');el.className='dimension-label'+(measured?'':' unverified');el.textContent=`${d.label} ${formatLength(d.value)}${measured?'':' · '+(BASIS[d.basis]||d.basis)}`;
   const label=new CSS2DObject(el);label.position.copy(a).lerp(b,.5);this.dimensionGroup.add(label);
  }
 }
 bindMeasure(){
  // Click two surfaces to measure; a press that drags is an orbit and is ignored.
  const canvas=this.renderer.domElement;let down=null;const ray=new THREE.Raycaster();
  canvas.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
  canvas.addEventListener('pointerup',e=>{if(!this.measuring||!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5||!this.model)return;const box=canvas.getBoundingClientRect();
   ray.setFromCamera(new THREE.Vector2((e.clientX-box.left)/box.width*2-1,-(e.clientY-box.top)/box.height*2+1),this.camera);
   const hit=ray.intersectObject(this.model,true).find(h=>{for(let o=h.object;o;o=o.parent)if(!o.visible)return false;return true;});if(hit)this.addMeasurePoint(hit.point);});
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&this.measuring)this.clearMeasure();});
 }
 addMeasurePoint(p){
  if(this.measurePoints.length===2)this.clearMeasure();this.measurePoints.push(p.clone());
  const dot=new THREE.Mesh(new THREE.SphereGeometry(.012,12,8),new THREE.MeshBasicMaterial({color:0x2b4430,depthTest:false,toneMapped:false}));dot.position.copy(p);dot.renderOrder=11;this.measureGroup.add(dot);
  if(this.measurePoints.length===2){const [a,b]=this.measurePoints;const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([a,b]),new THREE.LineBasicMaterial({color:0x2b4430,depthTest:false,toneMapped:false}));line.renderOrder=11;this.measureGroup.add(line);
   const mm=a.distanceTo(b)*1000;const el=document.createElement('span');el.className='dimension-label measure';el.textContent=`${Math.round(mm)} mm · model`;const label=new CSS2DObject(el);label.position.copy(a).lerp(b,.5);this.measureGroup.add(label);this.onMeasure?.(mm);}
  this.runner.draw();
 }
 clearMeasure(){for(const o of [...this.measureGroup.children]){this.measureGroup.remove(o);o.geometry?.dispose();o.material?.dispose();o.element?.remove();}this.measurePoints=[];this.onMeasure?.(null);this.runner.draw();}
 setMeasuring(value){this.measuring=value;if(!value)this.clearMeasure();this.container.classList.toggle('measuring',value);}
 setDimensions(value){this.dimensionGroup.visible=value;this.runner.draw();}
 updateCutaway(){
  if(!this.model)return;
  // The same rule runs during hand orbit and preset motion. Inside the flat,
  // retain the baked walls, ceiling and outside view; only outside views remove the shell.
  const inside=(this.interior||INTERIOR).some(box=>box.containsPoint(this.camera.position));
  this.model.traverse(o=>{const category=o.userData.category;
   if(['shell','ceiling','glass','exterior'].includes(category))o.visible=!this.cutaway||inside;
   if(category==='chair')o.visible=this.currentView!=='equipment';
  });
 }
 setCutaway(value){this.cutaway=value;this.updateCutaway();this.onCutaway?.(value);this.runner.draw();}
 setView(name,immediate=false){
  // Presets move the same camera through the same baked model. Preserve the
  // cutaway preference and never change materials or lights here.
  const view=VIEWS[name]||VIEWS.overview;this.currentView=name;this.controls.enablePan=true;
  const from=this.camera.position.clone(),fromTarget=this.controls.target.clone(),to=new THREE.Vector3(...view.position),toTarget=new THREE.Vector3(...view.target),oldFov=this.camera.fov;
  const token={};this.animation=token;const start=performance.now();
  const move=time=>{if(this.animation!==token)return;const t=(immediate||reduced)?1:Math.min((time-start)/750,1);const k=1-Math.pow(1-t,3);this.camera.position.lerpVectors(from,to,k);this.controls.target.lerpVectors(fromTarget,toTarget,k);this.camera.fov=THREE.MathUtils.lerp(oldFov,this.responsiveFov(view.fov),k);this.camera.updateProjectionMatrix();this.controls.update();this.updateCutaway();this.runner.draw();if(t<1)requestAnimationFrame(move);};move(start);
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
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);loader.load(asset('models/assembly.glb?design=v19-speakers'),gltf=>{
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
