"""Derive the portal variant's BOM, assembly stages and line drawings from its own graph.
V18's data (scripts/generate-data.py) is left alone. Prices reuse the dated V18 inputs: hardware by
unit, timber by area at the same rate per thickness, and scaled allowances for the extra machining.
"""
import json,math,csv,sys,re,statistics
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'source'));sys.path.insert(0,str(ROOT/'scripts'))
from pipe_engine import STOCK,CATALOG,room_geometry
from guide_drawing import draw_guide
A=json.loads((ROOT/'source/assembly-portal.json').read_text());P=json.loads((ROOT/'source/prices.json').read_text());L=json.loads((ROOT/'source/portal-layout.json').read_text());parts={p['id']:p for p in A['parts']}
OUT=ROOT/'public/data';DRAW=ROOT/'public/diagrams/portal';DRAW.mkdir(parents=True,exist_ok=True);DL=ROOT/'public/downloads'
ROOM=json.loads((ROOT/'source/room-measurements.json').read_text());CLEAR=json.loads((OUT/'clearances-portal.json').read_text());check={c['id']:c for c in CLEAR['checks']};GEO=room_geometry()
G=A['portal'];xs=G['xs'];yf,yb=G['rows'];levels=L['levels'];crate=L['crate']['size'];shift=G['desk_offset'];assert not A['validation']['geometry_errors']
labels={'tube_40':'40 mm pipe','tube_200':'200 mm pipe','tube_250':'250 mm pipe','tube_602':'602 mm pipe','tube_802':'802 mm pipe','tube_1000':'1,000 mm pipe','tube_1200':'1,200 mm pipe','tube_1500':'1,500 mm pipe','cross':'Four-way threaded cross','slide_tee':'Sliding T connector','flange':'Ø70 mm mounting flange','extension':'Female–female coupling','elbow':'90° elbow','saddle':'Saddle shelf holder','cap':'End cover'}
def show(id):
 m=re.match(r'Portal\.shelf([LR])(\d)',id)
 if m:return f"Divider · {'left' if m[1]=='L' else 'right'} shelf {int(m[2])+1}"
 m=re.match(r'Portal\.cap([LR])\d',id)
 if m:return f"Divider · {'left' if m[1]=='L' else 'right'} crown step"
 if id.startswith('Portal.lintel'):return 'Divider · lower lintel' if id.endswith('0') else 'Divider · upper lintel'
 return id.replace('Rack.','Wardrobe · ').replace('Desk.','Desk · ').replace('Speaker0','Speaker L').replace('Speaker1','Speaker R')
