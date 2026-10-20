import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, weld, meshopt } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';
import { stat, readFile, writeFile } from 'node:fs/promises';
await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder});
for(const path of ['public/models/flat-baked.glb']){
 const before=(await stat(path)).size;const document=await io.read(path);await document.transform(dedup(),prune(),weld(),meshopt({encoder:MeshoptEncoder,level:'high'}));await io.write(path,document);const after=(await stat(path)).size;const manifestPath='public/data/bake-manifest.json';const manifest=JSON.parse(await readFile(manifestPath,'utf8'));manifest.uncompressed_model_bytes=manifest.uncompressed_model_bytes||before;manifest.model_bytes=after;manifest.mesh_compression='EXT_meshopt_compression';await writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');console.log(`${path}: ${(before/1e6).toFixed(2)} MB → ${(after/1e6).toFixed(2)} MB`);
}
