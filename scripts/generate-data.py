"""Derive the site BOM, assembly stages and original line drawings from V18."""
import json,math,csv,io,sys,re,html
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'))
from pipe_engine import board_corners,STOCK,CATALOG
A=json.loads((ROOT/'source/assembly.json').read_text());P=json.loads((ROOT/'source/prices.json').read_text());parts={p['id']:p for p in A['parts']}
OUT=ROOT/'public/data';OUT.mkdir(parents=True,exist_ok=True);DRAW=ROOT/'public/diagrams';DRAW.mkdir(exist_ok=True)
labels={'tube_40':'40 mm pipe','tube_200':'200 mm pipe','tube_250':'250 mm pipe','tube_602':'602 mm pipe','tube_802':'802 mm pipe','tube_1000':'1,000 mm pipe','tube_1200':'1,200 mm pipe','tube_1500':'1,500 mm pipe','cross':'Four-way threaded cross','slide_tee':'Sliding T connector','flange':'Ø70 mm mounting flange','extension':'Female–female coupling','elbow':'90° elbow','saddle':'Saddle shelf holder','cap':'End cover'}
def show(id):
 p=parts[id];return labels.get(p['kind'],id.replace('Rack.','Wardrobe · ').replace('Desk.','Desk · ').replace('Speaker0','Speaker L').replace('Speaker1','Speaker R'))