def jwrite(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
cents=lambda v:round(float(v)*100)
counts=Counter(p['kind'] for p in parts.values());rows=[]
for r in P['hardware']:
 q=counts[r['kind']];packs=math.ceil(q/r['units_per_pack']);total=packs*float(r['unit_eur'])
 rows.append({'id':r['kind'],'category':'Hardware','name':labels.get(r['kind'],r['name']),'description':r['name']+(' · €4 each budget allowance; verify store price' if r['kind']=='cross' else ''),'sku':CATALOG[r['kind']]['sku'],'quantity':q,'buyPacks':packs,'packSize':r['units_per_pack'],'unitPrice':float(r['unit_eur']),'total':round(total,2),'url':r['source'],'status':r['status'],'purchase':True})
assert {k for k in counts if k!='wood'}=={r['kind'] for r in P['hardware']}
# Timber keeps V18's dated rate per thickness; only the areas change.
rate=defaultdict(list)
for r in P['wood']:rate[r['thickness_mm']].append(float(r['net_eur']['base'])/float(r['area_m2']))
rate={k:statistics.median(v) for k,v in rate.items()}
timber=0
for id,b in A['boards'].items():
 x0,x1,y0,y1=b['bounds'];w,d=(y1-y0,x1-x0);length,depth=max(w,d),min(w,d);net=round(w*d/1e6*rate[b['thickness']],2);timber+=net
 rows.append({'id':'wood:'+id,'category':'Wood','name':show(id),'description':f"{length:g} × {depth:g} × {b['thickness']:g} mm · oak allowance",'quantity':1,'buyPacks':1,'packSize':1,'unitPrice':net,'total':net,'url':None,'status':'Concept dimensions, not final machining sizes. Timber supplier not selected.','holes':len(b['holes']),'purchase':True})
t=P['totals']['base'];waste=round(timber*.15,2)
rows.append({'id':'wood-yield','category':'Wood','name':'Timber yield allowance','description':'15% material waste on the structural oak panels','quantity':1,'total':waste,'url':None,'status':'Budget allowance','purchase':False})
rows.append({'id':'light-lips','category':'Wood','name':'Five removable oak light covers','description':'Same five covers as V18: two desk, two wardrobe, one turned to the lintel','quantity':5,'total':float(t['lip_with_waste']),'url':None,'status':'Custom joinery allowance; verify access and fitting reliefs.','purchase':True})
BARS46=4
for i,r in enumerate(P['lighting']):
 q=BARS46 if r['name'].startswith('ÖVERSIDAN 46') else r['quantity'];rows.append({'id':'light:'+str(i),'category':'Lighting','name':r['name'],'description':'Intact original IKEA fixture or driver/lead'+(' · two extra bars under the top divider shelves' if q!=r['quantity'] else ''),'quantity':q,'buyPacks':q,'packSize':1,'unitPrice':float(r['unit_eur']),'total':round(q*float(r['unit_eur']),2),'url':r['source'],'status':'Retained 19 October 2026 price input','purchase':True})
for i,r in enumerate(P['base_allowances']):
 rows.append({'id':'allowance:'+str(i),'category':'Allowances','name':r['name'],'description':'Working budget allowance','quantity':r['quantity'],'unitPrice':float(r['base'])/r['quantity'],'total':float(r['base']),'url':None,'status':'Not a supplier quote','purchase':False})
gap=round(float(t['other_allowances'])-sum(float(r['base']) for r in P['base_allowances']),2)
rows.append({'id':'lip-fixings','category':'Allowances','name':'Light-cover fixings and extra cuts','description':'Small brackets, short wood screws and removable-cover joinery','quantity':1,'total':gap,'url':None,'status':'Budget allowance','purchase':False})
extra_boards=len(A['boards'])-15;bores=sum(len(b['holes']) for k,b in A['boards'].items() if k.startswith('Portal.'))
rows.append({'id':'portal-machining','category':'Allowances','name':'Divider board machining','description':f'{extra_boards} extra boards at V18\'s rate per board, {bores} post bores and shallow T reliefs','quantity':1,'total':round(100/15*extra_boards,2),'url':None,'status':'Allowance scaled from V18, not a quote','purchase':False})
rows.append({'id':'portal-fixings','category':'Allowances','name':'Ceiling and extra wall fixings','description':'Four ceiling ties and four divider wall ties; choose after checking the ceiling and wall construction','quantity':1,'total':30.0,'url':None,'status':'Allowance, not a quote; ceiling construction unknown','purchase':False})
base=sum(r['total'] for r in rows);reserve=round(base*.1,2)
rows.append({'id':'contingency','category':'Allowances','name':'Contingency · 10%','description':'Reserve on the core frame, wood, lights and allowances','quantity':1,'total':reserve,'url':None,'status':'Budget reserve','purchase':False})
core=round(base+reserve,2);with_crates=round(core+59.94*1.1,2)
rows.append({'id':'knagglig','category':'Crates','name':'KNAGGLIG · pine crate','description':f'{crate[0]} × {crate[1]} × {crate[2]} mm · six in the band above the door, three across and two high','quantity':6,'buyPacks':6,'packSize':1,'unitPrice':9.99,'total':59.94,'url':'https://www.ikea.com/de/de/p/knagglig-kasten-kiefer-70292359/','status':'Retained 20 October 2026 price; extra to core budget','purchase':True,'optional':True})
for i,r in enumerate(P['optional_allowances']):
 rows.append({'id':'optional:'+str(i),'category':'Optional','name':r['name'],'description':'Optional accessory allowance; no exact product selected','quantity':1,'total':float(r['base']),'url':None,'status':'Not a supplier quote; extra to core budget','purchase':True,'optional':True})
head=check['portal-head']['value'];floor_w=check['portal-floor-width']['value'];shoulder=check['portal-shoulder']['value'];exit_w=check['portal-exit']['value'];aisle=check['bed-aisle']['value'];crate_gap=check['ceiling-storage']['value']
ceiling=('measured' if GEO['ceiling_measured'] else 'ASSUMED')+f' {GEO["ceiling"]:,.0f} mm'
assigned=set();stages=[]
def stage(title,kicker,description,actions,selector=None,notes=None,focus='frame',extra=None,show_all=False):
 ids=sorted(id for id,p in parts.items() if id not in assigned and selector and selector(id,p));assigned.update(ids);n=len(stages)+1
 row={'id':n,'title':title,'kicker':kicker,'description':description,'actions':actions,'notes':notes or [],'parts':ids,'materials':[{'kind':k,'name':labels.get(k,k),'quantity':c,'sku':CATALOG.get(k,{}).get('sku'),'url':CATALOG.get(k,{}).get('source')} for k,c in sorted(Counter(parts[id]['kind'] for id in ids).items())],'focus':focus,'extra':extra or [],'diagram':f'diagrams/portal/step-{n:02}.svg'}
 row['showAll']=show_all
 stages.append(row)
post=lambda i,*names:(lambda id,p:bool(re.match(r'^P[FB][0-3]\.('+'|'.join(names)+')$',id)))
stage('Measure the door before making it','Preparation','The divider depends on the ceiling, the bar end and the back of the bar. Check all three first.',[
 f'Measure the ceiling where the divider stands, at both ends and in the middle. The model uses {ceiling}; the crates and lintel heights are derived from it.',
 f'Confirm the bar end at x {L["fixed"]["bar_end_x"]:,} mm and bar back at y {L["fixed"]["bar_back_y"]:,} mm from the walls. These come from the CAD model, not a site survey.',
 'Find out what the ceiling is made of. Four ties fix into it; concrete, hollow blocks and a suspended ceiling each need a different answer.',
 'Check the right wall for pipes and cables at the four divider wall ties.',
 f'Mock up the door with tape: {2*G["half_width"]:,} mm at its widest, {floor_w:,.0f} mm at the floor, {head:,.0f} mm high.'
],notes=['This is a checked geometry proposal, not a certified load rating or a drilling template. The ceiling ties are drawn, not designed: have them checked.'],focus='plan',show_all=True)
stage('Lay out the kit','Preparation','Sort pipes by their printed lengths. There are many more T connectors than in V18.',[
 'Use only the listed DOLLE PIPE family; do not mix generic plumbing threads or change a stock pipe length.',
 f'Sort {counts["slide_tee"]} sliding T connectors by post before starting. Each post carries its own stack.',
 'Dry-fit one T/pipe/saddle/board connection, and measure the seating stops into the fitting profile.',
 'Assemble cross-pipe modules while the T sleeves are free, then feed the posts through. Do not try to screw a rigid closed frame together.'
],show_all=True)
stage('Stage the divider posts','Divider','Six new posts join the two near desk posts, which finish the rear row at the wall end.',[
 f'Set out post centres at x {xs[0]:,.0f}, {xs[1]:,.0f}, {xs[2]:,.0f} and {xs[3]:,.0f} mm, in two rows at y {yf:,.0f} and {yb:,.0f} mm. The desk posts take the last two rear positions, so nothing is doubled.',
 'Load every sleeve for the 1,000 mm lower section before closing it into its coupling.',
 'Use floor protection under flanges. The frame is not self-supporting until it is tied to the wall and ceiling.',
],lambda id,p:bool(re.match(r'^P[FB][0-3]\.(foot|lower)$',id)))
stage('Complete the divider posts','Divider','1,500 mm upper sections finish well below the ceiling, so the posts stay uncut stock.',[
 'Load the upper sleeves, then close each post through its coupling.',
 f'Posts top out at about {parts["PF0.upper"]["origin"][2]+1000:,.0f} mm. The gap to the ceiling is taken up by the sliding T ties, not by cutting a pipe.',
 'Keep the frame loosely propped until the ties are in.'
],lambda id,p:bool(re.match(r'^P[FB][0-3]\.(extension|upper)$',id)))
stage('Fit the tower cross-pipes','Divider','Each shelf level hangs on 250 mm cross-pipes between the front and rear posts.',[
 f'Fit cross-pipes at {", ".join(f"{z-15:,}" for z in levels)} mm for the stepped shelves. Levels with a long overhang use arms instead on the inner posts.',
 f'Fit the lintel cross-pipes at {G["lintel"]-15:,.0f} and {G["upper"]-15:,.0f} mm on all four post pairs, and the tie cross-pipes at {G["tie_z"]:,.0f} mm.',
 'Each T has a single branch, so two pipes can never share one sleeve.'
],lambda id,p:id.startswith(('ShelfCross.PF','Portal.front')))
stage('Tie it to the ceiling and wall','Divider','Four ceiling ties and four wall ties stop the divider from tipping.',[
 f'Slide a T onto each tie cross-pipe, fit the 200 mm pipe and bring its flange to the ceiling at {GEO["ceiling"]:,.0f} mm.',
 'Because the T slides, a slightly different ceiling moves the tie rather than changing a pipe.',
 f'Fit the wall ties at {" and ".join(f"{z:,}" for z in L["frame"]["wall_tie_heights"])} mm on the front post and the rear desk post of the wall-side pair.',
 'Square the frame and check it is plumb before fitting any boards.'
],lambda id,p:id.startswith(('Portal.tie','Portal.wall')),notes=['Ceiling construction and fixings are unknown. No load capacity is implied by this model.'])
stage('Hang the stepped shelves','Divider','This is where the door appears: each board stops at the curve.',[
 f'Fit the {2*len(levels)} boards at underside heights {", ".join(f"{z:,}" for z in levels)} mm, left and right.',
 'Transfer the 44 mm post bores and shallow T reliefs from the real frame. Do not trust the preview numbers.',
 'Cut the inner ends last, against a full-size template of the opening. Left and right mirror each other.',
 'At 315 mm the right-hand shelf reuses the desk\'s low brace as its rear support, so only a front pipe is added.',
 'The top level sits on capped arms. Keep it to light things: no books, no plants that need watering overhead.'
],lambda id,p:id.startswith('Portal.shelf'),notes=['The arms are cantilevers with no manufacturer rating, as on the speaker trays.'])
stage('Close the crown','Divider','Two short floating steps finish the top of the circle.',[
 'Fit each board on two capped arms and four saddles.',
 f'Underside height {L["cap_steps"][0]:,} mm. Check head room with the people who actually live here.',
 'Keep these empty or nearly so.'
],lambda id,p:id.startswith('Portal.cap'))
stage('Build the crate band','Divider','Two continuous boards carry all six crates above the door.',[
 f'Fit the lower lintel at {G["lintel"]:,.0f} mm on its end pipes and the central rail, which is 1,200 + coupling + 200 mm between the inner cross-pipes.',
 f'Fit the upper lintel at {G["upper"]:,.0f} mm on its end pipes only: a rail there would run straight through the crates.',
 'Each board has eight post bores. A 2,092 mm oak board is long; check you can get it into the flat before ordering.',
 f'Check a real crate on the board: {crate[0]} × {crate[1]} × {crate[2]} mm between the inner posts, with {crate_gap:.0f} mm left above the top row.'
],lambda id,p:id.startswith(('Portal.lintel','Portal.rail')),notes=[f'The door head is {head:,.0f} mm, set by the oak light cover. A lower ceiling lowers it too.'])
stage('Stage the desk and wardrobe posts','Frame','The whole desk module stands behind the divider, unchanged.',[
 f'The desk block moves {shift:,.0f} mm toward the balcony compared with V18, as one rigid unit, until its near posts are the rear divider row.',
 'Those two posts carry both sets of sleeves. Stage them from the full list; their lower parts are the crowded ones.',
 'Their wall ties move to the divider heights, and they run on above the desk to reach the ceiling ties.',
 'Stage the lower sleeves and braces before closing each lower post.'
],lambda id,p:bool(re.match(r'^(RF[0-2]|RB[0-2]|DS0|SB0)\.(foot|lower)$',id)),focus='desk')
stage('Build the shared desk supports','Desk module','The same joints as V18: a rear cross line at 235 mm, a front brace at 400 mm and the desk-height crosses.',[
 'Low line first: a 200 mm tube and a four-female cross at 235 mm on each rear post, with a 250 mm pipe to a sliding T on the middle post and a 40 mm pipe into a wall flange. The rear posts continue with a 1,000 mm tube.',
 'Preassemble each cross/front-arm/elbow module with its 40 mm pipe, coupling and 602 mm front leg, and brace the leg to the middle post with a 250 mm sliding-T bridge at 400 mm.',
 'Fit the desk-height cross at each middle upright with its 250 mm front arm and rear bridge.'
],lambda id,p:id.startswith(('Desk.shared','Desk.cross','Desk.low','DF0','DF1')) or bool(re.match(r'^(DS0|RF0|SB0|RB0)\.mid$|^(DS0|RF0)\.(joint_riser|extension)$',id)),focus='desk')
stage('Fit the desktop and service shelf','Desk module','The same 1,615 × 702 mm surface, with its R100 corner now facing the door.',[
 'Fit the desktop around the continuing posts and screw it to its eight saddle tabs.',
 'Hang the rear service shelf on four separate wall shelf brackets (allowance); it is not part of the pipe frame.',
 f'The rounded corner sits on your way through the door. {exit_w:,.0f} mm is left between it and the left edge of the opening at the floor.'
],lambda id,p:id=='Desk.top' or id.startswith('Desk.service'),focus='desk')
stage('Complete the upper posts','Frame','Feed the pre-staged sleeves before closing the desk and wardrobe posts.',[
 'Ordinary wardrobe posts use 1000 + coupling + 1200 mm. The rear wall-side desk posts use 1000 + coupling + 1200 mm (near) and 1000 + coupling + 1000 mm (far) above their low cross. The near middle post continues with 602 + coupling + 1200 mm above its riser; the far one keeps its 1500 mm tube.',
 'Keep couplings fully seated; never leave a tube partly threaded to adjust the height.'
],lambda id,p:bool(re.match(r'^(RF[0-2]|RB[0-2]|DS0|SB0)\.(extension|upper|upper2|top_stub|top_extension|top_extension2)$',id)))
stage('Square and brace the frame','Frame','Tie the desk and wardrobe back to the wall.',[
 'Install the upper wall ties at their model heights.',
 'Fit the wardrobe depth bars, including the 1,800 mm coat-end brace.',
 'Check verticals and diagonals, then secure the verified fasteners.'
],lambda id,p:id.startswith(('Desk.wall','Rack.wall','Rack.depth')),notes=['Wall material and permissible fixings remain to be verified.'])
stage('Fit the hanging rails','Hanging storage','One short bay with two rails, and one coat bay.',[
 'Fit the 602 mm rails at 950 and 1,950 mm in the short bay, and at 2,030 mm in the coat bay.',
 'The coat rail sits 80 mm higher because both rails meet at one post, and two sleeves cannot share a height.',
 'About seven short garments fit per rail and four coats. That is less hanging space than V18.'
],lambda id,p:id.startswith('Rack.clean'),focus='wardrobe')
stage('Add the shelves','Shelves','Cross-pipes, desk shelves and wardrobe tops.',[
 'Build the listed 250 mm cross-pipe modules before closing the post sections.',
 'Fit the three 1,554 × 350 mm desk shelves at 1,540, 1,880 and 2,190 mm.',
 'Fit the two 606 mm wardrobe tops and the low shoe shelf at 200 mm.',
 'Keep opposing saddle tabs staggered on shared pipes.'
],lambda id,p:id.startswith(('ShelfCross.','Desk.shelf','Rack.top','Rack.coat_shoes')),focus='desk')
stage('Float and angle the speakers','Speaker module','Unchanged from V18, just further along the wall.',[
 'Attach each tray to two uncut 250 mm arms, each on a sliding T at a separate upright.',
 'Fit four saddle holders per tray, using the rotated screw layout from the model.',
 'Tilt each speaker down on angled isolation pads.'
],lambda id,p:id.startswith('Speaker'),notes=['No load rating for this cantilever arrangement has been established.'],focus='desk')
stage('Close the post ends','Finish the frame','Only close the posts after every sleeve and board is in place.',[
 'Fit the end covers after confirming their fit on this thread family. Covers carry no load.',
 'Recheck every socket, coupling, tie and saddle screw.'
],lambda id,p:id.endswith('.cover'))
stage('Light the door','Lighting','The 960 mm bar and its oak cover turn 90° and sit over the opening.',[
 'Fit the 960 mm ÖVERSIDAN under the lower lintel behind its oak cover, on the kitchen side.',
 'Fit two 460 mm bars under the top full shelves, left and right.',
 'Keep the other bars as in V18. Nine bars on the 30 W driver come to about 27.7 W, so check the driver rating.',
 'Keep drivers accessible; do not enclose mains equipment.'
],notes=['Bar wattages are scaled from V18 by length. Check the printed rating of each bar.'],extra=['1 × ÖVERSIDAN 96 cm','4 × ÖVERSIDAN 46 cm','4 × ÖVERSIDAN 71 cm','1 × separate 30 W driver'],show_all=True)
stage('Add crates and clothes','Fit out','Fill the band above the door, and move the folded clothes onto the shelves.',[
 f'Slide the six KNAGGLIG crates onto the lintels, three across and two high. There is {crate_gap:.0f} mm above the top row, so they go in flat rather than tilted.',
 'Crates are heavy overhead. Keep heavy things in the lower row, and secure the top row.',
 'Stack folded clothes in the tower bays between the posts: eight stacks of three across the two towers.',
 'Fit the equipment as in V18: Mac mini and router on the service shelf, Focusrite and dock under the front ends.',
 'Park the chair well under the desk when you are not using it.'
],extra=['6 × KNAGGLIG crates','Reused M1 Mac mini, router, OWC dock and two-input Focusrite','Removable equipment straps and cable clips'],show_all=True)
stage('Walk through the real room','Final check','A physical fit check completes the concept review.',[
 f'Walk through the door carrying something. {floor_w:,.0f} mm at the floor, {shoulder:,.0f} mm at shoulder height, {exit_w:,.0f} mm to the desk corner.',
 f'Sit at the desk and check the aisle beside the bed: {aisle:,.0f} mm with the chair parked, less when seated.',
 'Open the right balcony leaf and check its handle, curtains and coats.',
 'Have the ceiling and wall fixings checked before loading the crates or shelves.'
],notes=['The bathroom is only a shell because its fixtures are unknown.'],focus='plan',show_all=True)
assert assigned==set(parts),sorted(set(parts)-assigned)[:12]
draw_guide(stages,parts,A['boards'],DRAW)
fit=next(s for s in stages if s['title']=='Add crates and clothes');fit['diagram']='diagrams/equipment.svg'
def dim(id,label,a,b,value,basis):return {'id':id,'label':label,'a':a,'b':b,'value':round(value,1),'basis':basis}
room_basis='measured' if GEO['wall_measured'] else 'assumed';ceiling_basis='measured' if GEO['ceiling_measured'] else 'assumed';c=check['ceiling-storage']['points'];bed=check['bed-aisle']['points'];cx=G['cx'];hw=G['half_width'];y=G['ymid']
dimensions=[dim('room-width','Room width',[0,5550,50],[GEO['wall_x'],5550,50],GEO['wall_x'],room_basis),dim('room-length','Room length',[-220,0,50],[-220,5300,50],5300,'assumed'),
 dim('ceiling','Ceiling height',[60,5240,0],[60,5240,GEO['ceiling']],GEO['ceiling'],ceiling_basis),dim('portal-width','Door, widest',[cx-hw,yf-45,G['centre_z']],[cx+hw,yf-45,G['centre_z']],2*hw,'model'),
 dim('portal-floor','Door at the floor',[cx-floor_w/2,yf-45,10],[cx+floor_w/2,yf-45,10],floor_w,'model'),dim('portal-head','Door height',[cx,yf-45,0],[cx,yf-45,head],head,'preview'),
 dim('crate-ceiling','Top crates to ceiling',c[0],c[1],crate_gap,ceiling_basis),dim('bed-aisle','Bed to parked chair',bed[0],bed[1],aisle,'model')]
dz=-shift/1000;views={'overview':{'position':[8.0,7.2,4.8],'target':[1.7,.85,-1.6],'fov':43},'entrance':{'position':[2.36,1.42,-.42],'target':[2.36,1.38,-3.6],'fov':73},'desk':{'position':[1.58,1.43,-2.1125+dz],'target':[3.20,1.35,-2.1125+dz],'fov':62},'wardrobe':{'position':[1.32,1.55,-4.42],'target':[3.22,1.40,-4.54],'fov':65},'equipment':{'position':[2.00,.56,-2.1125+dz],'target':[3.29,.56,-2.1125+dz],'fov':90},'joints':{'position':[2.58,.50,-.94+dz],'target':[3.11,.48,-1.30+dz],'fov':68},'plan':{'position':[1.72,10.8,-2.1],'target':[1.72,0,-2.1],'fov':49}}
n=len(stages);pipes=sum(v for k,v in counts.items() if k.startswith('tube_'))
copy={
 '.header-status':'<span class="status-dot"></span> VARIANT <b>PORTAL</b>','.project-card .tiny-label':'THE PORTAL VARIANT','.version-token':'P',
 '.project-card h2':'A wall you<br>walk through.',
 '.feature-list':f'<button data-view="entrance"><span class="feature-icon">01</span><span><b>A door hinted, not built</b><small>{2*hw:,} × {head:,.0f} mm, drawn by the shelf ends</small></span><span>↗</span></button><button data-view="desk"><span class="feature-icon">02</span><span><b>The same desk, behind it</b><small>The whole module moved {shift:,.0f} mm along the wall</small></span><span>↗</span></button><button data-view="plan"><span class="feature-icon">03</span><span><b>Six crates over your head</b><small>Three across, two high, in the band above the door</small></span><span>↗</span></button>',
 '.project-note':'A second option, alongside V18. Fixed kitchen and bar retained.<br>Less hanging space; folded clothes move to the divider.',
 '.spec-strip':f'<div><strong>{2*hw:,} × {head:,.0f}</strong><span>mm door opening · {floor_w:,.0f} at the floor</span></div><div><strong>{crate_gap:.0f}</strong><span>mm above the top crates · {ceiling_basis} ceiling</span></div><div><strong>{len(parts)}</strong><span>frame & timber components</span></div><div><strong>{len(A["boards"])}</strong><span>oak boards, {len([k for k in A["boards"] if k.startswith("Portal.")])} in the divider</span></div>',
 '.editorial-card h2':'A room inside<br>a room.','.editorial-card p':f'The divider runs from the bar end to the right wall. Nothing in it is curved: {len(levels)*2+2} straight boards simply stop where the circle would be, and the eye does the rest.',
 '.detail-tags':'<span>Stock pipe lengths</span><span>Ceiling heights derived</span><span>Six KNAGGLIG crates</span><span>Bar stays fixed</span>',
 '#explore .verification-banner b':'A second option. The construction checks are still real.','#explore .verification-banner p':'Only the ceiling is measured. Room width and length, the bar and bed positions, sockets, ceiling construction, connector seating depths and every load capacity must be checked before cutting or building. The ceiling ties and overhead crates especially need a proper answer. The bathroom is a shell.',
 '.nav-item[data-tab="build"] span':str(n),'.build-intro p':f'{n} stages. Every frame component accounted for.<br>Start with the ceiling, not a final wood cut.','.step-progress small':f'/{n}',
 '#bom-link':f'<a class="text-button" href="downloads/bom-portal.csv" download>Download the BOM · CSV ↗</a>',
 '.download-grid':f'<a href="downloads/cut-list-portal.csv" download><span>01</span><div><b>Concept timber cut list</b><small>{len(A["boards"])} structural boards · verify fittings first</small></div><i>↗</i></a><a href="downloads/complete-bom-portal.md" download><span>02</span><div><b>Complete BOM</b><small>Markdown, with checks and notes</small></div><i>↗</i></a><a href="https://github.com/Krydix/FlatPlanning/blob/main/source/flat-portal.blend" target="_blank" rel="noopener noreferrer"><span>03</span><div><b>Blender model</b><small>The geometry behind this viewer</small></div><i>↗</i></a><a href="https://github.com/Krydix/FlatPlanning/blob/main/source/portal-layout.json" target="_blank" rel="noopener noreferrer"><span>04</span><div><b>Layout inputs</b><small>Door, crates and shelf levels</small></div><i>↗</i></a>',
 '.site-footer small':'Portal variant · Original planning guide · Updated 5 November 2026'}
metadata={'design':'Portal','variant':'portal','locked':False,'updated':'2026-11-05','priceBasis':'19–20 October 2026','partCount':len(parts),'pipeCount':pipes,'boardCount':len(A['boards']),'hardwarePieces':sum(v for k,v in counts.items() if k!='wood'),'lightState':'Afternoon daylight · ceiling fixture off','coreBudget':core,'withCrates':with_crates,'optionalAccessories':float(t['optional_accessories']),'entryGap':check['entry-passage']['value'],'desk':[1615,702,732],'room':[GEO['wall_x'],ROOM['assumed']['room_length_y'],GEO['ceiling']],'roomHeightMeasured':GEO['ceiling_measured'],'roomWidthMeasured':GEO['wall_measured'],'servicesSurveyed':ROOM['services']['status']!='not surveyed',
 'portal':{'width':2*hw,'floorWidth':floor_w,'head':head,'exitWidth':exit_w,'crates':6,'deskOffset':shift},'verification':['Room width and length still the CAD assumption; ceiling measured at '+f'{GEO["ceiling"]:,.0f} mm','Bar and bed positions come from the CAD model','Ceiling construction and tie fixings unknown','Sockets, switches, radiators and pipes are not surveyed','Connector seating offsets not measured','Cantilever, clamp, wood screw, wall and ceiling load capacities not certified','Bathroom fixtures unknown; shell only'],
 'model':'models/flat-portal-baked.glb?bake=portal-6','assemblyModel':'models/assembly-portal.glb?design=portal-2','views':views,'copy':copy,
 'printTitle':'FLAT / PORTAL · ORIGINAL ASSEMBLY PLANNING GUIDE','printHeading':'A wall.<br>A door hinted in it.','printStatus':f'Portal variant · {n} stages · {len(parts)} frame/timber components','printFacts':f'Divider from the bar end to the right wall. Opening {2*hw:,} × {head:,.0f} mm, {floor_w:,.0f} mm at the floor. Six crates above the door. Desk moved {shift:,.0f} mm along the wall. Main ceiling light off. Existing kitchen and bar stay fixed.'}
jwrite(OUT/'project-portal.json',{'meta':metadata,'dimensions':dimensions,'clearances':CLEAR,'parts':rows,'stages':stages,'boards':A['boards'],'columns':A['columns'],'graph':A['parts'],'checks':{'allAssignedExactlyOnce':True,'coreBudgetReconciled':core,'tubeLengths':sorted(STOCK)},'sources':{'repo':'https://github.com/Krydix/FlatPlanning','pages':'https://krydix.github.io/FlatPlanning/'}})
jwrite(OUT/'assembly-portal.json',A)
with (DL/'bom-portal.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Category','Part','Description','SKU','Required pieces','Purchase packs','Pack size','Pack/unit price EUR','Line total EUR','Supplier URL','Price / verification note'])
 for r in rows:w.writerow([r['category'],r['name'],r['description'],r.get('sku',''),r['quantity'],r.get('buyPacks',''),r.get('packSize',''),r.get('unitPrice',''),r['total'],r.get('url',''),r['status']])
