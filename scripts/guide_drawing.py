"""Original IKEA-inspired line illustrations for the assembly guide, one SVG per stage."""
import html,math
from pipe_engine import board_corners,board_outline
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(v,s):return tuple(x*s for x in v)
def project(v):
 x,y,z=v;return (.86*(y-1300)-.66*(x-2795),-.94*z+.24*(y-1300)+.30*(x-2795))
def esc(v):return html.escape(str(v),quote=True)
def poly(points,stroke,fill='none',width=3):return '<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" stroke="{stroke}" fill="{fill}" stroke-width="{width}" stroke-linejoin="round"/>'
def line(p,q,color,width=5,dash=False):return f'<line x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" y2="{q[1]:.2f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"'+(' stroke-dasharray="12 12"' if dash else '')+'/>'
def draw_part(id,parts,boards,active=False):
 p=parts[id];kind=p['kind'];o=p['origin'];axis=p['axis'];d=p['direction'];color='#17221c' if active else '#d8dcd5';fill='#fff' if active else '#f6f7f3';s=[]
 if kind.startswith('tube_'):
  s.append(line(project(o),project(add(o,mul(axis,p['data']['length']))),color,15 if active else 9))
 elif kind=='wood':
  b=boards[id];c=board_outline(b);z=b['bottom'];top=[project((x,y,z+b['thickness'])) for x,y in c];bottom=[project((x,y,z)) for x,y in c];n=len(c)
  for i in range(n):s.append(poly([bottom[i],bottom[(i+1)%n],top[(i+1)%n],top[i]],color,fill,3 if n==4 else 1.5))
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
 elif kind=='bracket':
  s.append(line(project(add(o,(0,0,-120))),project(o),color,8));s.append(line(project(o),project(add(o,mul(d,p['data']['reach']))),color,8))
 elif kind=='saddle':
  s.append(line(project(add(o,(0,0,-14))),project(add(o,mul(d,32))),color,8));s.append(line(project(add(o,mul(d,32))),project(add(add(o,mul(d,32)),(0,0,24))),color,5))
 return ''.join(s)
def draw_guide(stages,parts,boards,folder):
 seen=set()
 for st in stages:
  active=set(st['parts']);seen.update(active)
  preview=active or (set(parts) if st.get('showAll',st['id']<=2 or st['id']>=18) else seen)
  coords=[]
  for id in preview:
   p=parts[id];coords.append(project(p['origin']))
   if p['kind'].startswith('tube_'):coords.append(project(add(p['origin'],mul(p['axis'],p['data']['length']))))
   if p['kind']=='wood':coords.extend(project((x,y,boards[id]['bottom'])) for x,y in board_corners(boards[id]))
  x0=min(x for x,y in coords)-240;x1=max(x for x,y in coords)+240;y0=min(y for x,y in coords)-180;y1=max(y for x,y in coords)+180
  # Limit zoom to keep a meaningful physical context around a small detail.
  if x1-x0<1000:mid=(x0+x1)/2;x0=mid-500;x1=mid+500
  if y1-y0<900:mid=(y0+y1)/2;y0=mid-450;y1=mid+450
  body=[]
  for id in sorted(seen-active,key=lambda id:sum(parts[id]['origin'][:2]),reverse=True):body.append(draw_part(id,parts,boards,False))
  for id in sorted(preview,key=lambda id:sum(parts[id]['origin'][:2]),reverse=True):body.append(draw_part(id,parts,boards,True))
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.2f} {y0:.2f} {x1-x0:.2f} {y1-y0:.2f}" role="img" aria-labelledby="title"><title id="title">Step {st["id"]}: {esc(st["title"])}</title><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff"/>'+''.join(body)+'</svg>'
  (folder/f'step-{st["id"]:02}.svg').write_text(svg)