def jwrite(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
# Complete purchase list; reconcile every core line with the retained budget.
rows=[]
for r in P['hardware']:
 rows.append({'id':r['kind'],'category':'Hardware','name':labels.get(r['kind'],r['name']),'description':r['name']+(' · €4 each budget allowance; verify store price' if r['kind']=='cross' else ''),'sku':CATALOG[r['kind']]['sku'],'quantity':r['quantity'],'buyPacks':r['buy_packs'],'packSize':r['units_per_pack'],'unitPrice':float(r['unit_eur']),'total':float(r['total_eur']),'url':r['source'],'status':r['status'],'purchase':True})
for r in P['wood']:
 rows.append({'id':'wood:'+r['id'],'category':'Wood','name':show(r['id']),'description':f"{r['length_mm']:g} × {r['depth_mm']:g} × {r['thickness_mm']:g} mm · oak allowance",'quantity':1,'buyPacks':1,'packSize':1,'unitPrice':float(r['net_eur']['base']),'total':float(r['net_eur']['base']),'url':None,'status':'Concept dimensions, not final machining sizes. Timber supplier not selected.','holes':r['holes'],'purchase':True})
t=P['totals']['base']
rows.append({'id':'wood-yield','category':'Wood','name':'Timber yield allowance','description':'15% material waste on the structural oak panels','quantity':1,'total':round(float(t['timber_with_waste'])-float(t['timber_net']),2),'url':None,'status':'Budget allowance','purchase':False})
rows.append({'id':'light-lips','category':'Wood','name':'Five removable oak light covers','description':'Front lips, bottom glare returns and end cheeks, including yield allowance','quantity':5,'total':float(t['lip_with_waste']),'url':None,'status':'Custom joinery allowance; verify access and fitting reliefs.','purchase':True})
for i,r in enumerate(P['lighting']):
 rows.append({'id':'light:'+str(i),'category':'Lighting','name':r['name'],'description':'Intact original IKEA fixture or driver/lead','quantity':r['quantity'],'buyPacks':r['quantity'],'packSize':1,'unitPrice':float(r['unit_eur']),'total':float(r['total_eur']),'url':r['source'],'status':'Retained 19 October 2026 price input','purchase':True})
for i,r in enumerate(P['base_allowances']):
 rows.append({'id':'allowance:'+str(i),'category':'Allowances','name':r['name'],'description':'Working budget allowance','quantity':r['quantity'],'unitPrice':float(r['base'])/r['quantity'],'total':float(r['base']),'url':None,'status':'Not a supplier quote','purchase':False})
allowance_gap=round(float(t['other_allowances'])-sum(float(r['base']) for r in P['base_allowances']),2)
rows.append({'id':'lip-fixings','category':'Allowances','name':'Light-cover fixings and extra cuts','description':'Small brackets, short wood screws and removable-cover joinery','quantity':1,'total':allowance_gap,'url':None,'status':'Budget allowance','purchase':False})
rows.append({'id':'contingency','category':'Allowances','name':'Contingency · 10%','description':'Reserve on the core frame, wood, lights and allowances','quantity':1,'total':float(t['contingency']),'url':None,'status':'Budget reserve','purchase':False})
core=sum(r['total'] for r in rows);assert abs(core-float(t['core_budget']))<.02,(core,t['core_budget'])
rows.append({'id':'knagglig','category':'Crates','name':'KNAGGLIG · pine crate','description':'460 × 310 × 250 mm · four on top, two stacked below the folded bay','quantity':6,'buyPacks':6,'packSize':1,'unitPrice':9.99,'total':59.94,'url':'https://www.ikea.com/de/de/p/knagglig-kasten-kiefer-70292359/','status':'Retained 20 October 2026 price; extra to core budget','purchase':True,'optional':True})
for i,r in enumerate(P['optional_allowances']):
 rows.append({'id':'optional:'+str(i),'category':'Optional','name':r['name'],'description':'Optional accessory allowance; no exact product selected','quantity':1,'total':float(r['base']),'url':None,'status':'Not a supplier quote; extra to core budget','purchase':True,'optional':True})
counts=Counter(p['kind'] for p in parts.values());assert all(r['quantity']==counts[r['kind']] for r in P['hardware'])
# Stages are a dry-fit planning sequence. The physical assembly method must be
# confirmed with actual fittings; all sliding sleeves must be loaded before closing posts.
assigned=set();stages=[]
def stage(title,kicker,description,actions,selector=None,notes=None,focus='frame',extra=None):
 ids=sorted(id for id,p in parts.items() if id not in assigned and selector and selector(id,p));assigned.update(ids)
 number=len(stages)+1
 stages.append({'id':number,'title':title,'kicker':kicker,'description':description,'actions':actions,'notes':notes or [],'parts':ids,'materials':[{'kind':k,'name':labels.get(k,k),'quantity':n,'sku':CATALOG.get(k,{}).get('sku'),'url':CATALOG.get(k,{}).get('source')} for k,n in sorted(Counter(parts[id]['kind'] for id in ids).items())],'focus':focus,'extra':extra or [],'diagram':f'diagrams/step-{number:02}.svg'})
stage('Measure before making','Preparation','Lock the design; verify the real room and a sample connector before ordering wood or drilling.',[
 'Measure the ceiling height. The top crate envelope reaches about 2,468 mm; 2,500 mm is only the current assumption.',
 'Measure seating stops, sleeve envelopes, saddle height and screw positions using the measurement fields supplied with the model.',
 'Check the independent right balcony leaf, gathered curtain, real clothes and the 600 mm minimum entrance with a physical mock-up.',
 'Confirm wall construction, anchors, clamp anti-rotation and desk/speaker load capacities. Choose fixings for the actual substrate.'
],notes=['This is a checked geometry proposal, not a certified load rating or a drilling template. Do not cut the boards to these preview numbers until fitting measurements are entered.'],focus='plan')
stage('Lay out the kit','Preparation','Sort pipes by their printed catalog lengths, and keep similar-looking fittings separate.',[
 'Use only the listed DOLLE PIPE family; do not mix generic plumbing threads or change a stock pipe length.',
 'The BOM shows required pieces and purchase packs separately. Saddles come in packs of two.',
 'Dry-fit one T/pipe/saddle/board connection. Check the end-cover fit; covers do not carry load.',
 'Assemble horizontal pipe-and-fitting submodules while the T sleeves are free, then feed the upright sections through. Do not try to screw a rigid closed frame together.'
],notes=['All sliding T pieces for a rod section must be staged before flanges, couplings or covers prevent them passing. Exact assembly order and fastener torque must follow the actual part instructions.'])
stage('Stage the lower uprights','Frame','Lay out the ten main posts at their V18 positions. Leave the structure loose and supported.',[
 'Lay out paired front/back posts 290 mm apart, using the model axes rather than the wall surface as a datum.',
 'Stage the lower sleeves and braces before closing each 1,000 mm lower post into its coupling.',
 'Use floor protection under flanges. Do not assume that a floor flange must be drilled into the rental floor.',
 'Keep the frame braced or held during dry fitting; it is not self-supporting until its wall ties and braces are secured.'
],lambda id,p:bool(re.match(r'^(RF[0-3]|RB[0-3]|DS0|SB0)\.(foot|lower)$',id)),notes=['The near shelf frame is 50 mm before the desk edge frame used in older versions. Keep the V18 axes; moving it back causes a pipe intersection.'])
stage('Build the shared desk supports','Desk module','Two front returns carry the desk edge; the existing shelf posts replace the short rear desk legs.',[
 'Preassemble each free cross/front-arm/elbow module, with 40 mm pipe, coupling and 602 mm front leg. The cross-bearing post below uses 602 + coupling + 40 mm; above it uses 40 + coupling + 1500 mm.',
 'Fit a four-female DOLLE cross at each middle upright: 250 mm front arm, 250 mm rear bridge, upper and lower stock upright sections. Join the bridge to a sliding T on the rear upright.',
 'Use low 250 mm rear braces at 300 mm and front-leg braces at 400 mm, with a sliding T on both ends. Stagger them so two T sleeves cannot overlap; retain the low wall tie at 400 mm.',
 'The current fitting profile yields a 689 mm support-pipe axis. Keep all eight saddle screw points on the 704 mm underside plane.'
],lambda id,p:id.startswith(('Desk.shared','Desk.cross','Desk.low','DF0','DF1')) or bool(re.match(r'^(DS0|RF0)\.(joint_riser|extension)$',id)),notes=['No separate short rear desk legs. The two front returns finish below the tabletop; no front-leg holes are required. Leave the final wall anchoring to the verified fixing specification.'],focus='desk')
stage('Fit the desktop and service shelf','Desk module','Keep the full 1,615 × 702 mm surface with a clear front edge.',[
 'While the upper frame is still open, fit the desktop around the continuing rack posts and support it safely during assembly.',
 'Transfer four post clearances from the measured frame. The preview uses Ø44 mm, including two open-edge notches at the near end.',
 'Transfer the shallow underside tee/elbow reliefs from real castings. Do not break through the top face.',
 'Screw the desktop to its eight saddle tabs. Add the 1615 × 230 × 18 mm rear service shelf on two 250 mm T-connected pipes and four saddle tabs, at 500 mm underside / 518 mm top.',
 'The service shelf begins 472 mm behind the front edge. Transfer its two rear post clearances and shallow T-casting reliefs from actual parts. Keep the central knee area open.'
],lambda id,p:id=='Desk.top' or id.startswith('Desk.service'),notes=['Preview top height: 732 mm. This is derived from stock lengths and unmeasured socket offsets; it may change after calibration. Check the near foot and desk corner still clear the kitchen by at least 600 mm.'],focus='desk')
stage('Complete the upper posts','Frame','Feed the pre-staged upper sleeves before closing the upright sections.',[
 'Ordinary posts use 1000 + coupling + 1200 mm. The two cross-bearing desk posts instead use the separate 40 mm riser, coupling and 1500 mm upper tube above the cross; do not run a continuous pipe through the cross.',
 'Stage upper rail/cross-pipe subassemblies in height order before feeding the upper posts through their sleeves.',
 'Keep coupling seating fully engaged; do not shorten or leave a tube partly threaded to adjust the overall height.',
 'Leave the frame loose enough to square it, and retain temporary support until the wall ties are fixed.'
],lambda id,p:bool(re.match(r'^(RF[0-3]|RB[0-3]|DS0|SB0)\.(extension|upper|top_stub|top_extension)$',id)))
stage('Square and brace the frame','Frame','Tie the frame back to the wall using the verified anchor arrangement.',[
 'Install the upper wall ties at their model heights. The near desk ties are at 1,200 and 2,020 mm.',
 'Fit the wardrobe depth bars, including the low 200 mm bars and the 1,800 mm coat-end brace.',
 'Check verticals and diagonals, then secure the verified fasteners and clamp settings.',
 'Keep the bar and kitchen fixed. Confirm the desktop corner gap is approximately 641 mm in the actual flat.'
],lambda id,p:id.startswith(('Desk.wall','Rack.wall','Rack.depth')),notes=['Wall material and permissible fixings remain to be verified. The model does not specify an anchor type or allowable structural load.'])
stage('Add the two short-clothes rows','Hanging storage','The entrance-side wardrobe bay keeps two levels of short hanging storage.',[
 'Fit the 1,000 mm stock rails at 950 and 1,950 mm to their pre-staged sliding T connectors.',
 'Thread both free T branches onto each rail before closing the upright sections.',
 'Keep sleeves off couplings and clear of neighboring clamps.',
 'Check real short garments on both rows before locking the heights.'
],lambda id,p:id.startswith('Rack.clean0'),focus='wardrobe')
stage('Keep a full-length coat drop','Hanging storage','The window-side bay uses the next smaller 602 mm stock rail.',[
 'Fit the 602 mm coat rail at 1,950 mm.',
 'Allow about 70 mm hanger drop and up to 1,500 mm garment length in the design envelope.',
 'Four positions at roughly 140 mm pitch are shown; bulky winter coats may need fewer places.',
 'Keep the curtain gathered and the right balcony door/handle sweep clear.'
],lambda id,p:id.startswith('Rack.clean2'),notes=['The coat-bay width is a stock-pipe decision, not a cut-down 802 mm rail.'],focus='wardrobe')
stage('Add the shelf cross-pipes','Shelf supports','Every ordinary cross-pipe seats into a sliding T on both uprights.',[
 'Build the listed 250 mm cross-pipe/T modules before feeding or closing the corresponding post sections.',
 'Match the model heights for the desk shelves, folded bay, top shelves and coat shoe shelf.',
 'Use the correct shared cross-pipe where two neighboring boards meet.',
 'Keep opposing saddle tabs staggered along a shared pipe so the straps do not collide.'
],lambda id,p:id.startswith('ShelfCross.'),notes=['A saddle holder wraps around a horizontal pipe. It is not a substitute for an upright T clamp.'],focus='frame')
stage('Build the folded-clothes stack','Shelves','Four intermediate boards leave usable spaces for folded pullovers.',[
 'Set the 606 × 350 × 28 mm boards at underside heights 700, 1,100, 1,500 and 1,850 mm.',
 'Use four saddle tabs per board; transfer screw positions from the actual hardware.',
 'Keep the paired folded stacks inside the shelf depth.',
 'Check the 372 / 372 / 322 / 312 mm rear clear openings; the highest front opening is 272 mm behind the light lip.'
],lambda id,p:id.startswith('Rack.fold'),focus='wardrobe')
stage('Cap the storage bays with wood','Shelves','The three top boards finish at 2,218 mm, before the crates.',[
 'Fit the 1,004 mm top over short hanging and the two 606 mm tops over folds and long coats.',
 'Use four saddle tabs per board and preserve the stagger on shared support pipes.',
 'Keep the front edge clear for the removable light covers.',
 'Confirm ceiling height before adding top crates: the model leaves only a small margin at an assumed 2,500 mm.'
],lambda id,p:id.startswith('Rack.top'),focus='wardrobe')
stage('Fit the low coat-bay shelf','Shelves','The long coats retain a low shoe shelf rather than a second hanging row.',[
 'Fit the 606 × 350 × 28 mm board at 200 mm underside height.',
 'Screw it to its four saddle holders.',
 'The preview allows 100 mm shoes above the 228 mm top; verify actual boots and coat hems.',
 'Keep the door-side area free of loose shoes and trailing garments.'
],lambda id,p:id.startswith('Rack.coat_shoes'),focus='wardrobe')
stage('Build the three desk shelves','Desk shelves','The overhead shelves reuse the same main frame as the desk and wardrobe.',[
 'Fit the 1,554 × 350 mm boards at underside heights 1,540, 1,880 and 2,190 mm.',
 'The lowest board is 40 mm thick for the proposed MITTLED pocket; the upper two are 28 mm.',
 'Use four saddles per board and the shared far-end cross-pipe.',
 'Do not route the light pocket until clips, plugs, cable access and suitability of recessed installation are confirmed.'
],lambda id,p:id.startswith('Desk.shelf'),notes=['The proposed 1,320 × 32 × 20 mm underside pocket is unverified. Surface-mounting the original IKEA clips behind a removable wood lip is the alternative.'],focus='desk')
stage('Float and angle the speakers','Speaker module','Two side arms per tray keep the desktop free of speaker legs.',[
 'Attach each tray to two uncut 250 mm arms, each on a sliding T at a separate upright.',
 'Fit four saddle holders per 350 × 350 × 25 mm tray, using the rotated screw layout from the model.',
 'Tray top: 1,125 mm plus an illustrative 3 mm isolation pad. Aim both speakers about 52.9° toward the middle seat.',
 'Check real speaker weight, tweeter height, clamp anti-rotation and screw retention before loading.'
],lambda id,p:id.startswith('Speaker'),notes=['No load rating for this cantilever arrangement has been established. The desk-end placement gives a wide stereo angle, not a calibrated monitor triangle.'],focus='desk')
stage('Give worn clothes their own rail','Hanging storage','The throw-over rail marks clothes that are worn but ready to wear again.',[
 'Use the two 200 mm returns, sliding-T outer fittings and 602 mm rail shown in the graph.',
 'The rail sits at 1,250 mm in front of the folded bay.',
 'Keep the draped item in the front 200 mm zone, y=3,950–4,150 mm.',
 'Leave the rear part toward the balcony clear so the door handle cannot catch clothing.'
],lambda id,p:id.startswith('Wear.'),focus='wardrobe')
stage('Close the ends and recheck joints','Finish the frame','Only close the post ends after every required sleeve and board is in place.',[
 'Fit the listed upright end covers after confirming their actual fit on this DOLLE thread family.',
 'Recheck every structural socket, coupling, wall tie and saddle screw.',
 'Treat caps as covers only, never as load-bearing connections.',
 'Remove temporary support only after the frame and desk fixing checks are complete.'
],lambda id,p:id.endswith('.cover'))
stage('Light the work surface','Lighting','Keep the two original MITTLED bars intact.',[
 'Use two 600 mm MITTLED units with their original mounting clips and compatible leads/driver.',
 'The proposed pocket must retain at least 20 mm timber above it, with access for clips and connectors.',
 'If recess suitability or service clearance cannot be verified, surface-mount behind a removable wood lip.',
 'Route low-voltage leads away from clothes and sharp edges. Keep drivers accessible; do not enclose mains equipment in a routed pocket.'
],notes=['MITTLED load is 11 W on its own compatible driver. No LED strip is shortened.'],focus='desk',extra=['2 × MITTLED 600 mm','Compatible driver and leads','Custom pocket: verification required'])
stage('Hide the upper shelf lighting','Lighting','Warm light comes from intact ÖVERSIDAN bars behind removable oak covers.',[
 'Use one 960 mm, two 460 mm and four 710 mm ÖVERSIDAN bars across the five upper lighting positions.',
 'Use original surface clips inside the open-back wood cover: 18 × 40 mm front lip, 37 × 12 mm return, and removable end cheeks.',
 'Leave access to the screws, connectors and seven intact 3.5 m fixture leads.',
 'Connect the seven bars to the separate 30 W driver: 23.2 W total. Use ON mode for open shelves, rather than relying on wardrobe-door AUTO.'
],notes=['Housing cross sections, clip offsets, local wood reliefs and cable access remain preview dimensions. Keep the existing main ceiling fixture off for the modeled night scene.'],extra=['7 × ÖVERSIDAN','5 × removable oak light covers','1 × separate 30 W driver'])
stage('Add the six crates and equipment','Fit out','Finish the storage without changing the locked layout.',[
 'Place four KNAGGLIG 460 × 310 × 250 mm crates on top and two stacked in the lower folded bay.',
 'Check that top crates can be lifted out below the measured ceiling and secure storage as appropriate.',
 'Fit the reused monitor, 61-key controller and speakers. Put the M1 Mac mini, router and three separated power bricks on the rear service shelf; leave its front/back open and Mac ports facing along the shelf.',
 'Fit the Focusrite and OWC dock beneath opposite front ends using adjustable open U holders. Keep front sockets/knobs accessible and preserve the central 700 mm knee width. Exact Focusrite generation and holder model remain unconfirmed.',
 'Secure individual bricks without covering vents; route audio away from the brick bay and retain cable service loops. Check plug bend space and short tabletop screw lengths.',
 'The shown dock-to-Mac route needs a 2 m certified Thunderbolt lead allowance; the supplied 0.8 m dock cable will not follow this route. Remove the cable allowance if you already own a suitable lead.',
 'Keep the kitchen and bar fixed and use removable finishes. The TV is not part of this layout.'
],extra=['6 × KNAGGLIG crates','Reused M1 Mac mini, router, OWC dock and two-input Focusrite','Two adjustable under-desk device holder sets (allowance)','Removable equipment straps and cable clips'])
stage('Walk through the real room','Final check','A physical fit check completes the concept review.',[
 'Walk the entrance with the chair parked and in use. Preserve at least 600 mm; current modeled corner gap is 640.9 mm.',
 'Open the independent right balcony leaf and check its handle, curtains, coats and worn-clothes rail.',
 'Confirm all doors, drawers and the fixed bar remain usable. The bar has only 240 mm of leg recess.',
 'Test the dimmers and cable access. Check load-bearing fixings with the appropriate installer before loading storage or leaning on the desk.'
],notes=['The public model shows concept geometry and artistically balanced lighting, not a structural or lux certification. The bathroom is only a shell because its fixtures are unknown.'],focus='plan')
assert assigned==set(parts),sorted(set(parts)-assigned)
assert len(assigned)==len(parts)
# Original IKEA-inspired line illustrations, generated from the same graph.
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(v,s):return tuple(x*s for x in v)
def project(v):
 x,y,z=v;return (.86*(y-1300)-.66*(x-2795),-.94*z+.24*(y-1300)+.30*(x-2795))
def esc(v):return html.escape(str(v),quote=True)
def poly(points,stroke,fill='none',width=3):return '<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" stroke="{stroke}" fill="{fill}" stroke-width="{width}" stroke-linejoin="round"/>'
def line(p,q,color,width=5,dash=False):return f'<line x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" y2="{q[1]:.2f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"'+(' stroke-dasharray="12 12"' if dash else '')+'/>'
def draw_part(id,active=False):
 p=parts[id];kind=p['kind'];o=p['origin'];axis=p['axis'];d=p['direction'];color='#17221c' if active else '#d8dcd5';fill='#fff' if active else '#f6f7f3';s=[]
 if kind.startswith('tube_'):
  s.append(line(project(o),project(add(o,mul(axis,p['data']['length']))),color,15 if active else 9))
 elif kind=='wood':
  b=A['boards'][id];c=board_corners(b);z=b['bottom'];top=[project((x,y,z+b['thickness'])) for x,y in c];bottom=[project((x,y,z)) for x,y in c]
  for i in (0,1,2,3):s.append(poly([bottom[i],bottom[(i+1)%4],top[(i+1)%4],top[i]],color,fill,3))
  s.append(poly(top,color,fill,4))
  for x,y,diam in b['holes']:
   ring=[project((x+diam/2*math.cos(t),y+diam/2*math.sin(t),z+b['thickness'])) for t in [j*math.tau/20 for j in range(20)]];s.append(poly(ring,color,'#fff',2.5))
 elif kind=='slide_tee':
  s.append(line(project(add(o,mul(axis,-35))),project(add(o,mul(axis,35))),color,23));s.append(line(project(o),project(add(o,mul(d,30))),color,22))
 elif kind=='cross':
  for v in (axis,d):s.append(line(project(add(o,mul(v,-30))),project(add(o,mul(v,30))),color,23))
 elif kind=='extension':s.append(line(project(add(o,mul(axis,-16))),project(add(o,mul(axis,16))),color,23))
 elif kind=='flange':
  v=(1,0,0) if abs(axis[2])>.9 else (0,1,0);w=(0,1,0) if abs(axis[2])>.9 else (0,0,1)
  ring=[project(add(o,add(mul(v,35*math.cos(t)),mul(w,35*math.sin(t))))) for t in [j*math.tau/20 for j in range(20)]];s.append(poly(ring,color,fill,4))
 elif kind=='elbow':
  s.append(line(project(add(o,mul(axis,20))),project(o),color,23));s.append(line(project(o),project(add(o,mul(d,20))),color,23))
 elif kind=='cap':s.append(line(project(o),project(add(o,mul(axis,4))),color,24))
 elif kind=='saddle':
  s.append(line(project(add(o,(0,0,-14))),project(add(o,mul(d,32))),color,8));s.append(line(project(add(o,mul(d,32))),project(add(add(o,mul(d,32)),(0,0,24))),color,5))
 return ''.join(s)
seen=set()
for st in stages:
 active=set(st['parts']);seen.update(active)
 preview=active or (set(parts) if st['id']<=2 or st['id']>=18 else seen)
 coords=[]
 for id in preview:
  p=parts[id];coords.append(project(p['origin']))
  if p['kind'].startswith('tube_'):coords.append(project(add(p['origin'],mul(p['axis'],p['data']['length']))))
  if p['kind']=='wood':coords.extend(project((x,y,A['boards'][id]['bottom'])) for x,y in board_corners(A['boards'][id]))
 x0=min(x for x,y in coords)-240;x1=max(x for x,y in coords)+240;y0=min(y for x,y in coords)-180;y1=max(y for x,y in coords)+180
 # Limit zoom to keep a meaningful physical context around a small detail.
 if x1-x0<1000:mid=(x0+x1)/2;x0=mid-500;x1=mid+500
 if y1-y0<900:mid=(y0+y1)/2;y0=mid-450;y1=mid+450
 body=[]
 for id in sorted(seen-active,key=lambda id:sum(parts[id]['origin'][:2]),reverse=True):body.append(draw_part(id,False))
 for id in sorted(preview,key=lambda id:sum(parts[id]['origin'][:2]),reverse=True):body.append(draw_part(id,True))
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.2f} {y0:.2f} {x1-x0:.2f} {y1-y0:.2f}" role="img" aria-labelledby="title"><title id="title">Step {st["id"]}: {esc(st["title"])}</title><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff"/>'+''.join(body)+'</svg>'
 (DRAW/f'step-{st["id"]:02}.svg').write_text(svg)