with (DL/'cut-list-portal.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['Board ID','Length mm','Depth mm','Thickness mm','Underside mm','Rotation degrees','Post holes mm','Corner radii mm','Status'])
 for id,b in A['boards'].items():
  x0,x1,y0,y1=b['bounds'];w.writerow([id,y1-y0,x1-x0,b['thickness'],b['bottom'],b.get('rotation_degrees',0),json.dumps(b['holes']),json.dumps(b.get('corner_radii',[])),'CONCEPT ONLY — calibrate fitting profile before cutting'])
md=['# Complete BOM — Portal divider variant','',f"Core estimate **€{core:,.2f}** including 10% reserve. With six crates **€{with_crates:,.2f}**. Prices keep V18's 19–20 October 2026 basis; timber is priced by area at V18's rate per thickness, and the divider's extra machining and fixings are allowances.",'','| Part | Qty | Packs | Unit/pack € | Total € | Source |','|---|---:|---:|---:|---:|---|']
md+=[f"| {r['name']} · {r['description']} | {r['quantity']} | {r.get('buyPacks','—')} | {r.get('unitPrice','—')} | {r['total']:.2f} | {r.get('url') or 'Allowance'} |" for r in rows]
md+=['','## Connection and machining checks','',*A['notes'][-6:],'','Ceiling construction, fixings, clamp loads and connector seating offsets require measurement. No final drilling or routing template is supplied.']
(DL/'complete-bom-portal.md').write_text('\n'.join(md)+'\n')
print('PORTAL_DATA_READY',json.dumps({'parts':len(parts),'stages':n,'budget':core,'withCrates':with_crates,'BOMlines':len(rows),'hardware':round(sum(r['total'] for r in rows if r['category']=='Hardware'),2),'wood':round(sum(r['total'] for r in rows if r['category']=='Wood'),2)}))
