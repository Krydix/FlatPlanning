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
// Slider values are horizontal degrees, as in games, so window shape never changes the setting.
export const FOV_RANGE=[40,130];
export const horizontalFov=(vertical,aspect)=>2*Math.atan(Math.tan(vertical*Math.PI/360)*aspect)*180/Math.PI;
export const verticalFov=(horizontal,aspect)=>Math.min(140,2*Math.atan(Math.tan(horizontal*Math.PI/360)/aspect)*180/Math.PI);
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
 bed: {position:[2.55,1.65,-2.75],target:[.78,.42,-3.72],fov:70},
 bar: {position:[2.05,1.45,-3.25],target:[.62,.62,-2.3],fov:68},
 kitchen: {position:[1.75,1.62,-2.55],target:[1.9,1.25,0],fov:78},
};
// GLAMBERGET daybed motion. `slide` and `lift` run 0 (daybed) → 1 (double bed); each cushion
// has a height offset in metres and a squash/stretch scale about its base.
const clamp01=t=>Math.min(1,Math.max(0,t));const smooth=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
const backOut=t=>{const c=1.4;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2);};
const span=(t,a,b)=>clamp01((t-a)/(b-a));
// slideOut: when the pull-out starts rolling out; home: when it is fully back in. The balcony
// leaves move only outside that window, so they never meet the moving bed.
export const BED_TIMING={open:2.0,close:2.55,slideOut:.42,home:1.35};
export function bedPose(t,opening,count=5){
 // The last frame is exact, so a finished motion never leaves a cushion mid-wobble.
 if(t>=(opening?BED_TIMING.open:BED_TIMING.close))return {slide:+opening,lift:+opening,cushions:Array.from({length:count},()=>opening?{y:0,sx:0,sy:0,hidden:true}:{y:0,sx:1,sy:1})};
 if(opening){
  // Cushions hop and vanish one by one, then the pull-out rolls out and rises on its legs.
  const cushions=Array.from({length:count},(_,i)=>{const k=span(t,i*.07,i*.07+.42),s=1-Math.pow(span(k,.3,1),2);return {y:.16*Math.sin(Math.PI*k),sx:s,sy:s*(1+.1*Math.sin(Math.PI*span(k,0,.3)))};});
  return {slide:smooth(span(t,BED_TIMING.slideOut,1.45)),lift:backOut(span(t,1.45,1.95)),cushions};
 }
 // The pull-out drops and rolls home, then each cushion falls in and plops: squash, rebound, settle.
 const cushions=Array.from({length:count},(_,i)=>{const start=1.38+i*.13,fall=.32,land=start+fall;
  if(t<start)return {y:0,sx:0,sy:0,hidden:true};
  if(t<land){const k=(t-start)/fall;return {y:.75*(1-k*k),sx:.92,sy:1.1};}
  const k=t-land,decay=Math.exp(-k*7),wobble=Math.cos(k*24)*decay;return {y:0,sx:1+.16*wobble,sy:1-.24*wobble};});
 return {slide:1-smooth(span(t,.4,BED_TIMING.home)),lift:1-smooth(span(t,0,.42)),cushions};
}
// Balcony leaves turn about a vertical hinge. Room data is in plan mm (x right, y toward the
// balcony); the viewer's z is -y. Returns +1 or -1: the rotation sign that swings the leaf from
// its closed direction toward its open direction.
export function hingeSign(hinge,closed,open){
 const c=[closed[0]-hinge[0],-(closed[1]-hinge[1])],o=[open[0]-hinge[0],-(open[1]-hinge[1])];
 // d/dθ of a Y rotation at θ=0 maps (x,z) to (z,-x).
 return Math.sign(c[1]*o[0]-c[0]*o[1])||1;
}
// Target angle of each leaf for a balcony and bed state: as far open as the bed lets it.
export const leafAngle=(leaf,open,bedExtended)=>open?(bedExtended?leaf.angle_bed_extended:leaf.angle_daybed):0;
export function rendererFor(element,background){
 // Baked atlases are already display-referred (Blender view transform applied at bake time).
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(pixelRatio());renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NoToneMapping;
 renderer.setClearColor(background);renderer.domElement.tabIndex=0;element.appendChild(renderer.domElement);
 // Safari holds a closed page's graphics memory until collection, so reloads pile up until contexts
 // start failing. Release it explicitly, and rebuild if the page comes back from the back/forward cache.
 window.addEventListener('pagehide',()=>{renderer.dispose();renderer.forceContextLoss();});window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
 return renderer;
}
export function loopViewer(renderer,scene,camera,controls,container,labels,onResize){
 // Frames are requested only while something changes: damping, a preset move or a redraw.
 let dirty=true;let enabled=true;let lost=false;let frame=0;let drawn='';
 // Resizing wipes the canvas, so redraw in the same callback: waiting a frame shows it blank.
 const size=()=>{const box=container.getBoundingClientRect();if(box.width<1||box.height<1)return;const key=[box.width,box.height,pixelRatio()].join();if(key===drawn)return;drawn=key;renderer.setPixelRatio(pixelRatio());renderer.setSize(box.width,box.height);if(labels)labels.setSize(box.width,box.height);camera.aspect=box.width/box.height;onResize?.();camera.updateProjectionMatrix();if(enabled&&!lost){renderer.render(scene,camera);if(labels)labels.render(scene,camera);dirty=false;}else dirty=true;};
 const tick=()=>{frame=0;if(!enabled||lost)return;const moving=controls.update();if(moving||dirty){renderer.render(scene,camera);if(labels)labels.render(scene,camera);dirty=false;}if(moving)wake(false);};
 function wake(redraw=true){if(redraw)dirty=true;if(!frame&&enabled&&!lost)frame=requestAnimationFrame(tick);}
 const ro=new ResizeObserver(size);ro.observe(container);window.addEventListener('resize',size);controls.addEventListener('change',()=>wake());controls.addEventListener('start',()=>wake());
 const canvas=renderer.domElement;canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();lost=true;if(frame)cancelAnimationFrame(frame);frame=0;});canvas.addEventListener('webglcontextrestored',()=>{lost=false;wake();});
 size();
 return {size,draw(){wake();},enable(value){enabled=value;if(value){size();wake();}else if(frame){cancelAnimationFrame(frame);frame=0;}},dispose(){if(frame)cancelAnimationFrame(frame);ro.disconnect();window.removeEventListener('resize',size);renderer.dispose();}};
}
// Under memory pressure Safari can lose and restore a context thousands of times, which shows as
// flicker. Repeated losses within a few seconds end the attempt instead.
export function watchContext(canvas,{onLost,onRestored,onFailed},now=()=>performance.now()){let recent=[];let failed=false;
 canvas.addEventListener('webglcontextlost',()=>{if(failed)return;const time=now();recent=[...recent.filter(t=>time-t<8000),time];if(recent.length>=3){failed=true;onFailed?.();}else onLost?.();});
 canvas.addEventListener('webglcontextrestored',()=>{if(!failed)onRestored?.();});}
