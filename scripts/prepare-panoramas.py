"""Remove Blender's local-path JPEG comments without recompressing pixels."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
manifest_path=ROOT/'public/data/panoramas.json'
manifest=json.loads(manifest_path.read_text())
for record in manifest['panoramas']:
 path=ROOT/'public'/record['file'];data=path.read_bytes()
 assert data[:2]==b'\xff\xd8','Expected JPEG'
 out=bytearray(data[:2]);offset=2;dimensions=None
 while offset<len(data):
  assert data[offset]==255,'Invalid JPEG marker'
  marker=data[offset+1]
  if marker in (0xda,0xd9):out.extend(data[offset:]);break
  length=struct.unpack_from('>H',data,offset+2)[0];end=offset+2+length
  if marker in (0xc0,0xc1,0xc2):
   height,width=struct.unpack_from('>HH',data,offset+5);dimensions=(width,height)
  if marker!=0xfe:out.extend(data[offset:end])
  offset=end
 assert dimensions==(record['width'],record['height']),'Render resolution does not match provenance'
 path.write_bytes(out)
 record['bytes']=len(out);record['sha256']=hashlib.sha256(out).hexdigest()
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print(f"Prepared {len(manifest['panoramas'])} full-resolution Cycles panoramas; pixel data unchanged.")
