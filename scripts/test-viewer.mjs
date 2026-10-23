import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

globalThis.window={matchMedia:()=>({matches:false}),devicePixelRatio:2,addEventListener(){},removeEventListener(){}};
const {RoomViewer,loopViewer,INTERIOR}=await import('../src/viewer.js');

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

test('dimensions are dashed unless measured on site',()=>{
 globalThis.document={createElement:()=>({className:'',textContent:'',style:{},setAttribute(){}})};
 const viewer={dimensionGroup:new THREE.Group()};
 RoomViewer.prototype.addDimensions.call(viewer,[{label:'Room width',a:[0,0,0],b:[3450,0,0],value:3450,basis:'assumed'},{label:'Ceiling',a:[0,0,0],b:[0,0,2480],value:2480,basis:'measured'}]);
 const lines=viewer.dimensionGroup.children.filter(o=>o.isLine);
 assert.equal(lines[0].material.type,'LineDashedMaterial');assert.equal(lines[1].material.type,'LineBasicMaterial');
 const labels=viewer.dimensionGroup.children.filter(o=>o.element);assert.match(labels[0].element.textContent,/3\.45 m · assumed/);assert.match(labels[1].element.textContent,/2\.48 m$/);
 assert.ok(INTERIOR.length===3);
});
