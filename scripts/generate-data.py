"""Derive the site BOM, assembly stages and original line drawings from V18."""
import json,math,csv,io,sys,re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'));sys.path.insert(0,str(ROOT/'scripts'))
from pipe_engine import STOCK,CATALOG
A=json.loads((ROOT/'source/assembly.json').read_text());P=json.loads((ROOT/'source/prices.json').read_text());parts={p['id']:p for p in A['parts']}
OUT=ROOT/'public/data';OUT.mkdir(parents=True,exist_ok=True);DRAW=ROOT/'public/diagrams';DRAW.mkdir(exist_ok=True)
# Room facts and Blender-derived clearances (scripts/check-clearances.py) keep every quoted distance traceable.
ROOM=json.loads((ROOT/'source/room-measurements.json').read_text());CLEAR=json.loads((OUT/'clearances.json').read_text());check={c['id']:c for c in CLEAR['checks']}
from pipe_engine import room_geometry,EAR_MM,ENTRY_CORNER_RADIUS
from speaker_placement import speaker_layout
SPEAKERS=speaker_layout(ROOT);speaker_sep=math.dist(*(s['centre'] for s in SPEAKERS))
GEO=room_geometry();entry=check['entry-passage']['value'];tilt=CLEAR['speaker_tilt_degrees']
DESK=A['boards']['Desk.top'];DESK_TOP=DESK['bottom']+DESK['thickness'];TRAY=A['boards']['Speaker0.platform'];TRAY_SIZE=TRAY['bounds'][1]-TRAY['bounds'][0];toe_in=180-abs(math.degrees(SPEAKERS[0]['yaw']))
labels={'tube_40':'40 mm pipe','tube_200':'200 mm pipe','tube_250':'250 mm pipe','tube_602':'602 mm pipe','tube_802':'802 mm pipe','tube_1000':'1,000 mm pipe','tube_1200':'1,200 mm pipe','tube_1500':'1,500 mm pipe','cross':'Four-way threaded cross','slide_tee':'Sliding T connector','flange':'Ø70 mm mounting flange','extension':'Female–female coupling','elbow':'90° elbow','saddle':'Saddle shelf holder','cap':'End cover','bracket':'Wall shelf bracket (allowance)'}
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
 f'Measure the ceiling height. The top crate envelope reaches about 2,468 mm; {GEO["ceiling"]:,.0f} mm is '+('measured.' if GEO['ceiling_measured'] else 'only the current assumption.'),
 'Measure the room width at three heights, both diagonals and the right-wall plumb. Record them, plus every socket, switch, radiator and pipe, in source/room-measurements.json.',
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
 'Stage the lower sleeves before closing each lower post into its coupling. The two rear desk posts start with a 200 mm tube and a threaded cross at 235 mm instead.',
 'Use floor protection under flanges. Do not assume that a floor flange must be drilled into the rental floor.',
 'Keep the frame braced or held during dry fitting; it is not self-supporting until its wall ties and braces are secured.'
],lambda id,p:bool(re.match(r'^(RF[0-3]|RB[0-3]|DS0|SB0)\.(foot|lower)$',id)),notes=['The near shelf frame is 50 mm before the desk edge frame used in older versions. Keep the V18 axes; moving it back causes a pipe intersection.'])
stage('Build the shared desk supports','Desk module','Crosses where a line continues, sliding Ts where it ends: a low line into the wall at 235 mm, a front brace at 400 mm and the desk-height joints.',[
 'Low line first: each rear post starts with a 200 mm tube and a four-female DOLLE cross at 235 mm. From the cross a 250 mm pipe runs to a sliding T on the middle post and a 40 mm pipe into a wall flange. Above the cross the rear post continues with 1,000 + coupling + 1,000 mm.',
 'Preassemble each free cross/front-arm/elbow module with its 40 mm pipe, coupling and 602 mm front leg. The middle post below the desk cross is 602 + coupling + 40 mm; above it 40 + coupling + 1500 mm.',
 'Fit the desk-height cross at each middle upright: 250 mm front arm into the front-leg elbow, 250 mm rear bridge into the sliding T on the rear upright. Brace the front leg to the middle post with a 250 mm pipe between two sliding Ts at 400 mm; it cannot share the 235 mm station on the middle post.',
 f'The current fitting profile yields a {DESK["bottom"]-15:g} mm support-pipe axis. Keep all eight saddle screw points on the {DESK["bottom"]:g} mm underside plane.'
],lambda id,p:id.startswith(('Desk.shared','Desk.cross','Desk.low','DF0','DF1')) or bool(re.match(r'^(DS0|RF0|SB0|RB0)\.mid$|^(DS0|RF0)\.(joint_riser|extension)$',id)),notes=['No separate short rear desk legs. The two front returns finish below the tabletop; no front-leg holes are required. The cross is a threaded fitting: build each post as a stack of stock sections and stage every sleeve before closing it. Leave the final wall anchoring to the verified fixing specification.'],focus='desk')
stage('Fit the desktop and service shelf','Desk module','Keep the full 1,615 × 702 mm surface with a clear front edge.',[
 'While the upper frame is still open, fit the desktop around the continuing rack posts and support it safely during assembly.',
 'Transfer four post clearances from the measured frame. The preview uses Ø44 mm, including two open-edge notches at the near end.',
 'Transfer the shallow underside tee/elbow reliefs from real castings. Do not break through the top face.',
 f'Round the entrance-side front corner to R{ENTRY_CORNER_RADIUS} mm. It widens the kitchen-corner passage; the nearest saddle screw stays on full-width timber.',
 'Screw the desktop to its eight saddle tabs. Hang the 1615 × 230 × 18 mm rear service shelf on four separate wall shelf brackets at 500 mm underside / 518 mm top; it is not part of the pipe frame.',
 'The service shelf begins 472 mm behind the front edge. Choose the brackets (about 200 mm reach) and their wall fixings for the real wall; the budget carries an allowance only. Transfer its two rear post clearances from actual parts and keep the central knee area open.'
],lambda id,p:id=='Desk.top' or id.startswith('Desk.service'),notes=[f'Preview top height: {DESK_TOP:g} mm. This is derived from stock lengths and unmeasured socket offsets; it may change after calibration.',f'Kitchen-corner passage in the model: {entry:.0f} mm, limited by the low front brace on the near leg rather than the desk corner. Keep at least 600 mm.'],focus='desk')
stage('Complete the upper posts','Frame','Feed the pre-staged upper sleeves before closing the upright sections.',[
 'Ordinary wardrobe posts use 1000 + coupling + 1200 mm. The two middle desk posts use the separate 40 mm riser, coupling and 1500 mm upper tube above the desk cross; the two rear desk posts use 1000 + coupling + 1000 mm above their low cross. Do not run a continuous pipe through a cross.',
 'Stage upper rail/cross-pipe subassemblies in height order before feeding the upper posts through their sleeves.',
 'Keep coupling seating fully engaged; do not shorten or leave a tube partly threaded to adjust the overall height.',
 'Leave the frame loose enough to square it, and retain temporary support until the wall ties are fixed.'
],lambda id,p:bool(re.match(r'^(RF[0-3]|RB[0-3]|DS0|SB0)\.(extension|upper|top_stub|top_extension)$',id)))
stage('Square and brace the frame','Frame','Tie the frame back to the wall using the verified anchor arrangement.',[
 'Install the upper wall ties at their model heights. The near desk ties are at 1,200 and 2,020 mm.',
 'Fit the wardrobe depth bars: the low 200 mm bar under the folded bay and the 1,800 mm coat-end brace. The low wall ties under the desk are already part of the rear cross line.',
 'Check verticals and diagonals, then secure the verified fasteners and clamp settings.',
 f'Keep the bar and kitchen fixed. Confirm the kitchen-corner passage is about {entry:.0f} mm in the actual flat.'
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
 f'Top crates reach about 2,468 mm, {check["ceiling-storage"]["value"]:.0f} mm below the '+('measured' if GEO['ceiling_measured'] else 'ASSUMED')+f' {GEO["ceiling"]:,.0f} mm ceiling; check the actual top shelf with a crate before loading it.'
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
stage('Float the speakers inside the shelf column','Speaker module','Two side arms per tray; the trays sit between the middle and rear posts, so nothing overhangs the desktop.',[
 'Attach each tray to two uncut 250 mm arms, each on a sliding T at a separate upright.',
 f'Fit four saddle holders per {TRAY_SIZE:g} × {TRAY_SIZE:g} × 25 mm tray. The trays are square to the frame, flush with the shelf fronts, and mirrored about the desk centre line.',
 f'Tray top: {TRAY["bottom"]+TRAY["thickness"]:,} mm. Turn each speaker about {toe_in:.0f}° on its tray so it faces the seated ear reference (x {EAR_MM[0]:,}, z {EAR_MM[1]:,} mm), not the seat centre. {TRAY_SIZE:g} mm is the smallest square that takes the turned speaker with a 5 mm edge margin.',
 f'Each speaker sits centred on its tray, fully supported, at least 15 mm from the nearest frame part. The speakers end up about {speaker_sep:,.0f} mm apart and {SPEAKERS[0]["wall_gap"]:.0f} mm from the wall.',
 f'Tilt each speaker about {tilt:g}° down on angled isolation pads.',
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
],notes=['Two 5.5 W MITTLED bars draw 11 W together on their own compatible driver. No LED strip is shortened.'],focus='desk',extra=['2 × MITTLED 600 mm','Compatible driver and leads','Custom pocket: verification required'])
stage('Hide the upper shelf lighting','Lighting','Warm light comes from intact ÖVERSIDAN bars behind removable oak covers.',[
 'Use one 960 mm, two 460 mm and four 710 mm ÖVERSIDAN bars across the five upper lighting positions.',
 'Use original surface clips inside the open-back wood cover: 18 × 40 mm front lip, 37 × 12 mm return, and removable end cheeks.',
 'Leave access to the screws, connectors and seven intact 3.5 m fixture leads.',
 'Connect the seven bars to the separate 30 W driver: 23.2 W total. Use ON mode for open shelves, rather than relying on wardrobe-door AUTO.'
],notes=['Housing cross sections, clip offsets, local wood reliefs and cable access remain preview dimensions. Keep the existing main ceiling fixture off for the modeled night scene.'],extra=['7 × ÖVERSIDAN','5 × removable oak light covers','1 × separate 30 W driver'])
stage('Add the six crates and equipment','Fit out','Finish the storage without changing the locked layout.',[
 'Place four KNAGGLIG 460 × 310 × 250 mm crates on top and two stacked in the lower folded bay.',
 'Check that top crates can be lifted out below the measured ceiling and secure storage as appropriate.',
 'Fit the reused monitor on the optional desk-clamp VESA arm at the desktop rear edge; no monitor stand fits behind the 61-key controller. Keep the clamp jaw clear of the router antennas.',
 'Put the M1 Mac mini, router, and the router and dock power supplies on the rear service shelf; leave its front/back open and Mac ports facing along the shelf. The Mac mini M1 has an internal power supply, so the third brick bay is spare.',
 'Fit the Focusrite and OWC dock beneath opposite front ends using adjustable open U holders. Keep front sockets/knobs accessible and preserve the central 700 mm knee width. Exact Focusrite generation and holder model remain unconfirmed.',
 'Secure individual bricks without covering vents; route audio away from the brick bay and retain cable service loops. Check plug bend space and short tabletop screw lengths.',
 'The shown dock-to-Mac route needs a 2 m certified Thunderbolt lead allowance; the supplied 0.8 m dock cable will not follow this route. Remove the cable allowance if you already own a suitable lead.',
 'Keep the kitchen and bar fixed and use removable finishes. The TV is not part of this layout.'
],extra=['6 × KNAGGLIG crates','Reused M1 Mac mini, router, OWC dock and two-input Focusrite','Two adjustable under-desk device holder sets (allowance)','Removable equipment straps and cable clips'])
stage('Walk through the real room','Final check','A physical fit check completes the concept review.',[
 f'Walk the entrance with the chair parked and in use. Preserve at least 600 mm; the modelled kitchen-corner passage is {entry:.0f} mm.',
 'Open the independent right balcony leaf and check its handle, curtains, coats and worn-clothes rail.',
 'Confirm all doors, drawers and the fixed bar remain usable. The bar has only 240 mm of leg recess.',
 'Test the dimmers and cable access. Check load-bearing fixings with the appropriate installer before loading storage or leaning on the desk.'
],notes=['The public model shows concept geometry and artistically balanced lighting, not a structural or lux certification. The bathroom is only a shell because its fixtures are unknown.'],focus='plan')
assert assigned==set(parts),sorted(set(parts)-assigned)
assert len(assigned)==len(parts)
# Original IKEA-inspired line illustrations, generated from the same graph.
from guide_drawing import draw_guide
draw_guide(stages,parts,A['boards'],DRAW)
# The equipment sheet shows the separately budgeted adjustable holders as well.
import runpy
runpy.run_path(str(ROOT/'scripts/equipment-diagram.py'))
stages[19]['diagram']='diagrams/equipment.svg'
# Purchase data, model graph and a printable CSV keep the guide independently usable.
metadata={'design':'V18','locked':True,'updated':'2026-10-20','priceBasis':'19–20 October 2026','partCount':len(parts),'pipeCount':sum(n for k,n in counts.items() if k.startswith('tube_')),'boardCount':len(A['boards']),'hardwarePieces':sum(n for k,n in counts.items() if k!='wood'),'lightState':'Afternoon daylight · ceiling fixture off','coreBudget':float(t['core_budget']),'withCrates':float(P['six_knagglig_crates']['core_plus_crates_including_contingency_eur']),'optionalAccessories':float(t['optional_accessories']),'entryGap':entry,'desk':[1615,702,DESK_TOP],'room':[GEO['wall_x'],ROOM['assumed']['room_length_y'],GEO['ceiling']],'roomHeightMeasured':GEO['ceiling_measured'],'roomWidthMeasured':GEO['wall_measured'],'servicesSurveyed':ROOM['services']['status']!='not surveyed','verification':['Room '+' and '.join(x for x,m in (('width and length',GEO['wall_measured']),('height',GEO['ceiling_measured'])) if not m)+' still the CAD assumption'+(f'; ceiling measured at {GEO["ceiling"]:,.0f} mm' if GEO['ceiling_measured'] else '') if not (GEO['wall_measured'] and GEO['ceiling_measured']) else 'Room dimensions are measured','Sockets, switches, radiators and pipes are not surveyed','Connector seating offsets not measured','Cantilever, clamp, wood screw and wall-fixing load capacities not certified','Custom MITTLED recess and light-cover details remain provisional','Bathroom fixtures unknown; shell only']}
def dim(id,label,a,b,value,basis):return {'id':id,'label':label,'a':a,'b':b,'value':round(value,1),'basis':basis}
c=check['ceiling-storage']['points'];e=check['entry-passage']['points'];bed=check['bed-aisle']['points']
room_basis='measured' if GEO['wall_measured'] else 'assumed';ceiling_basis='measured' if GEO['ceiling_measured'] else 'assumed'
dimensions=[dim('room-width','Room width',[0,5550,50],[GEO['wall_x'],5550,50],GEO['wall_x'],room_basis),dim('room-length','Room length',[-220,0,50],[-220,5300,50],5300,'assumed'),
 dim('ceiling','Ceiling height',[60,5240,0],[60,5240,GEO['ceiling']],GEO['ceiling'],ceiling_basis),dim('entry','Kitchen-corner passage',e[0],e[1],entry,'model'),
 dim('desk-height','Desktop height',[2700,2020,0],[2700,2020,DESK_TOP],DESK_TOP,'preview'),dim('crate-ceiling','Top crates to ceiling',c[0],c[1],check['ceiling-storage']['value'],ceiling_basis),
 dim('bed-aisle','Bed to desk aisle',bed[0],bed[1],check['bed-aisle']['value'],'model')]
jwrite(OUT/'project.json',{'meta':metadata,'dimensions':dimensions,'clearances':CLEAR,'parts':rows,'stages':stages,'boards':A['boards'],'columns':A['columns'],'graph':A['parts'],'checks':{'allAssignedExactlyOnce':True,'coreBudgetReconciled':round(core,2),'tubeLengths':sorted(STOCK)},'sources':{'repo':'https://github.com/Krydix/FlatPlanning','pages':'https://krydix.github.io/FlatPlanning/'}})
jwrite(OUT/'assembly.json',A)
jwrite(OUT/'equipment.json',json.loads((ROOT/'source/equipment-layout.json').read_text()))
with (ROOT/'public/downloads/bom.csv').open('w',newline='') as f:
 writer=csv.writer(f,lineterminator="\n");writer.writerow(['Category','Part','Description','SKU','Required pieces','Purchase packs','Pack size','Pack/unit price EUR','Line total EUR','Supplier URL','Price / verification note'])
 for r in rows:writer.writerow([r['category'],r['name'],r['description'],r.get('sku',''),r['quantity'],r.get('buyPacks',''),r.get('packSize',''),r.get('unitPrice',''),r['total'],r.get('url',''),r['status']])
with (ROOT/'public/downloads/cut-list.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Board ID','Length mm','Depth mm','Thickness mm','Underside mm','Rotation degrees','Post holes mm','Corner radii mm','Status'])
 for id,b in A['boards'].items():
  x0,x1,y0,y1=b['bounds'];w.writerow([id,y1-y0,x1-x0,b['thickness'],b['bottom'],b.get('rotation_degrees',0),json.dumps(b['holes']),json.dumps(b.get('corner_radii',[])),'CONCEPT ONLY — calibrate fitting profile before cutting'])
print('DATA_READY',json.dumps({'parts':len(parts),'stages':len(stages),'budget':round(core,2),'BOMlines':len(rows)}))

md=['# Complete BOM — V18 cross-braced desk module','',f"Core estimate **€{metadata['coreBudget']:,.2f}** including 10% reserve. With six crates **€{metadata['withCrates']:,.2f}**.",'','Four four-female crosses. At desk height a cross on each middle post joins the 250 mm front arm and the 250 mm rear bridge. At 235 mm a cross on each rear post takes a 250 mm pipe from a sliding T on the middle post and a 40 mm pipe into a wall flange; the front leg is braced to the middle post by a 250 mm sliding-T bridge at 400 mm. Middle posts stack 602 + coupling + 40, cross, 40 + coupling + 1500 mm; rear posts 200, cross, 1000 + coupling + 1000 mm. The rear service shelf hangs on four separate wall brackets (allowance). No structural stock pipe is cut or stretched.','', 'Crosses carry a €4.00 each budget allowance, not a confirmed shop quote. Other prices retain their dated 19–20 October 2026 basis.','', '| Part | Qty | Packs | Unit/pack € | Total € | Source |','|---|---:|---:|---:|---:|---|']
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
# The downloadable Blender add-on bundles the same engine, adapter and room/fitting sources.
import zipfile
with zipfile.ZipFile(ROOT/'public/downloads/dolle-editor-v18.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name,source in (('__init__.py','dolle_editor_addon.py'),('pipe_engine.py','pipe_engine.py'),('blender_components.py','blender_components.py'),('Measurements-v8.json','Measurements-v8.json'),('room-measurements.json','room-measurements.json'),('portal-layout.json','portal-layout.json')):
  info=zipfile.ZipInfo('dolle_pipe_editor/'+name,date_time=(2026,10,21,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(ROOT/'source'/source).read_bytes())