# The equipment sheet shows the separately budgeted adjustable holders as well.
import runpy
runpy.run_path(str(ROOT/'scripts/equipment-diagram.py'))
stages[19]['diagram']='diagrams/equipment.svg'
# Purchase data, model graph and a printable CSV keep the guide independently usable.
metadata={'design':'V18','locked':True,'updated':'2026-10-20','priceBasis':'19–20 October 2026','partCount':len(parts),'pipeCount':sum(n for k,n in counts.items() if k.startswith('tube_')),'boardCount':len(A['boards']),'hardwarePieces':sum(n for k,n in counts.items() if k!='wood'),'lightState':'Practical night lighting · ceiling fixture off','coreBudget':float(t['core_budget']),'withCrates':float(P['six_knagglig_crates']['core_plus_crates_including_contingency_eur']),'optionalAccessories':float(t['optional_accessories']),'entryGap':640.9,'desk':[1615,702,732],'room':[3450,5300,2500],'roomHeightMeasured':False,'verification':['Room height and connector seating offsets not measured','Cantilever, clamp, wood screw and wall-fixing load capacities not certified','Custom MITTLED recess and light-cover details remain provisional','Bathroom fixtures unknown; shell only']}
jwrite(OUT/'project.json',{'meta':metadata,'parts':rows,'stages':stages,'boards':A['boards'],'columns':A['columns'],'graph':A['parts'],'checks':{'allAssignedExactlyOnce':True,'coreBudgetReconciled':round(core,2),'tubeLengths':sorted(STOCK)},'sources':{'repo':'https://github.com/Krydix/FlatPlanning','pages':'https://krydix.github.io/FlatPlanning/'}})
jwrite(OUT/'assembly.json',A)
jwrite(OUT/'equipment.json',json.loads((ROOT/'source/equipment-layout.json').read_text()))
with (ROOT/'public/downloads/bom.csv').open('w',newline='') as f:
 writer=csv.writer(f,lineterminator="\n");writer.writerow(['Category','Part','Description','SKU','Required pieces','Purchase packs','Pack size','Pack/unit price EUR','Line total EUR','Supplier URL','Price / verification note'])
 for r in rows:writer.writerow([r['category'],r['name'],r['description'],r.get('sku',''),r['quantity'],r.get('buyPacks',''),r.get('packSize',''),r.get('unitPrice',''),r['total'],r.get('url',''),r['status']])