export class RoomViewer {
 constructor(container,{onProgress,onReady,onError,onCutaway,onContextLost,onContextRestored,onContextFailed,onMeasure,onFov,balcony=[],dimensions=[],ceiling,model='models/flat-baked.glb?bake=v26-stools',sky='models/sky.ktx2?v=2',views}={}){
  this.views={...VIEWS,...views};this.balconySpec=balcony;this.motion=Promise.resolve();this.onFov=onFov;this.userFov=null;this.container=container;this.onCutaway=onCutaway;this.onError=onError;this.onMeasure=onMeasure;this.cutaway=true;this.currentView='overview';this.scene=new THREE.Scene();this.interior=ceiling?interiorFor(ceiling):INTERIOR;
  this.camera=new THREE.PerspectiveCamera(43,1,.02,100);this.renderer=rendererFor(container,0xe8eadf);watchContext(this.renderer.domElement,{onLost:onContextLost,onRestored:()=>{onContextRestored?.();this.runner.draw();},onFailed:()=>{this.runner.enable(false);this.renderer.dispose();this.renderer.forceContextLoss();this.renderer.domElement.remove();onContextFailed?.();}});
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.1;this.controls.minDistance=.35;this.controls.maxDistance=21;this.controls.maxPolarAngle=Math.PI*.52;
  this.controls.addEventListener('start',()=>{this.animation=null;});
  this.controls.addEventListener('change',()=>this.updateCutaway());
  this.labels=new CSS2DRenderer();this.labels.domElement.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:2';container.appendChild(this.labels.domElement);
  this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container,this.labels,()=>{this.camera.fov=this.fovGoal();this.reportFov();});
  this.dimensionGroup=new THREE.Group();this.dimensionGroup.visible=false;this.scene.add(this.dimensionGroup);this.addDimensions(dimensions);this.setView('overview',true);
  this.measureGroup=new THREE.Group();this.scene.add(this.measureGroup);this.measurePoints=[];this.measuring=false;this.bindMeasure();
  // KTX2 atlases stay GPU-compressed (UASTC/ETC1S → ASTC/BC7/ETC2), with full mip chains.
  this.ktx2=new KTX2Loader().setTranscoderPath(asset('basis/')).detectSupport(this.renderer);
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);loader.setKTX2Loader(this.ktx2);const ktx2Sky=sky;
  loader.load(asset(model),gltf=>{
   this.model=gltf.scene;this.scene.add(this.model);this.addSky(ktx2Sky);
   this.model.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=false;const mats=Array.isArray(o.material)?o.material:[o.material];for(const m of mats){m.toneMapped=false;if(m.map)m.map.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());if(o.name==='flat_glass'||o.userData.category?.endsWith('_glass')){m.transparent=true;m.opacity=.10;m.depthWrite=false;m.side=THREE.DoubleSide;}}}});
   this.setupBed();this.setupBalcony();this.setupStools();this.setCutaway(this.cutaway);this.runner.draw();onReady?.();
  },event=>{if(event.total)onProgress?.(Math.round(event.loaded/event.total*100));},error=>{console.error('Room model load failed',error);onError?.(error);});
 }
 // A hand-set FOV wins over the preset until the next preset is chosen, including across resizes.
 fovGoal(){return this.userFov==null?this.responsiveFov(this.views[this.currentView]?.fov||43):verticalFov(this.userFov,this.camera.aspect);}
 reportFov(){this.onFov?.(horizontalFov(this.camera.fov,this.camera.aspect));}
 // The orbit target keeps its size on screen: the camera slides along its line of sight to
 // cancel the magnification, so only the perspective changes.
 setFov(value){
  this.animation=null;this.userFov=THREE.MathUtils.clamp(value,...FOV_RANGE);const fov=verticalFov(this.userFov,this.camera.aspect),half=degrees=>Math.tan(degrees*Math.PI/360);
  const {target,minDistance=0,maxDistance=Infinity}=this.controls,offset=this.camera.position.clone().sub(target);let length=THREE.MathUtils.clamp(offset.length()*half(this.camera.fov)/half(fov),minDistance,maxDistance);
  // Inside the flat the camera stops short of the walls; past that point the view has to scale.
  const room=this.interior?.find(box=>box.containsPoint(this.camera.position)&&box.containsPoint(target));
  if(room){const wall=new THREE.Ray(target,offset.clone().normalize()).intersectBox(room,new THREE.Vector3());if(wall)length=Math.min(length,Math.max(minDistance,wall.distanceTo(target)-.12));}
  offset.setLength(length);
  this.camera.position.copy(target).add(offset);this.camera.fov=fov;this.camera.updateProjectionMatrix();this.controls.update();this.updateCutaway();this.reportFov();this.runner.draw();
 }
 // A plain textured dome: a three.js equirect background would expand into a huge cube map.
 addSky(url){
  this.ktx2.load(asset(url),texture=>{
   const geometry=new THREE.SphereGeometry(60,48,32);const uv=geometry.attributes.uv;for(let i=0;i<uv.count;i++)uv.setY(i,1-uv.getY(i));
   const sky=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({map:texture,side:THREE.BackSide,depthWrite:false,toneMapped:false}));sky.scale.x=-1;sky.rotation.y=-Math.PI/2;sky.renderOrder=-1;sky.frustumCulled=false;
   sky.onBeforeRender=(renderer,scene,camera)=>{sky.position.copy(camera.position);sky.updateMatrixWorld();};this.sky=sky;this.scene.add(sky);this.updateCutaway();this.runner.draw();
  },undefined,error=>console.warn('Sky unavailable',error));
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
  const inside=(this.interior||INTERIOR).some(box=>box.containsPoint(this.camera.position));if(this.sky)this.sky.visible=!this.cutaway||inside;
  this.model.traverse(o=>{const category=o.userData.category;
   if(['shell','ceiling','glass','exterior'].includes(category)||category?.endsWith('_glass'))o.visible=!this.cutaway||inside;
   if(category==='chair')o.visible=this.currentView!=='equipment';
  });
 }
 setCutaway(value){this.cutaway=value;this.updateCutaway();this.onCutaway?.(value);this.runner.draw();}
 setView(name,immediate=false){
  // Presets move the same camera through the same baked model. Preserve the
  // cutaway preference and never change materials or lights here.
  const view=(this.views||VIEWS)[name]||VIEWS.overview;this.currentView=name;this.userFov=null;this.controls.enablePan=true;
  const from=this.camera.position.clone(),fromTarget=this.controls.target.clone(),to=new THREE.Vector3(...view.position),toTarget=new THREE.Vector3(...view.target),oldFov=this.camera.fov;
  const token={};this.animation=token;const start=performance.now();
  const move=time=>{if(this.animation!==token)return;const t=(immediate||reduced)?1:Math.min((time-start)/750,1);const k=1-Math.pow(1-t,3);this.camera.position.lerpVectors(from,to,k);this.controls.target.lerpVectors(fromTarget,toTarget,k);this.camera.fov=THREE.MathUtils.lerp(oldFov,this.userFov==null?this.responsiveFov(view.fov):verticalFov(this.userFov,this.camera.aspect),k);this.camera.updateProjectionMatrix();this.controls.update();this.updateCutaway();this.runner.draw();if(t<1)requestAnimationFrame(move);else this.reportFov?.();};move(start);
 }
 // The bake exports the pull-out extended and the cushions in place; start as a daybed.
 setupBed(){
  const nodes={};this.model.traverse(o=>{const c=o.userData.category;if(c?.startsWith('bed_'))nodes[c]=o;});
  const pull=nodes.bed_pullout;if(!pull){this.bed=null;return;}
  const [dx,dy]=pull.userData.bed_extend||[.825,.17];
  // Each cushion squashes about its own base, so it hangs from a pivot at its bottom centre.
  const cushions=Object.keys(nodes).filter(k=>k.startsWith('bed_cushion_')).sort().map(k=>{const mesh=nodes[k];const box=new THREE.Box3().setFromObject(mesh);const pivot=new THREE.Group();pivot.position.set((box.min.x+box.max.x)/2,box.min.y,(box.min.z+box.max.z)/2);mesh.parent.add(pivot);pivot.updateMatrixWorld();pivot.attach(mesh);return pivot;});
  // Nodes keep their exported origins, so every move is an offset from where the bake left them.
  this.bed={pull,legs:nodes.bed_legs,dx,dy,cushions,base:cushions.map(c=>c.position.clone()),pullBase:pull.position.clone(),legsBase:nodes.bed_legs?.position.clone(),extended:false,busy:false};
  this.poseBed({slide:0,lift:0,cushions:cushions.map(()=>({y:0,sx:1,sy:1}))});
 }
 poseBed({slide,lift,cushions}){
  const b=this.bed;b.pull.position.copy(b.pullBase).add(new THREE.Vector3(-b.dx*(1-slide),-b.dy*(1-lift),0));if(b.legs)b.legs.position.copy(b.legsBase).x-=b.dx*(1-slide);
  b.cushions.forEach((c,i)=>{const p=cushions[i];c.visible=!p.hidden&&p.sx>.001;c.position.copy(b.base[i]);c.position.y+=p.y;c.scale.set(p.sx||1e-3,p.sy||1e-3,p.sx||1e-3);});
 }
 get hasBed(){return !!this.bed;}
 // Motions queue up, so a press during one plays after it instead of fighting it.
 queue(task){const run=this.motion.then(task);this.motion=run.catch(()=>{});return run;}
 setBedExtended(value){
  const b=this.bed;if(!b||b.extended===value)return Promise.resolve(b?.extended??false);b.extended=value;
  return this.queue(async()=>{
   // Pulling out: the leaves come in to what the extended bed leaves free while the cushions
   // pop away, and are done before the pull-out starts rolling.
   // Pushing in: they open up again once the pull-out is home, while the cushions drop in.
   const wait=seconds=>new Promise(resolve=>setTimeout(resolve,reduced?0:seconds*1000));
   // A long swing holds the bed back just enough that the slide still starts after it.
   const lead=value?Math.max(0,this.leafTime(true)-BED_TIMING.slideOut):0;
   // The bar stools slide in to the bar as the bed starts, and back out once it is home.
   await Promise.all([wait(lead).then(()=>this.playBed(value)),value?this.swingLeaves(true):wait(BED_TIMING.home).then(()=>this.swingLeaves(false)),value?this.moveStools(false):wait(BED_TIMING.home).then(()=>this.moveStools(true))]);
   return value;});
 }
 playBed(value){
  const b=this.bed,total=value?BED_TIMING.open:BED_TIMING.close,start=performance.now();
  return new Promise(resolve=>{const step=time=>{const t=reduced?total:Math.min((time-start)/1000,total);this.poseBed(bedPose(t,value,b.cushions.length));this.runner.draw();if(t<total)requestAnimationFrame(step);else resolve();};requestAnimationFrame(step);});
 }
 // Stools are baked where people sit; `stool_tuck` is the move (plan metres) in to the bar.
 setupStools(){
  const nodes=[];this.model.traverse(o=>{if(o.userData.category?.startsWith('stool_'))nodes.push(o);});
  this.stools=nodes.length?nodes.map(node=>{const [dx,dy]=node.userData.stool_tuck||[0,0];return {node,base:node.position.clone(),tuck:new THREE.Vector3(dx,0,-dy)};}):null;this.stoolsOut=1;
 }
 moveStools(out){
  if(!this.stools)return Promise.resolve();const from=this.stoolsOut,to=out?1:0;if(from===to)return Promise.resolve();
  const total=reduced?0:.7,start=performance.now();
  return new Promise(resolve=>{const step=time=>{const k=total?Math.min((time-start)/1000/total,1):1;this.stoolsOut=from+(to-from)*smooth(k);
   for(const s of this.stools)s.node.position.copy(s.base).addScaledVector(s.tuck,1-this.stoolsOut);this.runner.draw();if(k<1)requestAnimationFrame(step);else resolve();};requestAnimationFrame(step);});
 }
 // Each leaf hangs from a pivot on its hinge line, so turning the pivot swings frame and glass together.
 setupBalcony(){
  const nodes={};this.model.traverse(o=>{const c=o.userData.category;if(c?.startsWith('balcony_'))nodes[c]=o;});
  const leaves=this.balconySpec.map(spec=>{const parts=[nodes['balcony_'+spec.side],nodes[`balcony_${spec.side}_glass`]].filter(Boolean);if(!parts.length)return null;
   const pivot=new THREE.Group();pivot.position.set(spec.hinge_mm[0]/1000,0,-spec.hinge_mm[1]/1000);parts[0].parent.add(pivot);pivot.updateMatrixWorld();for(const p of parts)pivot.attach(p);
   return {...spec,pivot,sign:hingeSign(spec.hinge_mm,spec.closed_toward_mm,spec.open_toward_mm),angle:0};}).filter(Boolean);
  this.balcony=leaves.length?{leaves,open:false}:null;
 }
 get hasBalcony(){return !!this.balcony;}
 setBalconyOpen(value){
  if(!this.balcony||this.balcony.open===value)return Promise.resolve(this.balcony?.open??false);this.balcony.open=value;
  return this.queue(()=>this.swingLeaves(this.bed?.extended??false).then(()=>value));
 }
 // Seconds a swing to this bed state takes: 0.6 s plus 0.7 s per 100° of the longest travel.
 leafTime(bedExtended){const leaves=this.balcony?.leaves||[];const travel=Math.max(0,...leaves.map(l=>Math.abs(l.angle-leafAngle(l,this.balcony.open,bedExtended))));return travel<.01||reduced?0:.6+travel/100*.7;}
 swingLeaves(bedExtended){
  const leaves=this.balcony?.leaves||[];const from=leaves.map(l=>l.angle),to=leaves.map(l=>leafAngle(l,this.balcony.open,bedExtended));
  const total=this.leafTime(bedExtended),start=performance.now();if(!total){leaves.forEach((l,i)=>{l.angle=to[i];l.pivot.rotation.y=l.sign*l.angle*Math.PI/180;});this.runner.draw();return Promise.resolve();}
  return new Promise(resolve=>{const step=time=>{const k=total?Math.min((time-start)/1000/total,1):1,e=smooth(k);
   leaves.forEach((l,i)=>{l.angle=from[i]+(to[i]-from[i])*e;l.pivot.rotation.y=l.sign*l.angle*Math.PI/180;});this.runner.draw();if(k<1)requestAnimationFrame(step);else resolve();};requestAnimationFrame(step);});
 }
 resize(){this.runner.size();}
 setEnabled(value){this.runner.enable(value);}
}
export class AssemblyViewer {
 constructor(container,onReady,onError,model='models/assembly.glb?design=v19-speakers'){
  this.container=container;this.scene=new THREE.Scene();this.camera=new THREE.PerspectiveCamera(39,1,.02,70);this.renderer=rendererFor(container,0xfbfcf7);this.renderer.toneMapping=THREE.NoToneMapping;
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.minDistance=.25;this.controls.maxDistance=12;this.runner=loopViewer(this.renderer,this.scene,this.camera,this.controls,container);
  this.materials={active:new THREE.MeshBasicMaterial({color:0x344b38}),wood:new THREE.MeshBasicMaterial({color:0xe2dfd0}),context:new THREE.MeshBasicMaterial({color:0xe4e8df}),initial:new THREE.MeshBasicMaterial({color:0xa6b69b})};
  this.edgeMaterial=new THREE.LineBasicMaterial({color:0x18281b});this.meshes=[];
  const loader=new GLTFLoader();loader.setMeshoptDecoder(MeshoptDecoder);loader.load(asset(model),gltf=>{
   this.model=gltf.scene;this.scene.add(this.model);this.model.traverse(o=>{if(!o.isMesh)return;let p=o;while(p&&!p.userData.part_id)p=p.parent;const id=p?.userData.part_id;if(!id)return;o.userData.componentId=id;o.userData.componentKind=p.userData.catalog_kind;const edge=new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry,38),this.edgeMaterial);o.add(edge);o.userData.edge=edge;this.meshes.push(o);});this.ready=true;onReady?.();
  },undefined,e=>{console.error('Assembly model load failed',e);onError?.(e);});
 }
 select(stage,stages){if(!this.ready){this.pending={stage,stages};return;}const active=new Set(stage.parts),seen=new Set(stages.filter(s=>s.id<=stage.id).flatMap(s=>s.parts));const showAll=stage.showAll??(stage.id<=2||stage.id>=18);const box=new THREE.Box3();let hasFocus=false;
  for(const mesh of this.meshes){const id=mesh.userData.componentId;const selected=active.has(id);mesh.visible=showAll||seen.has(id);mesh.material=selected?(mesh.userData.componentKind==='wood'?this.materials.wood:this.materials.active):showAll?this.materials.initial:this.materials.context;mesh.userData.edge.visible=selected||showAll;if(selected){box.expandByObject(mesh);hasFocus=true;}}
  if(!hasFocus)box.setFromObject(this.model);const centre=box.getCenter(new THREE.Vector3());const size=box.getSize(new THREE.Vector3());const distance=Math.max(size.x,size.y,size.z,1.15)*1.55*Math.max(1,1.2/this.camera.aspect);this.controls.target.copy(centre);this.camera.position.copy(centre).add(new THREE.Vector3(-1.5,.9,1.15).normalize().multiplyScalar(distance));this.controls.update();this.runner.size();this.runner.draw();
 }
 setEnabled(value){this.runner.enable(value);}
 resize(){this.runner.size();}
}
