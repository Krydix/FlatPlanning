"""Orthographic equipment planning sheet, generated from the shared envelopes."""
import json,html
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;cfg=json.loads((ROOT/'source/equipment-layout.json').read_text())
# Top view: along-desk width maps to horizontal; front-to-wall maps upward.
def pt(x,y):return (70+(2920-y)*.55,470-(x-2703)*.55)
s=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 720" role="img"><title>Under-desk service shelf and front device mounts</title><rect width="1040" height="720" fill="white"/>','<g fill="none" stroke="#1b2520" stroke-width="2">']
def rect(bounds,fill='white',stroke='#1b2520',dash=False):
 x0,x1,y0,y1=bounds;p=pt(x0,y0);q=pt(x1,y1);s.append(f'<rect x="{min(p[0],q[0])}" y="{min(p[1],q[1])}" width="{abs(q[0]-p[0])}" height="{abs(p[1]-q[1])}" fill="{fill}" stroke="{stroke}"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')
def text(x,y,v,size=16):s.append(f'<text x="{x}" y="{y}" stroke="none" fill="#1b2520" font-family="Arial,sans-serif" font-size="{size}">{html.escape(v)}</text>')
rect([2703,3405,1305,2920]);rect(cfg['shelf']['bounds'],'#eeeae1');rect(cfg['knee_zone']['bounds'],'#f7f8f6','#6f8175',True)
for d in cfg['devices']:
 x,y,z=d['location'];dx,dy,dz=d['size'];rect([x-dx/2,x+dx/2,y-dy/2,y+dy/2],'#fff')
 p=pt(x,y);name={'Mac mini M1':'M1 mini','Router allowance':'Router','Power brick 1':'PSU 1','Power brick 2':'PSU 2','Power brick 3':'PSU 3','Focusrite two-input interface':'Focusrite','OWC Thunderbolt 4 dock':'OWC dock'}[d['id']];text(p[0]-28,p[1]+5,name,13)
for m in cfg['mounts']:rect(m['bounds'],'none','#626c66',True)
s.append('</g>');text(70,42,'20 / EQUIPMENT UNDER THE DESK',22);text(70,76,'TOP VIEW THROUGH THE TABLETOP · CONCEPT CLEARANCES',15)
text(90,511,'FRONT / SEATED SIDE',16);text(342,455,'700 mm central knee width',16)
text(70,550,'Rear shelf: 1615 × 230 × 18 mm · top 518 mm · 186 mm clear above',16)
text(70,580,'472 mm knee depth before the rear shelf; keep the middle open.',16)
text(70,610,'Front holders: controls face the room. Check case, plugs, vents and short screws.',15)
text(70,640,'Mac ports face along shelf. Strap bricks separately and retain service loops.',15)
text(70,680,'Router, brick and holder envelopes are provisional. Not a drilling template.',14)
s.append('</svg>');(ROOT/'public/diagrams/equipment.svg').write_text(''.join(s))