with (ROOT/'public/downloads/cut-list.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Board ID','Length mm','Depth mm','Thickness mm','Underside mm','Rotation degrees','Post holes mm','Status'])
 for id,b in A['boards'].items():
  x0,x1,y0,y1=b['bounds'];w.writerow([id,y1-y0,x1-x0,b['thickness'],b['bottom'],b.get('rotation_degrees',0),json.dumps(b['holes']),'CONCEPT ONLY — calibrate fitting profile before cutting'])
print('DATA_READY',json.dumps({'parts':len(parts),'stages':len(stages),'budget':round(core,2),'BOMlines':len(rows)}))

md=['# Complete BOM — V18 connected desk joints','',f"Core estimate **€{metadata['coreBudget']:,.2f}** including 10% reserve. With six crates **€{metadata['withCrates']:,.2f}**.",'','The two cross joints use four female sockets. Rear support pipes now bridge to the middle posts. Low front braces at 400 mm use T fittings at both ends, staggered from the 300 mm rear braces. Cross-bearing posts use 602 + coupling + 40 mm below the cross, then 40 + coupling + 1500 mm above it. No structural stock pipe is cut or stretched.','', 'Crosses carry a €4.00 each budget allowance, not a confirmed shop quote. Other prices retain their dated 19–20 October 2026 basis.','', '| Part | Qty | Packs | Unit/pack € | Total € | Source |','|---|---:|---:|---:|---:|---|']
for r in rows:
 md.append(f"| {r['name']} · {r['description']} | {r['quantity']} | {r.get('buyPacks','—')} | {r.get('unitPrice','—')} | {r['total']:.2f} | {r.get('url') or 'Allowance'} |")
