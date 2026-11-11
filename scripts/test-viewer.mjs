import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

globalThis.window={matchMedia:()=>({matches:false}),devicePixelRatio:2,addEventListener(){},removeEventListener(){}};
const {RoomViewer,bedPose,BED_TIMING,hingeSign,leafAngle,loopViewer,watchContext,INTERIOR,FOV_RANGE,horizontalFov,verticalFov}=await import('../src/viewer.js');

test('camera presets preserve baked materials and the chosen cutaway throughout each transition',()=>{
 const queue=[];
 globalThis.requestAnimationFrame=callback=>queue.push(callback);
 const texture=new THREE.Texture();const material=new THREE.MeshBasicMaterial({map:texture});
 const shell=new THREE.Mesh(new THREE.BoxGeometry(),material);
 shell.userData.category='shell';
 const scene=new THREE.Scene();scene.add(shell);
 const viewer={camera:new THREE.PerspectiveCamera(43,1,.02,100),scene,
  controls:{target:new THREE.Vector3(),update(){},enablePan:true},
  runner:{draw(){}},updateCutaway(){},responsiveFov:RoomViewer.prototype.responsiveFov,
  setCutaway(){assert.fail('A camera preset must never change the cutaway or lighting');}};
 for(const cutaway of [false,true]){
  viewer.cutaway=cutaway;shell.visible=!cutaway;
  for(const preset of ['entrance','desk','wardrobe','plan','overview']){
   RoomViewer.prototype.setView.call(viewer,preset);
   const started=performance.now();
   for(const elapsed of [100,375,800]){
    const pending=queue.splice(0);for(const callback of pending)callback(started+elapsed);
    assert.equal(viewer.cutaway,cutaway);
    assert.equal(shell.visible,!cutaway);
    assert.equal(shell.material,material);
    assert.equal(shell.material.map,texture);
   }
   assert.equal(queue.length,0);
   assert.ok(viewer.camera.position.length()>0);
  }
 }
});

test('a superseded camera animation cannot take over the next preset',()=>{
 const queue=[];globalThis.requestAnimationFrame=callback=>queue.push(callback);
 const viewer={camera:new THREE.PerspectiveCamera(),controls:{target:new THREE.Vector3(),update(){}},
  runner:{draw(){}},updateCutaway(){},responsiveFov:RoomViewer.prototype.responsiveFov};
 RoomViewer.prototype.setView.call(viewer,'entrance');
 RoomViewer.prototype.setView.call(viewer,'desk',true);
 const finalPosition=viewer.camera.position.clone();
 for(const callback of queue.splice(0))callback(performance.now()+1000);
 assert.ok(viewer.camera.position.equals(finalPosition));
 assert.equal(viewer.currentView,'desk');
});

test('cutaway retains illuminated room surfaces and the outside view for interior viewpoints',()=>{
 const model=new THREE.Group();
 for(const category of ['shell','ceiling','glass','exterior','wood']){
  const mesh=new THREE.Mesh();mesh.userData.category=category;model.add(mesh);
 }
 const viewer={model,cutaway:true,camera:{position:new THREE.Vector3(1,1,-2)}};
 RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.every(o=>o.visible));
 // The hall is interior too; a point beside the flat in wall thickness is not.
 viewer.camera.position.set(2.8,1.5,1.5);RoomViewer.prototype.updateCutaway.call(viewer);assert.ok(model.children.every(o=>o.visible));
 viewer.camera.position.set(-.2,1.5,-2);RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.filter(o=>['shell','ceiling','glass','exterior'].includes(o.userData.category)).every(o=>!o.visible));
 viewer.camera.position.set(8,7,5);RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.filter(o=>['shell','ceiling','glass','exterior'].includes(o.userData.category)).every(o=>!o.visible));
 assert.equal(model.children.find(o=>o.userData.category==='wood').visible,true);
 viewer.cutaway=false;RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.every(o=>o.visible));
});

