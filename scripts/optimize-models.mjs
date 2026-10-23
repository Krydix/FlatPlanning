import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRTextureBasisu } from '@gltf-transform/extensions';
import { dedup, prune, weld, meshopt } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import { stat, readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
// Baked atlases become KTX2 (UASTC + Zstandard, full mip chain) so they stay GPU-compressed:
// roughly a quarter of the memory of decoded PNG/JPEG. Requires KTX-Software 4.3+ (`ktx`);
// set KTX_BIN if it is not on PATH.
const KTX=process.env.KTX_BIN||'ktx';const RDO=process.env.KTX_RDO||'2.0';
// Large, low-frequency surfaces use ETC1S (smaller download); inspected detail stays UASTC.
const SMOOTH=new Set((process.env.KTX_ETC1S??'shell,ceiling,exterior,glass').split(',').filter(Boolean));
await MeshoptEncoder.ready;await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
for(const path of ['public/models/flat-baked.glb']){
 const before=(await stat(path)).size;const document=await io.read(path);await document.transform(dedup(),prune(),weld(),meshopt({encoder:MeshoptEncoder,level:'high'}));
 const work=await mkdtemp(join(tmpdir(),'flat-ktx-'));const textures=[];let gpuBytes=0;
 document.createExtension(KHRTextureBasisu).setRequired(true);
 for(const [i,texture] of document.getRoot().listTextures().entries()){
  // Prefer the lossless graded bake from .cache so re-encoding never compounds compression loss.
  const key=(texture.getName()||'').replace(/^baked[-_]/,'').replace(/_graded$/,'');const cached=`.cache/bake/baked-${key}.png`;
  const source=existsSync(cached)?await readFile(cached):texture.getMimeType()==='image/ktx2'?null:texture.getImage();if(!source)continue;
  const input=join(work,`${i}.png`),output=join(work,`${i}.ktx2`);await writeFile(input,source);
  const smooth=SMOOTH.has(key);
  execFileSync(KTX,['create','--format','R8G8B8_SRGB',...(smooth?['--encode','basis-lz','--clevel','4','--qlevel','255']:['--encode','uastc','--uastc-quality','2','--uastc-rdo','--uastc-rdo-l',RDO,'--zstd','18']),'--generate-mipmap',input,output],{stdio:'inherit'});
  const [width,height]=texture.getSize();gpuBytes+=Math.round(width*height*4/3);
  texture.setImage(await readFile(output)).setMimeType('image/ktx2').setURI('');textures.push({name:key,size:[width,height],codec:smooth?'ETC1S':'UASTC',bytes:(await stat(output)).size});
 }
 await rm(work,{recursive:true,force:true});await io.write(path,document);const after=(await stat(path)).size;
 const manifestPath='public/data/bake-manifest.json';const manifest=JSON.parse(await readFile(manifestPath,'utf8'));manifest.uncompressed_model_bytes=manifest.uncompressed_model_bytes||before;manifest.model_bytes=after;manifest.mesh_compression='EXT_meshopt_compression';
 manifest.texture_compression=`KHR_texture_basisu: KTX2, mipmapped; UASTC (RDO λ${RDO}, Zstandard 18) for detail, ETC1S for ${[...SMOOTH].join(', ')}`;manifest.textures=textures;manifest.texture_count=textures.length;manifest.gpu_texture_bytes_estimate=gpuBytes;
 await writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');console.log(`${path}: ${(before/1e6).toFixed(2)} MB → ${(after/1e6).toFixed(2)} MB; ${textures.length} KTX2 atlases ≈ ${(gpuBytes/1e6).toFixed(0)} MB GPU`);
}
