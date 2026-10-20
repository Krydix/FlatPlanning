import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';

globalThis.window={matchMedia:()=>({matches:false})};
const {RoomViewer}=await import('../src/viewer.js');

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

test('cutaway retains illuminated room surfaces for interior viewpoints',()=>{
 const model=new THREE.Group();
 for(const category of ['shell','ceiling','glass','exterior','wood']){
  const mesh=new THREE.Mesh();mesh.userData.category=category;model.add(mesh);
 }
 const viewer={model,cutaway:true,camera:{position:new THREE.Vector3(1,1,-2)},
  shellBounds:new THREE.Box3(new THREE.Vector3(0,0,-5.3),new THREE.Vector3(3.45,2.5,1))};
 RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.filter(o=>o.userData.category!=='exterior').every(o=>o.visible));
 viewer.camera.position.set(8,7,5);RoomViewer.prototype.updateCutaway.call(viewer);
 assert.ok(model.children.filter(o=>['shell','ceiling','glass'].includes(o.userData.category)).every(o=>!o.visible));
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