test('equipment inspection hides only the chair and restores it for normal room views',()=>{
 const model=new THREE.Group();const texture=new THREE.Texture();const material=new THREE.MeshBasicMaterial({map:texture});
 for(const category of ['chair','equipment','wood','shell']){const mesh=new THREE.Mesh(undefined,material);mesh.userData.category=category;model.add(mesh);}
 const viewer={model,cutaway:true,currentView:'equipment',camera:{position:new THREE.Vector3(1,1,-2)},shellBounds:new THREE.Box3(new THREE.Vector3(0,0,-5.3),new THREE.Vector3(3.45,2.5,1))};
 RoomViewer.prototype.updateCutaway.call(viewer);
 assert.equal(model.children[0].visible,false);assert.ok(model.children.slice(1).every(o=>o.visible));
 assert.ok(model.children.every(o=>o.material===material&&o.material.map===texture));
 viewer.currentView='desk';RoomViewer.prototype.updateCutaway.call(viewer);assert.ok(model.children.every(o=>o.visible));
});

test('the render loop sleeps when idle and wakes for changes, resize and context restore',()=>{
 const queue=[];globalThis.requestAnimationFrame=callback=>{queue.push(callback);return queue.length;};globalThis.cancelAnimationFrame=()=>{};
 globalThis.ResizeObserver=class{observe(){}disconnect(){}};
 const listeners={},canvasEvents={};let renders=0,moving=0;
 const renderer={domElement:{addEventListener:(type,fn)=>{canvasEvents[type]=fn;}},setPixelRatio(){},setSize(){},render(){renders++;},dispose(){}};
 const controls={update:()=>moving-->0,addEventListener:(type,fn)=>{listeners[type]=fn;}};
 const container={getBoundingClientRect:()=>({width:400,height:300})};
 const runner=loopViewer(renderer,new THREE.Scene(),new THREE.PerspectiveCamera(),controls,container);
 const flush=()=>{for(const callback of queue.splice(0))callback(0);};
 flush();assert.equal(renders,1);flush();assert.equal(queue.length,0,'no frames while idle');
 moving=3;listeners.change();flush();flush();flush();flush();assert.equal(queue.length,0);assert.ok(renders>=4);
 const before=renders;canvasEvents.webglcontextlost({preventDefault(){}});runner.draw();flush();assert.equal(renders,before,'no drawing while the context is lost');
 canvasEvents.webglcontextrestored();flush();assert.equal(renders,before+1);
 runner.enable(false);runner.draw();assert.equal(queue.length,0,'disabled viewers request no frames');
});

test('a variant replaces camera presets without losing the rest',()=>{
 const queue=[];globalThis.requestAnimationFrame=callback=>queue.push(callback);
 const viewer={camera:new THREE.PerspectiveCamera(),controls:{target:new THREE.Vector3(),update(){}},runner:{draw(){}},updateCutaway(){},responsiveFov:RoomViewer.prototype.responsiveFov,views:{desk:{position:[9,1,-3],target:[3,1,-3],fov:60}}};
 RoomViewer.prototype.setView.call(viewer,'desk',true);assert.equal(viewer.camera.position.x,9);
 RoomViewer.prototype.setView.call(viewer,'missing',true);assert.equal(viewer.currentView,'missing');assert.ok(viewer.camera.position.x!==9,'An unknown preset falls back to the overview');
});