category_totals={category:round(sum(r['total'] for r in rows if r['category']==category),2) for category in dict.fromkeys(r['category'] for r in rows)}
wood_cents=round(category_totals['Wood']*100)
core_cents=round(core*100)
reserve_cents=round(float(t['contingency'])*100)
without_wood_base=core_cents-wood_cents-reserve_cents
without_wood_reserve=round(without_wood_base*.1)
md[4:4]=[f"Without wood: **€{(without_wood_base+without_wood_reserve)/100:,.2f}**, including a recalculated 10% reserve of €{without_wood_reserve/100:,.2f}. Excludes boards, timber waste and light covers; keeps machining and fixings. Add your reclaimed wood cost separately. Crates and optional accessories remain extra.", '', '| Category | Subtotal € |', '|---|---:|', *[f"| {c}{' (extra)' if c in ('Crates','Optional') else ''} | {v:.2f} |" for c,v in category_totals.items()], '', 'Allowances includes the core 10% reserve. Category subtotals reconcile to the listed rows.', '']
md += ['', '## Connection and machining checks' ,'',*A['notes'][-8:],'','Cross seating offsets, exact physical assembly closure, fixings, clamp loads and room height require measurement. The current stock module only closes when measured cross/T/elbow stops match the profile constraints. No final drilling or routing template is supplied.']
(ROOT/'public/downloads/complete-bom.md').write_text('\n'.join(md)+'\n')
