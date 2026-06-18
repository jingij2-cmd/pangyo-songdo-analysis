import csv, math, heapq, numpy as np
from datetime import date
D="/sessions/epic-eager-bohr/mnt/.projects/019eb978-ac1c-7129-8c8d-bcbdd2ceb136/docs"
GRID="/sessions/epic-eager-bohr/mnt/uploads/2024년_인구_다사_100M.csv"
OX,OY=900000.0,1900000.0  # 다사 100km tile origin in EPSG:5179 (x[900k-1000k],y[1900k-2000k])

# ---- load grid pop (to_in_001) -> 5179 centroid ----
gx=[];gy=[];gp=[]
for row in csv.reader(open(GRID,encoding='cp949',errors='replace')):
    if row[2]!='to_in_001': continue
    d=row[1].replace('다사','')
    XXX=int(d[:3]); YYY=int(d[3:])
    try: p=int(row[3])
    except: p=0
    gx.append(OX+XXX*100+50); gy.append(OY+YYY*100+50); gp.append(p)
gx=np.array(gx);gy=np.array(gy);gp=np.array(gp,float)
print("grid cells:",len(gp),"pop sum:",int(gp.sum()))
print("5179 X range %.0f-%.0f Y %.0f-%.0f"%(gx.min(),gx.max(),gy.min(),gy.max()))

# validate: convert a high-pop centroid to lng/lat via EPSG:5179 inverse (GRS80, no datum shift)
a=6378137.0; f=1/298.257222101; e2=f*(2-f); k0=0.9996
lat0=math.radians(38.0); lon0=math.radians(127.5); FE=1000000.0; FN=2000000.0
def M(phi): return a*((1-e2/4-3*e2**2/64-5*e2**3/256)*phi-(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*phi)+(15*e2**2/256+45*e2**3/1024)*math.sin(4*phi)-(35*e2**3/3072)*math.sin(6*phi))
M0=M(lat0); e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
def inv5179(E,N):
    mu=(M0+(N-FN)/k0)/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    p1=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16)*math.sin(4*mu)+(151*e1**3/96)*math.sin(6*mu)
    C1=(e2/(1-e2))*math.cos(p1)**2; T1=math.tan(p1)**2
    N1=a/math.sqrt(1-e2*math.sin(p1)**2); R1=a*(1-e2)/(1-e2*math.sin(p1)**2)**1.5
    Dd=(E-FE)/(N1*k0); ep2=e2/(1-e2)
    lat=p1-(N1*math.tan(p1)/R1)*(Dd**2/2-(5+3*T1+10*C1-4*C1**2-9*ep2)*Dd**4/24)
    lon=lon0+(Dd-(1+2*T1+C1)*Dd**3/6+(5-2*C1+28*T1)*Dd**5/120)/math.cos(p1)
    return math.degrees(lat),math.degrees(lon)
i=int(np.argmax(gp)); la,lo=inv5179(gx[i],gy[i])
print("max-pop cell pop=%d at lng=%.4f lat=%.4f (검증: 수도권이면 lng126-128,lat37-38)"%(gp[i],lo,la))

# ---- subway nodes + dijkstra ----
nodes={}
for r in csv.DictReader(open(f"{D}/nodes.tsv"),delimiter='\t'):
    nodes[int(r['id'])]=(float(r['x_5179']),float(r['y_5179']),r['statnm'],r['begin'],r['effective_begin'])
def pdte(s):
    s=(s or '').strip()
    if not s: return None
    try:y,m,dd=s.split('-');return date(int(y),int(m),int(dd))
    except:return None
CUT=date(2026,6,18)
from collections import defaultdict
adj=defaultdict(list)
for r in csv.DictReader(open(f"{D}/links.tsv"),delimiter='\t'):
    b=pdte(r['begin'])
    if b and b>CUT: continue
    fr=int(r['fromNode']);t=int(r['toNode'])
    if fr not in nodes or t not in nodes: continue
    adj[fr].append((t,float(r['timeFT']))); adj[t].append((fr,float(r['timeTF'])))
def dij(srcs):
    dist={s:0.0 for s in srcs}; pq=[(0.0,s) for s in srcs]; heapq.heapify(pq)
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist.get(u,1e18):continue
        for v,w in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18): dist[v]=nd; heapq.heappush(pq,(nd,v))
    return dist

WALK=1.2; DETOUR=1.3  # m/s, street detour factor
def reach_pop(label,srcs):
    dist=dij(srcs)
    # for each reachable node within 60min, relax grid cells
    cell_t=np.full(len(gp),1e18)
    sx=np.array([nodes[n][0] for n in dist]); sy=np.array([nodes[n][1] for n in dist]); st=np.array([dist[n] for n in dist])
    for k in range(len(st)):
        if st[k]>3600: continue
        budget=3600-st[k]
        Rmax=budget*WALK/DETOUR  # max straight-line dist whose walk fits in remaining 60min budget
        # prune cells by bbox
        m=(np.abs(gx-sx[k])<=Rmax)&(np.abs(gy-sy[k])<=Rmax)
        if not m.any(): continue
        dd=np.hypot(gx[m]-sx[k],gy[m]-sy[k])*DETOUR
        tt=st[k]+dd/WALK
        cur=cell_t[m]; cell_t[m]=np.minimum(cur,tt)
    p30=gp[cell_t<=1800].sum(); p60=gp[cell_t<=3600].sum()
    print(f"\n===== {label} =====")
    print(f"30분 도달인구: {int(p30):,}  | 60분 도달인구: {int(p60):,}")
    return int(p30),int(p60)

res={}
res['판교']=reach_pop("판교 (신분당·경강)",[26,824])
res['송도']=reach_pop("송도 국제업무지구 (인천1호선)",[249])
import json; json.dump(res,open("reachpop_result.json","w"))
print("\nratio 30min 판교/송도: %.2f"%(res['판교'][0]/res['송도'][0]))