test('FOV changes the perspective while the orbit target keeps its size on screen',()=>{
 const queue=[];globalThis.requestAnimationFrame=callback=>queue.push(callback);const seen=[];
 const viewer=Object.create(RoomViewer.prototype);Object.assign(viewer,{camera:new THREE.PerspectiveCamera(43,2),controls:{target:new THREE.Vector3(),update(){},minDistance:.35,maxDistance:21},runner:{draw(){}},updateCutaway(){},views:{desk:{position:[1,2,3],target:[0,0,0],fov:62}},userFov:null,onFov:fov=>seen.push(fov)});
 RoomViewer.prototype.setView.call(viewer,'desk',true);assert.equal(viewer.camera.fov,62);assert.ok(Math.abs(seen.at(-1)-horizontalFov(62,2))<1e-9);
 const apparent=()=>viewer.camera.position.distanceTo(viewer.controls.target)*Math.tan(viewer.camera.fov*Math.PI/360);const size=apparent(),direction=viewer.camera.position.clone().normalize(),aim=viewer.controls.target.clone();
 for(const fov of [60,120,75]){viewer.setFov(fov);assert.ok(Math.abs(seen.at(-1)-fov)<1e-9);assert.ok(Math.abs(apparent()-size)<1e-9,'The target must not grow or shrink');assert.ok(viewer.camera.position.clone().normalize().distanceTo(direction)<1e-9,'The view direction must not change');assert.ok(viewer.controls.target.equals(aim));}
 viewer.setFov(90);viewer.camera.aspect=1;assert.ok(Math.abs(horizontalFov(viewer.fovGoal(),1)-90)<1e-9,'A resize keeps the horizontal setting');viewer.camera.aspect=2;
 viewer.setFov(500);assert.ok(Math.abs(seen.at(-1)-FOV_RANGE[1])<1e-9);viewer.setFov(1);assert.ok(Math.abs(seen.at(-1)-FOV_RANGE[0])<1e-9);assert.ok(viewer.camera.position.length()<=21,'The camera stays inside the orbit limits');
 RoomViewer.prototype.setView.call(viewer,'desk',true);assert.equal(viewer.userFov,null);assert.equal(viewer.camera.fov,62);
 RoomViewer.prototype.setView.call(viewer,'desk');viewer.setFov(70);for(const callback of queue.splice(0))callback(performance.now()+1000);assert.ok(Math.abs(horizontalFov(viewer.camera.fov,2)-70)<1e-9,'A drag stops a preset move');
 assert.ok(verticalFov(130,.5)<=140,'Portrait windows stay away from a degenerate projection');
});

test('a resize redraws at once, and an unchanged size leaves the canvas alone',()=>{
 const queue=[];globalThis.requestAnimationFrame=callback=>{queue.push(callback);return queue.length;};globalThis.cancelAnimationFrame=()=>{};globalThis.ResizeObserver=class{observe(){}disconnect(){}};
 let box={width:400,height:300},sets=0,renders=0;
 const renderer={domElement:{addEventListener(){}},setPixelRatio(){},setSize(){sets++;},render(){renders++;},dispose(){}};
 const runner=loopViewer(renderer,new THREE.Scene(),new THREE.PerspectiveCamera(),{update:()=>false,addEventListener(){}},{getBoundingClientRect:()=>box});
 assert.equal(sets,1);assert.equal(renders,1,'Drawn in the resize callback, without waiting a frame');
 runner.size();runner.size();assert.equal(sets,1,'Same size must not wipe the canvas');assert.equal(renders,1);
 box={width:500,height:300};runner.size();assert.equal(sets,2);assert.equal(renders,2);assert.equal(queue.length,0);
 runner.enable(false);box={width:600,height:300};runner.size();assert.equal(renders,2,'A hidden viewer does not draw');runner.enable(true);for(const callback of queue.splice(0))callback(0);assert.equal(renders,3);
});

test('FOV compensation keeps the camera inside the room',()=>{
 globalThis.requestAnimationFrame=()=>0;
 const viewer=Object.create(RoomViewer.prototype);Object.assign(viewer,{camera:new THREE.PerspectiveCamera(70,1.3),controls:{target:new THREE.Vector3(2.36,1.4,-3.6),update(){},minDistance:.35,maxDistance:21},runner:{draw(){}},updateCutaway(){},interior:INTERIOR,userFov:null});
 viewer.camera.position.set(2.36,1.4,-.42);viewer.setFov(50);assert.ok(viewer.camera.position.z<=-.12+1e-9,'Stops short of the kitchen wall');assert.ok(viewer.camera.position.z>-.42,'Still backs up as far as it can');
 viewer.setFov(120);const inside=INTERIOR.some(box=>box.containsPoint(viewer.camera.position));assert.ok(inside);
});

test('repeated context losses end the attempt instead of flickering, and single ones recover',()=>{
 const handlers={};const canvas={addEventListener:(type,fn)=>{handlers[type]=fn;}};let clock=0,lost=0,restored=0,failed=0;
 watchContext(canvas,{onLost:()=>lost++,onRestored:()=>restored++,onFailed:()=>failed++},()=>clock);
 const cycle=()=>{handlers.webglcontextlost();handlers.webglcontextrestored();};
 cycle();clock=20000;cycle();clock=40000;cycle();assert.equal(failed,0,'Spaced-out losses are ordinary recoveries');assert.equal(lost,3);assert.equal(restored,3);
 clock=41000;cycle();clock=42000;cycle();assert.equal(failed,1);for(let i=0;i<50;i++)cycle();assert.equal(failed,1,'Failing happens once');assert.equal(lost,4);assert.equal(restored,4);
});

test('dimensions are dashed unless measured on site',()=>{
 globalThis.document={createElement:()=>({className:'',textContent:'',style:{},setAttribute(){}})};
 const viewer={dimensionGroup:new THREE.Group()};
 RoomViewer.prototype.addDimensions.call(viewer,[{label:'Room width',a:[0,0,0],b:[3450,0,0],value:3450,basis:'assumed'},{label:'Ceiling',a:[0,0,0],b:[0,0,2480],value:2480,basis:'measured'}]);
 const lines=viewer.dimensionGroup.children.filter(o=>o.isLine);
 assert.equal(lines[0].material.type,'LineDashedMaterial');assert.equal(lines[1].material.type,'LineBasicMaterial');
 const labels=viewer.dimensionGroup.children.filter(o=>o.element);assert.match(labels[0].element.textContent,/3\.45 m · assumed/);assert.match(labels[1].element.textContent,/2\.48 m$/);
 assert.ok(INTERIOR.length===3);
});

test('the daybed opens to a flat double and closes with every cushion back in place',()=>{
 const start=bedPose(0,true);assert.equal(start.slide,0);assert.equal(start.lift,0);for(const c of start.cushions){assert.equal(c.sx,1);assert.equal(c.y,0);}
 const open=bedPose(BED_TIMING.open,true);assert.equal(open.slide,1);assert.equal(open.lift,1);assert.ok(open.cushions.every(c=>c.hidden));
 // The pull-out only rises once it has cleared the fixed frame, and drops before it rolls home.
 for(let t=0;t<BED_TIMING.open;t+=.05){const p=bedPose(t,true);if(p.lift>0)assert.equal(p.slide,1,`lifting at ${t}s before fully out`);}
 for(let t=0;t<BED_TIMING.close;t+=.05){const p=bedPose(t,false);if(p.slide<1)assert.equal(p.lift,0,`rolling in at ${t}s while still raised`);
  // Cushions only fall onto the closed daybed.
  if(p.cushions.some(c=>!c.hidden))assert.equal(p.slide,0,`cushion visible at ${t}s with the bed out`);}
 const closed=bedPose(BED_TIMING.close,false);assert.equal(closed.slide,0);assert.equal(closed.lift,0);for(const c of closed.cushions)assert.deepEqual(c,{y:0,sx:1,sy:1});
 // A cushion lands from above and squashes: wider and flatter just after touchdown.
 const landed=bedPose(1.38+.32+.01,false).cushions[0];assert.equal(landed.y,0);assert.ok(landed.sx>1&&landed.sy<1);
});

test('balcony leaves swing into the room and never past what the bed leaves free',()=>{
 // Turning a closed leaf by sign × a small angle must move its free edge toward the open side.
 for(const [hinge,closed,open] of [[[260,5300],[1420,5300],[260,4140]],[[2580,5300],[1420,5300],[2580,4140]]]){
  const sign=hingeSign(hinge,closed,open),a=sign*.1;const x=closed[0]-hinge[0],z=-(closed[1]-hinge[1]);
  const turned=[x*Math.cos(a)+z*Math.sin(a),-x*Math.sin(a)+z*Math.cos(a)];assert.ok(turned[1]>0,'the free edge moves toward the room (+z)');
 }
 const leaf={angle_daybed:42,angle_bed_extended:33};
 assert.equal(leafAngle(leaf,false,false),0);assert.equal(leafAngle(leaf,false,true),0);
 assert.equal(leafAngle(leaf,true,false),42);assert.equal(leafAngle(leaf,true,true),33);
 // The leaves only move while the pull-out is still: in before it rolls out, out after it is home.
 assert.equal(bedPose(BED_TIMING.slideOut,true).slide,0);
 assert.equal(bedPose(BED_TIMING.home,false).slide,0);
});
